"""Get authorized requests to the Hakai API using the requests library.

Supports both web flow (copy/paste credentials) and desktop flow (OAuth with PKCE).

Written by: Taylor Denouden, Chris Davis, and Nate Rosenstock
Last updated: Sept 2025
"""

import json
import os
import secrets
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from time import mktime
from typing import Dict, Union, Literal, Optional
from urllib.parse import urlparse, parse_qs

import pkce
from requests_oauthlib import OAuth2Session


class Client(OAuth2Session):
    _credentials_file = os.path.expanduser("~/.hakai-api-auth")
    DEFAULT_API_ROOT = "https://hecate.hakai.org/api"
    DEFAULT_LOGIN_PAGE = "https://hecate.hakai.org/api-client-login"
    CREDENTIALS_ENV_VAR = "HAKAI_API_CREDENTIALS"
    USER_AGENT_ENV_VAR = "HAKAI_API_USER_AGENT"

    def __init__(
        self,
        api_root: str = DEFAULT_API_ROOT,
        login_page: str = DEFAULT_LOGIN_PAGE,
        credentials: Union[str, Dict] = None,
        auth_flow: Literal["web", "desktop"] = "web",
        local_port: int = 65500,
    ):
        """Create a new Client class with credentials.

        Params:
            api_root: The base url of the hakai api you want to call.
                Defaults to the production server.
            login_page: The url of the login page to direct users to.
                Defaults to the production login page.
            credentials (str, Dict): Credentials token retrieved from the hakai api
                login page. If `None`, loads cached credentials or prompts for log in.
            auth_flow: Authentication flow type - "web" (default, copy/paste) or "desktop" (OAuth with PKCE).
                Only used if credentials are not provided.
            local_port: Port for local callback server in desktop flow (default 65500).
                Only used when auth_flow="desktop".
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
        env_credentials = os.getenv(self.CREDENTIALS_ENV_VAR, None)
        if isinstance(credentials, dict):
            self._credentials = credentials
        elif isinstance(credentials, str):
            # Parse credentials from string
            self._credentials = self._parse_credentials_string(credentials)
        elif env_credentials is not None:
            self._credentials = self._parse_credentials_string(env_credentials)
        elif self.file_credentials_are_valid():
            self._credentials = self._get_credentials_from_file()
        else:
            # Get new credentials based on auth_flow
            if auth_flow == "desktop":
                self._credentials = self._get_credentials_from_desktop_oauth()
            else:
                # Default to web flow for backward compatibility
                self._credentials = self._get_credentials_from_web()

        if self._credentials is None:
            raise ValueError("Credentials could not be set.")

        # Cache the credentials
        self._save_credentials_to_file(self._credentials)

        # Init the OAuth2Session parent class with credentials
        super(Client, self).__init__(token=self._credentials)

        # Set User-Agent header
        user_agent = os.getenv(self.USER_AGENT_ENV_VAR, "hakai-api-client-py")
        self.headers.update({"User-Agent": user_agent})

    @property
    def api_root(self) -> str:
        """Return the api base url."""
        return self._api_root

    @property
    def login_page(self) -> str:
        """Return the login page url."""
        return self._login_page

    @property
    def credentials(self) -> Dict:
        """Return the credentials object."""
        if self._credentials is None:
            raise ValueError("Credentials have not been set.")
        return self._credentials

    @classmethod
    def reset_credentials(cls):
        """Remove the cached credentials file."""
        if os.path.isfile(cls._credentials_file):
            os.remove(cls._credentials_file)

    def _save_credentials_to_file(self, credentials: Dict):
        """Save the credentials object to a file."""
        with open(self._credentials_file, "w") as outfile:
            json.dump(credentials, outfile)

    @classmethod
    def file_credentials_are_valid(cls) -> bool:
        """Check if the cached credentials exist and are valid."""
        if not os.path.isfile(cls._credentials_file):
            return False
        with open(cls._credentials_file, "r"):
            try:
                credentials = cls._get_credentials_from_file()
                expires_at = credentials["expires_at"]
            except (KeyError, ValueError):
                os.remove(cls._credentials_file)
                return False

            now = int(
                (
                    mktime(datetime.now().timetuple())
                    + datetime.now().microsecond / 1000000.0
                )
            )  # utc timestamp

        if now > expires_at:
            cls.reset_credentials()
            return False

        return True

    @classmethod
    def _get_credentials_from_file(cls) -> Dict:
        """Get user credentials from a cached file."""
        with open(cls._credentials_file, "r") as infile:
            result = json.load(infile)
        result = Client._check_keys_convert_types(result)
        return result

    def _get_credentials_from_web(self) -> Dict:
        """Get user credentials from a web sign-in."""
        print("Please go here and authorize:")
        print(self.login_page, flush=True)
        response = input("\nCopy and paste your credentials from the login page:\n")

        # Reformat response to dict
        credentials = dict(map(lambda x: x.split("="), response.split("&")))
        return credentials

    def _get_credentials_from_desktop_oauth(self) -> Dict:
        """Get user credentials using desktop OAuth flow with PKCE."""
        print("Starting desktop OAuth authentication flow...")

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

        print("Opening browser for authentication...")
        print(f"If browser doesn't open, visit: {auth_url}")
        webbrowser.open(auth_url)

        # Start local server to receive callback
        print(f"Waiting for authorization on port {self._local_port}...")
        self._authorization_code = self._wait_for_callback()

        if not self._authorization_code:
            raise ValueError("Failed to receive authorization code")

        # Exchange code for tokens
        print("Exchanging authorization code for tokens...")
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

        print("Authentication successful!")
        return credentials

    def _wait_for_callback(self) -> Optional[str]:
        """Start a local HTTP server to receive the OAuth callback."""
        authorization_code = None
        server_error = None

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                nonlocal authorization_code, server_error

                parsed_url = urlparse(handler_self.path)

                if parsed_url.path == "/callback":
                    params = parse_qs(parsed_url.query)

                    # Verify state parameter
                    received_state = params.get("state", [None])[0]
                    if received_state != self._state:
                        server_error = "State mismatch - possible CSRF attack"
                        handler_self.send_error(400, server_error)
                        return

                    # Check for errors
                    if "error" in params:
                        error = params["error"][0]
                        error_desc = params.get("error_description", [""])[0]
                        server_error = f"OAuth error: {error} - {error_desc}"
                        handler_self.send_error(400, server_error)
                        return

                    # Get authorization code
                    authorization_code = params.get("code", [None])[0]

                    if not authorization_code:
                        server_error = "No authorization code received"
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

            def log_message(self, *args):
                pass  # Suppress logging

        # Start server
        server = HTTPServer(("127.0.0.1", self._local_port), CallbackHandler)
        server.timeout = 120  # 2 minute timeout
        server.handle_request()
        server.server_close()

        if server_error:
            raise ValueError(server_error)

        return authorization_code

    def _exchange_code_for_tokens(self) -> Dict:
        """Exchange authorization code for tokens using the desktop endpoint."""
        import requests

        token_url = f"{self._api_root}/auth/desktop/token"
        data = {
            "code": self._authorization_code,
            "code_verifier": self._code_verifier,
            "redirect_uri": f"http://127.0.0.1:{self._local_port}/callback",
        }

        response = requests.post(token_url, json=data)

        if response.status_code != 200:
            error_msg = f"Token exchange failed: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('error', '')}: {error_data.get('error_description', '')}"
            except Exception:
                error_msg += f" - {response.text}"
            raise ValueError(error_msg)

        return response.json()

    def refresh_token(self) -> bool:
        """Refresh the access token using the refresh token.

        Returns:
            True if refresh successful, False otherwise
        """
        if "refresh_token" not in self._credentials:
            return False

        import requests

        refresh_url = f"{self._api_root}/auth/refresh"
        data = {
            "refresh_token": self._credentials["refresh_token"],
            "client_type": "desktop" if self._auth_flow == "desktop" else "web",
        }

        try:
            response = requests.post(refresh_url, json=data)

            if response.status_code != 200:
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

            return True

        except Exception:
            return False

    @staticmethod
    def _parse_credentials_string(credentials: str) -> Dict:
        """Parse a credentials string into a dictionary."""
        result = dict(map(lambda x: x.split("="), credentials.split("&")))
        result = Client._check_keys_convert_types(result)
        return result

    @staticmethod
    def _check_keys_convert_types(credentials: dict) -> dict:
        """Check that the credentials dict has the required keys and convert types."""
        missing_keys = [
            key
            for key in ["access_token", "token_type", "expires_at"]
            if key not in credentials
        ]
        if len(missing_keys) > 0:
            raise ValueError(
                f"Credentials string is missing required keys: {str(missing_keys)}."
            )

        # Convert expires_at to int
        credentials["expires_at"] = int(float(credentials["expires_at"]))

        # If expires_in is present, convert to int
        if "expires_in" in credentials:
            credentials["expires_in"] = int(float(credentials["expires_in"]))

        return credentials
