"""Hakai API Python Client."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger
from requests_oauthlib import OAuth2Session

from .auth import DesktopAuthStrategy, WebAuthStrategy

if TYPE_CHECKING:
    from requests import Response


class Client(OAuth2Session):
    """Hakai API client for authenticated HTTP requests.

    Extends OAuth2Session to provide authenticated access to the Hakai API
    resource server. Handles OAuth2 credential management, caching, and
    automatic token refresh for seamless API interactions.

    The client supports two authentication flows:
    - Web flow: Copy/paste credentials from a web login page (default)
    - Desktop flow: OAuth2 with PKCE for native applications

    Credentials are automatically cached to the credentials_file for reuse
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

    DEFAULT_API_ROOT = "https://hecate.hakai.org/api"
    DEFAULT_LOGIN_PAGE = "https://hecate.hakai.org/api-client-login"
    CREDENTIALS_ENV_VAR = "HAKAI_API_CREDENTIALS"
    USER_AGENT_ENV_VAR = "HAKAI_API_USER_AGENT"

    def __init__(
        self,
        api_root: str = DEFAULT_API_ROOT,
        login_page: str = DEFAULT_LOGIN_PAGE,
        credentials: str | dict | None = None,
        credentials_file: str | Path | None = None,
        user_agent: str | None = None,
        auth_flow: Literal["web", "desktop"] = "web",
        local_port: int = 65500,
        use_refresh: bool = True,
        callback_timeout: int = 120,
    ) -> None:
        """Create a new Client class with credentials.

        Args:
            api_root: The base url of the hakai api you want to call.
                Defaults to the production server.
            login_page: The url of the login page to direct users to.
                Defaults to the production login page.
            credentials: Credentials token retrieved from the hakai api
                login page. If `None`, loads cached credentials or prompts for log in.
            credentials_file: The path to the file where credentials are saved. This will default to the path given by
                environment variable `HAKAI_API_CREDENTIALS`, if defined, else to `~/.hakai-api-auth`.
            user_agent: A user-agent string to use when requesting the hakai api to identify your application.
                This will default to the value given by environment variable `HAKAI_API_USER_AGENT`, if defined, else
                to `hakai-api-client-py`.
            auth_flow: Authentication flow type - "web" (default, copy/paste) or "desktop" (OAuth with PKCE).
                Only used if credentials are not provided.
            local_port: Port for local callback server in desktop flow (default 65500).
                Only used when auth_flow="desktop".
            use_refresh: Whether to use the refresh token to automatically extend user sessions.
                Currently only works for credentials obtained with the "desktop" authentication flow.
            callback_timeout: Timeout for detecting credentials in browser in seconds.

        Raises:
            ValueError: If credentials are unable to be set.
        """
        self._api_root = api_root
        self._login_page = login_page
        self._auth_flow = auth_flow
        self._local_port = local_port
        self._use_refresh = use_refresh

        if credentials_file is None:
            credentials_file = os.getenv(self.CREDENTIALS_ENV_VAR, Path.home() / ".hakai-api-auth")
        credentials_file = Path(credentials_file)

        if user_agent is None:
            user_agent = os.getenv(self.USER_AGENT_ENV_VAR, "hakai-api-client-py")

        # Create authentication strategy
        if auth_flow == "desktop":
            self._auth_strategy = DesktopAuthStrategy(
                api_root, local_port=local_port, credentials_file=credentials_file, callback_timeout=callback_timeout
            )
        else:
            self._auth_strategy = WebAuthStrategy(api_root, login_page=login_page, credentials_file=credentials_file)

        # Get credentials using strategy or provided values
        logger.trace(f"Initializing Hakai API client with auth_flow={auth_flow}")

        if isinstance(credentials, dict):
            logger.trace("Using provided credentials dictionary")
            # Validate and type-convert the provided credentials
            self._credentials = self._auth_strategy._check_keys_convert_types(credentials)
        elif isinstance(credentials, str):
            logger.trace("Parsing credentials from provided string")
            self._credentials = self._auth_strategy.parse_credentials_string(credentials)
        else:
            # Use strategy to get credentials (handles env vars and cached credentials properly)
            logger.trace(f"No credentials provided, using {auth_flow} authentication strategy")
            try:
                self._credentials = self._auth_strategy.get_credentials()
            except Exception as e:
                logger.error(f"Failed to get credentials from strategy: {e}")
                self._credentials = None

        if self._credentials is None:
            logger.error("Failed to obtain valid credentials from any source")
            raise ValueError("Credentials could not be set.")

        # Cache the credentials
        logger.trace(f"Caching credentials to file {self.credentials_file}")
        self._auth_strategy.save_credentials_to_file(self._credentials)

        # Init the OAuth2Session parent class with credentials
        super().__init__(token=self._credentials)

        # Set User-Agent header
        self.headers.update({"User-Agent": user_agent})
        logger.debug(f"Hakai API client initialized successfully with User-Agent: {user_agent}")

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

    def reset_credentials(self) -> None:
        """Remove the cached credentials file.

        Deletes the credentials file from the filesystem if it exists.
        """
        self._auth_strategy.reset_credentials()

    def file_credentials_are_valid(self) -> bool:
        """Check if the cached credentials exist and are valid.

        Validates that the credentials file exists, can be parsed,
        contains required fields, and has not expired.

        Returns:
            True if the credentials are valid, False otherwise.
        """
        return self._auth_strategy.file_credentials_are_valid()

    def refresh_token(self) -> bool:
        """Refresh the access token using the refresh token.

        Uses the stored refresh token to obtain a new access token from
        the API. Updates the stored credentials and OAuth2Session token
        if successful.

        Returns:
            True if refresh successful, False otherwise.
        """
        if "refresh_token" not in self._credentials:
            logger.trace("No refresh token available, cannot refresh")
            return False

        logger.trace("Attempting to refresh access token using auth strategy")

        # All strategies that support refresh tokens should have a refresh_token method
        if self._use_refresh:
            updated_credentials = self._auth_strategy.refresh_token(self._credentials)
            if updated_credentials:
                self._credentials = updated_credentials
                self._auth_strategy.save_credentials_to_file(self._credentials)
                self.token = self._credentials
                logger.trace("Access token refreshed successfully")
                return True

        logger.warning("Token refresh failed or is not supported by the current auth strategy")
        return False

    # Factory methods for easy client creation
    @classmethod
    def create_web_client(
        cls,
        api_root: str = DEFAULT_API_ROOT,
        login_page: str = DEFAULT_LOGIN_PAGE,
        credentials: str | dict | None = None,
    ) -> Client:
        """Create a client using web authentication flow.

        Args:
            api_root: The base url of the hakai api.
            login_page: The url of the login page to direct users to.
            credentials: Optional credentials to use.

        Returns:
            A Client configured for web authentication.
        """
        return cls(
            api_root=api_root,
            login_page=login_page,
            credentials=credentials,
            auth_flow="web",
        )

    @classmethod
    def create_desktop_client(
        cls,
        api_root: str = DEFAULT_API_ROOT,
        local_port: int = 65500,
        credentials: str | dict | None = None,
        callback_timeout: int = 120,
    ) -> Client:
        """Create a client using desktop OAuth authentication flow.

        Args:
            api_root: The base url of the hakai api.
            local_port: Port for local callback server.
            credentials: Optional credentials to use.
            callback_timeout: Timeout for detecting credentials in browser in seconds.

        Returns:
            A Client configured for desktop OAuth authentication.
        """
        return cls(
            api_root=api_root,
            credentials=credentials,
            auth_flow="desktop",
            local_port=local_port,
            callback_timeout=callback_timeout,
        )

    # Backward compatibility methods
    def _get_credentials_from_web(self) -> dict:
        """Backward compatibility method for getting credentials from web prompt.

        Returns:
            dict: Credentials dictionary from web authentication.

        Raises:
            TypeError: If auth_flow is not 'web'.
        """
        if not isinstance(self._auth_strategy, WebAuthStrategy):
            raise TypeError("_get_credentials_from_web is only available for 'web' auth_flow")
        return self._auth_strategy._get_credentials_from_web_input()

    def _save_credentials_to_file(self, credentials: dict) -> None:
        """Backward compatibility method for saving credentials to file."""
        self._auth_strategy.save_credentials_to_file(credentials)

    def _parse_credentials_string(self, credentials: str) -> dict:
        """Backward compatibility for parsing credentials string.

        Returns:
            dict: Parsed credentials dictionary.
        """
        return self._auth_strategy.parse_credentials_string(credentials)

    def _check_keys_convert_types(self, credentials: dict) -> dict:
        """Backward compatibility for checking keys and converting types.

        Returns:
            dict: Validated and type-converted credentials dictionary.
        """
        return self._auth_strategy._check_keys_convert_types(credentials)

    @property
    def credentials_file(self) -> str:
        """Backward compatibility property for credentials file path.

        Returns:
            The path to the credentials file.
        """
        return str(self._auth_strategy.credentials_file)

    def _get_credentials_from_file(self) -> dict:
        """Backward compatibility method for getting credentials from file.

        Returns:
            The contents of the credentials file as a dict.
        """
        return self._auth_strategy.get_credentials_from_file()

    def request(self, method: str, uri: str, **kwargs: dict[str, Any]) -> Response:
        """Override request method to handle 401 responses by re-authenticating.

        Args:
            method: HTTP method (GET, POST, etc.)
            uri: URI to request
            **kwargs: Additional arguments forwarded to requests.request().

        Returns:
            Response object
        """
        # Test for relative urls and prepend API root if needed
        if uri.startswith("/"):
            uri = f"{self.api_root}{uri}"

        # First attempt
        response = super().request(method, uri, **kwargs)

        # If we get a 401, try to re-authenticate once
        if response.status_code == 401:
            logger.warning("Received 401 Unauthorized, attempting to re-authenticate")

            # First try refresh token if available
            if "refresh_token" in self._credentials:
                logger.trace("Attempting token refresh")
                if self.refresh_token():
                    logger.trace("Token refresh successful, retrying request")
                    response = super().request(method, uri, **kwargs)
                    return response
                else:
                    logger.warning("Token refresh failed, falling back to full re-authentication")

            # If no refresh token or refresh failed, do full re-authentication
            logger.debug("Starting full re-authentication flow")

            # Clear cached credentials and get new ones
            self._auth_strategy.reset_credentials()

            try:
                # Get new credentials using the strategy
                self._credentials = self._auth_strategy.get_credentials()

                # Update the token for this session
                self.token = self._credentials

                # Cache the new credentials
                self._auth_strategy.save_credentials_to_file(self._credentials)

                # Retry the request with new credentials
                logger.trace("Re-authentication successful, retrying request")
                response = super().request(method, uri, **kwargs)

            except Exception as e:
                logger.error(f"Re-authentication failed: {e}")
                # Return the original 401 response if re-auth fails

        return response
