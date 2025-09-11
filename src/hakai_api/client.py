"""Get authorized requests to the Hakai API using the requests library.

Supports both web flow (copy/paste credentials) and desktop flow (OAuth with PKCE).
"""

from __future__ import annotations

import json
import os
import secrets
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import mktime
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

import pkce
from loguru import logger
from requests_oauthlib import OAuth2Session


class Client(OAuth2Session):
    """Hakai API client for authenticated HTTP requests.

    Extends OAuth2Session to provide authenticated access to the Hakai API
    resource server. Handles OAuth2 credential management, caching, and
    automatic token refresh for seamless API interactions.

    The client supports two authentication flows:
    - Web flow: Copy/paste credentials from a web login page (default)
    - Desktop flow: OAuth2 with PKCE for native applications

    Credentials are automatically cached to ~/.hakai-api-auth for reuse
    across sessions until expiry.

    Attributes:
        DEFAULT_API_ROOT: Default production API base URL.
        DEFAULT_LOGIN_PAGE: Default production login page URL.
        CREDENTIALS_ENV_VAR: Environment variable name for credentials.
        USER_AGENT_ENV_VAR: Environment variable name for User-Agent header.

    Example:
        Basic usage with default settings:

        >>> client = Client()
        >>> response = client.get("/eims/views/output/stations")

        Desktop OAuth flow:

        >>> client = Client(auth_flow="desktop")
        >>> response = client.get("/eims/views/output/stations")

        Custom API endpoint:

        >>> client = Client(api_root="https://custom.api.endpoint")
        >>> response = client.get("/custom/endpoint")
    """

    _credentials_file = os.path.expanduser("~/.hakai-api-auth")
    DEFAULT_API_ROOT = "https://hecate.hakai.org/api"
    DEFAULT_LOGIN_PAGE = "https://hecate.hakai.org/api-client-login"
    CREDENTIALS_ENV_VAR = "HAKAI_API_CREDENTIALS"
    USER_AGENT_ENV_VAR = "HAKAI_API_USER_AGENT"

    def __init__(
        self,
        api_root: str = DEFAULT_API_ROOT,
        login_page: str = DEFAULT_LOGIN_PAGE,
        credentials: str | dict | None = None,
        auth_flow: Literal["web", "desktop"] = "web",
        local_port: int = 65500,
    ) -> None:
        """Create a new Client class with credentials.

        Args:
            api_root: The base url of the hakai api you want to call.
                Defaults to the production server.
            login_page: The url of the login page to direct users to.
                Defaults to the production login page.
            credentials: Credentials token retrieved from the hakai api
                login page. If `None`, loads cached credentials or prompts for log in.
            auth_flow: Authentication flow type - "web" (default, copy/paste) or "desktop" (OAuth with PKCE).
                Only used if credentials are not provided.
            local_port: Port for local callback server in desktop flow (default 65500).
                Only used when auth_flow="desktop".

        Raises:
            ValueError: If credentials are unable to be set.
        """
        self._api_root = api_root
        self._login_page = login_page
        self._credentials = None
        self._auth_flow = auth_flow
        self._local_port = local_port

        # Desktop OAuth state
        self._state = None
        self._code_verifier = None
        self._authorization_code = None

        # Try to get credentials from various sources
        logger.debug(f"Initializing Hakai API client with auth_flow={auth_flow}")
        env_credentials = os.getenv(self.CREDENTIALS_ENV_VAR, None)
        if isinstance(credentials, dict):
            logger.debug("Using provided credentials dictionary")
            self._credentials = credentials
        elif isinstance(credentials, str):
            logger.debug("Parsing credentials from provided string")
            # Parse credentials from string
            self._credentials = self._parse_credentials_string(credentials)
        elif env_credentials is not None:
            logger.debug("Loading credentials from environment variable")
            self._credentials = self._parse_credentials_string(env_credentials)
        elif self.file_credentials_are_valid():
            logger.debug("Loading cached credentials from file")
            self._credentials = self._get_credentials_from_file()
        else:
            # Get new credentials based on auth_flow
            logger.info(f"No valid cached credentials found, starting {auth_flow} authentication flow")
            if auth_flow == "desktop":
                self._credentials = self._get_credentials_from_desktop_oauth()
            else:
                # Default to web flow for backward compatibility
                self._credentials = self._get_credentials_from_web()

        if self._credentials is None:
            logger.error("Failed to obtain valid credentials from any source")
            raise ValueError("Credentials could not be set.")

        # Cache the credentials
        logger.debug("Caching credentials to file")
        self._save_credentials_to_file(self._credentials)

        # Init the OAuth2Session parent class with credentials
        super().__init__(token=self._credentials)

        # Set User-Agent header
        user_agent = os.getenv(self.USER_AGENT_ENV_VAR, "hakai-api-client-py")
        self.headers.update({"User-Agent": user_agent})
        logger.info(f"Hakai API client initialized successfully with User-Agent: {user_agent}")

    @property
    def api_root(self) -> str:
        """Return the api base url.

        Returns:
            The base URL of the Hakai API.
        """
        return self._api_root

    @property
    def login_page(self) -> str:
        """Return the login page url.

        Returns:
            The URL of the login page.
        """
        return self._login_page

    @property
    def credentials(self) -> dict:
        """Return the credentials object.

        Returns:
            Credentials object.

        Raises:
            ValueError: If credentials are not provided.
        """
        if self._credentials is None:
            raise ValueError("Credentials have not been set.")
        return self._credentials

    @classmethod
    def reset_credentials(cls) -> None:
        """Remove the cached credentials file.

        Deletes the credentials file from the filesystem if it exists.
        """
        if os.path.isfile(cls._credentials_file):
            logger.info("Removing cached credentials file")
            os.remove(cls._credentials_file)
        else:
            logger.debug("No cached credentials file to remove")

    def _save_credentials_to_file(self, credentials: dict) -> None:
        """Save the credentials object to a file.

        Args:
            credentials: Credentials object.

        Raises:
            OSError: If file cannot be created or written to.
            json.JSONEncodeError: If credentials cannot be serialized to JSON.
        """
        try:
            with open(self._credentials_file, "w") as outfile:
                json.dump(credentials, outfile)
            logger.debug(f"Credentials saved to {self._credentials_file}")
        except (OSError, json.JSONEncodeError) as e:
            logger.error(f"Failed to save credentials to file: {e}")
            raise

    @classmethod
    def file_credentials_are_valid(cls) -> bool:
        """Check if the cached credentials exist and are valid.

        Validates that the credentials file exists, can be parsed,
        contains required fields, and has not expired.

        Returns:
            True if the credentials are valid, False otherwise.
        """
        if not os.path.isfile(cls._credentials_file):
            logger.debug("No cached credentials file found")
            return False
        with open(cls._credentials_file):
            try:
                credentials = cls._get_credentials_from_file()
                expires_at = credentials["expires_at"]
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid cached credentials file, removing: {e}")
                os.remove(cls._credentials_file)
                return False

            now = int(mktime(datetime.now().timetuple()) + datetime.now().microsecond / 1000000.0)  # utc timestamp

        if now > expires_at:
            logger.info("Cached credentials have expired, removing")
            cls.reset_credentials()
            return False

        logger.debug("Cached credentials are valid")
        return True

    @classmethod
    def _get_credentials_from_file(cls) -> dict:
        """Get user credentials from a cached file.

        Loads and validates credentials from the cached credentials file.

        Returns:
            A dict containing the credentials with required keys and proper types.
        """
        with open(cls._credentials_file) as infile:
            result = json.load(infile)
        result = Client._check_keys_convert_types(result)
        return result

    def _get_credentials_from_web(self) -> dict:
        """Get user credentials from a web sign-in.

        Prompts the user to copy and paste credentials from the login page.

        Returns:
            A dict containing the credentials parsed from user input.

        Raises:
            ValueError: If the input format is invalid or cannot be split properly.
            AttributeError: If the input string lacks expected string methods.
        """
        logger.info(f"Please visit the login page: {self._login_page}")
        response = input("\nCopy and paste your credentials from the login page:\n")

        logger.debug("Parsing credentials from user input")
        # Reformat response to dict
        try:
            credentials = dict(map(lambda x: x.split("="), response.split("&")))
            logger.debug("Successfully parsed web credentials")
            return credentials
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to parse credentials from input: {e}")
            raise

    def _get_credentials_from_desktop_oauth(self) -> dict:
        """Get user credentials using desktop OAuth flow with PKCE.

        Returns:
            A dict containing the credentials.

        Raises:
            ValueError: If credentials could not be loaded.
        """
        # Generate PKCE parameters
        self._code_verifier, code_challenge = pkce.generate_pkce_pair()

        # Generate state for CSRF protection
        self._state = secrets.token_urlsafe(32)

        # Build authorization URL for desktop endpoint
        from urllib.parse import urlencode

        params = {
            "redirect_uri": f"http://127.0.0.1:{self._local_port}/callback",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": self._state,
        }

        # Use the desktop auth endpoint
        auth_url = f"{self._api_root}/auth/desktop?{urlencode(params)}"

        webbrowser.open(auth_url)

        # Start local server to receive callback
        logger.info(f"Starting local callback server on port {self._local_port}")
        self._authorization_code = self._wait_for_callback()

        if not self._authorization_code:
            logger.error("Failed to receive authorization code from OAuth callback")
            raise ValueError("Failed to receive authorization code")

        logger.debug("Successfully received authorization code, exchanging for tokens")
        # Exchange code for tokens
        tokens = self._exchange_code_for_tokens()

        # Convert desktop token response to match web format
        credentials = {
            "access_token": tokens["access_token"],
            "token_type": tokens["token_type"],
            "expires_at": tokens["expires_at"],
            "expires_in": tokens["expires_in"],
        }

        # Store refresh token if provided
        if "refresh_token" in tokens:
            credentials["refresh_token"] = tokens["refresh_token"]
            logger.debug("Desktop OAuth completed successfully with refresh token")
        else:
            logger.debug("Desktop OAuth completed successfully without refresh token")

        return credentials

    def _wait_for_callback(self) -> str | None:
        """Start a local HTTP server to receive the OAuth callback.

        Starts a local HTTP server on the configured port to handle the OAuth
        callback redirect. Validates the state parameter and extracts the
        authorization code from the callback parameters.

        Returns:
            The authorization code from the OAuth callback.

        Raises:
            ValueError: If state mismatch occurs, OAuth error is returned,
                or no authorization code is received.
        """
        authorization_code = None
        server_error = None

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self) -> None:  # noqa: N802, N805
                nonlocal authorization_code, server_error

                parsed_url = urlparse(handler_self.path)

                if parsed_url.path == "/callback":
                    params = parse_qs(parsed_url.query)

                    # Verify state parameter
                    received_state = params.get("state", [None])[0]
                    if received_state != self._state:
                        server_error = "State mismatch - possible CSRF attack"
                        logger.error(server_error)
                        handler_self.send_error(400, server_error)
                        return

                    # Check for errors
                    if "error" in params:
                        error = params["error"][0]
                        error_desc = params.get("error_description", [""])[0]
                        server_error = f"OAuth error: {error} - {error_desc}"
                        logger.error(server_error)
                        handler_self.send_error(400, server_error)
                        return

                    # Get authorization code
                    authorization_code = params.get("code", [None])[0]

                    if not authorization_code:
                        server_error = "No authorization code received"
                        logger.error(server_error)
                        handler_self.send_error(400, server_error)
                        return

                    # Send success response
                    handler_self.send_response(200)
                    handler_self.send_header("Content-type", "text/html")
                    handler_self.end_headers()

                    success_html = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Authentication Successful</title>
                        <style>
                            body {
                                font-family: -apple-system, system-ui, sans-serif;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                height: 100vh;
                                margin: 0;
                                background: #82080B;
                            }
                            .container {
                                background: white;
                                padding: 40px;
                                border-radius: 10px;
                                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                                text-align: center;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Authentication Successful!</h1>
                            <p>You can close this window and return to your application.</p>
                            <script>setTimeout(() => window.close(), 2000);</script>
                        </div>
                    </body>
                    </html>
                    """
                    handler_self.wfile.write(success_html.encode())
                else:
                    handler_self.send_error(404, "Not found")

            def log_message(self, *args: list[Any] | None) -> None:
                pass  # Suppress logging

        # Start server
        server = HTTPServer(("127.0.0.1", self._local_port), CallbackHandler)
        server.timeout = 120  # 2 minute timeout
        server.handle_request()
        server.server_close()

        if server_error:
            logger.error(f"OAuth callback server error: {server_error}")
            raise ValueError(server_error)

        logger.debug("OAuth callback received successfully")
        return authorization_code

    def _exchange_code_for_tokens(self) -> dict:
        """Exchange authorization code for tokens using the desktop endpoint.

        Returns:
            A dictionary containing the authorization code (JWT token).

        Raises:
            ValueError: If the authorization code is invalid.

        """
        import requests

        token_url = f"{self._api_root}/auth/desktop/token"
        data = {
            "code": self._authorization_code,
            "code_verifier": self._code_verifier,
            "redirect_uri": f"http://127.0.0.1:{self._local_port}/callback",
        }

        response = requests.post(token_url, json=data, timeout=10)

        if response.status_code != 200:
            error_msg = f"Token exchange failed: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('error', '')}: {error_data.get('error_description', '')}"
            except (json.JSONDecodeError, ValueError):
                error_msg += f" - {response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Successfully exchanged authorization code for tokens")
        return response.json()

    def refresh_token(self) -> bool:
        """Refresh the access token using the refresh token.

        Uses the stored refresh token to obtain a new access token from
        the API. Updates the stored credentials and OAuth2Session token
        if successful.

        Returns:
            True if refresh successful, False otherwise.
        """
        if "refresh_token" not in self._credentials:
            logger.debug("No refresh token available, cannot refresh")
            return False

        logger.debug("Attempting to refresh access token")

        import requests

        refresh_url = f"{self._api_root}/auth/refresh"
        data = {
            "refresh_token": self._credentials["refresh_token"],
            "client_type": "desktop" if self._auth_flow == "desktop" else "web",
        }

        try:
            response = requests.post(refresh_url, json=data, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Token refresh failed with status {response.status_code}")
                return False

            new_tokens = response.json()

            # Update credentials
            self._credentials["access_token"] = new_tokens["access_token"]
            self._credentials["expires_at"] = new_tokens["expires_at"]
            self._credentials["expires_in"] = new_tokens["expires_in"]

            # Save updated credentials
            self._save_credentials_to_file(self._credentials)

            # Update OAuth2Session token
            self.token = self._credentials

            logger.info("Access token refreshed successfully")
            return True

        except (requests.RequestException, json.JSONDecodeError, KeyError, OSError) as e:
            logger.error(f"Token refresh failed with exception: {e}")
            return False

    @staticmethod
    def _parse_credentials_string(credentials: str) -> dict:
        """Parse a credentials string into a dictionary.

        Args:
            credentials: The credentials string.

        Returns:
            A dictionary containing the credentials.

        Raises:
            ValueError: If the string format is invalid or cannot be split properly.
            AttributeError: If the string lacks expected string methods.
            KeyError: If required credential keys are missing after parsing.
        """
        logger.debug("Parsing credentials string")
        try:
            result = dict(map(lambda x: x.split("="), credentials.split("&")))
            result = Client._check_keys_convert_types(result)
            logger.debug("Successfully parsed and validated credentials string")
            return result
        except (ValueError, AttributeError, KeyError) as e:
            logger.error(f"Failed to parse credentials string: {e}")
            raise

    @staticmethod
    def _check_keys_convert_types(credentials: dict) -> dict:
        """Check and clean the credentials.

        Validates that required keys are present and converts string values
        to appropriate types (expires_at and expires_in to integers).

        Args:
            credentials: credentials dictionary to validate and clean.

        Returns:
            updated credentials dictionary with proper types.

        Raises:
            ValueError: if required keys (access_token, token_type, expires_at)
                are missing from the credentials dictionary.
        """
        missing_keys = [key for key in ["access_token", "token_type", "expires_at"] if key not in credentials]
        if len(missing_keys) > 0:
            logger.error(f"Credentials missing required keys: {missing_keys}")
            raise ValueError(f"Credentials string is missing required keys: {str(missing_keys)}.")

        # Convert expires_at to int
        try:
            credentials["expires_at"] = int(float(credentials["expires_at"]))
            logger.debug(f"Credentials expire at timestamp: {credentials['expires_at']}")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid expires_at value: {e}")
            raise ValueError(f"Invalid expires_at value in credentials: {e}")

        # If expires_in is present, convert to int
        if "expires_in" in credentials:
            try:
                credentials["expires_in"] = int(float(credentials["expires_in"]))
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid expires_in value: {e}")
                raise ValueError(f"Invalid expires_in value in credentials: {e}")

        return credentials
