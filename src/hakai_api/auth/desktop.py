"""Desktop OAuth authentication strategy with PKCE."""

from __future__ import annotations

import json
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import pkce
import requests
from loguru import logger

from .base import AuthStrategy


class DesktopAuthStrategy(AuthStrategy):
    """Desktop OAuth authentication strategy using PKCE flow.

    This strategy implements the OAuth2 Authorization Code flow with PKCE
    (Proof Key for Code Exchange) for native desktop applications.
    """

    def __init__(self, api_root: str, local_port: int = 65500, callback_timeout: int = 120, **kwargs: object) -> None:
        """Initialize the desktop authentication strategy.

        Args:
            api_root: The base url of the hakai api.
            local_port: Port for local callback server.
            callback_timeout: Timeout for callback server in seconds.
            **kwargs: Additional parameters.
        """
        super().__init__(api_root, **kwargs)
        self.local_port = local_port

        # OAuth state variables
        self._state = None
        self._code_verifier = None
        self._authorization_code = None
        self._callback_timeout = callback_timeout

    def get_credentials(self) -> dict:
        """Get user credentials using desktop OAuth flow with PKCE.

        First checks for cached credentials, environment variables, or initiates
        the OAuth flow if none are available.

        Returns:
            A dict containing the credentials.
        """
        # Try environment variable first
        env_credentials = os.getenv("HAKAI_API_CREDENTIALS")
        if env_credentials is not None:
            logger.trace("Loading credentials from environment variable")
            try:
                parsed_creds = self.parse_credentials_string(env_credentials)
                # Check if environment credentials are expired
                if self._are_credentials_expired(parsed_creds):
                    logger.warning("Environment variable credentials have expired")
                else:
                    return parsed_creds
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid environment variable credentials: {e}")

        # Try cached credentials
        if self.file_credentials_are_valid():
            logger.trace("Loading cached credentials from file")
            return self.get_credentials_from_file()

        # Start OAuth flow
        logger.debug("No valid cached credentials found, starting desktop authentication flow")
        return self._get_credentials_from_desktop_oauth()

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
        params = {
            "redirect_uri": f"http://127.0.0.1:{self.local_port}/callback",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": self._state,
        }

        # Use the desktop auth endpoint
        auth_url = f"{self.api_root}/auth/desktop?{urlencode(params)}"

        webbrowser.open(auth_url)

        # Start local server to receive callback
        logger.trace(f"Starting local callback server on port {self.local_port}")
        self._authorization_code = self._wait_for_callback()

        if not self._authorization_code:
            logger.error("Failed to receive authorization code from OAuth callback")
            raise ValueError("Failed to receive authorization code")

        logger.trace("Successfully received authorization code, exchanging for tokens")
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
            logger.trace("Desktop OAuth completed successfully with refresh token")
        else:
            logger.trace("Desktop OAuth completed successfully without refresh token")

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

        def _get_callback_html() -> str:
            """Load the HTML callback page from file.

            Returns:
                The HTML callback page.
            """
            from pathlib import Path

            html_file = Path(__file__).parent / "desktop_callback.html"
            try:
                with html_file.open("r", encoding="utf-8") as f:
                    return f.read()
            except (OSError, FileNotFoundError) as e:
                logger.error(f"Could not load desktop_callback.html: {e}")

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

                    success_html = _get_callback_html()
                    handler_self.wfile.write(success_html.encode())
                else:
                    handler_self.send_error(404, "Not found")

            def log_message(self, *args: list[Any] | None) -> None:
                pass  # Suppress logging

        # Start server
        server = HTTPServer(("127.0.0.1", self.local_port), CallbackHandler)
        server.timeout = self._callback_timeout
        server.handle_request()
        server.server_close()

        if server_error:
            logger.error(f"OAuth callback server error: {server_error}")
            raise ValueError(server_error)

        logger.trace("OAuth callback received successfully")
        return authorization_code

    def _exchange_code_for_tokens(self) -> dict:
        """Exchange authorization code for tokens using the desktop endpoint.

        Returns:
            A dictionary containing the authorization code (JWT token).

        Raises:
            ValueError: If the authorization code is invalid.
        """
        token_url = f"{self.api_root}/auth/desktop/token"
        data = {
            "code": self._authorization_code,
            "code_verifier": self._code_verifier,
            "redirect_uri": f"http://127.0.0.1:{self.local_port}/callback",
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

        logger.debug("Successfully exchanged authorization code for tokens")
        return response.json()

    @property
    def client_type(self) -> str:
        """Get the client type for desktop authentication strategy."""
        return "desktop"

    # refresh_token method is now inherited from AuthStrategy base class
