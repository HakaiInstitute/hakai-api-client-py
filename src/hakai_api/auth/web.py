"""Web authentication strategy using copy/paste credentials."""

import json
import logging
import os

from .base import AuthStrategy

logger = logging.getLogger(__name__)


class WebAuthStrategy(AuthStrategy):
    """Web authentication strategy using copy/paste from login page.

    This is the traditional authentication flow where users visit a login page,
    authenticate, and copy/paste the resulting credentials string.
    """

    def get_credentials(self) -> dict:
        """Get user credentials from web sign-in flow.

        First checks for cached credentials, environment variables, or prompts
        for login if none are available.

        Returns:
            A dict containing the credentials parsed from user input or cache.
        """
        # Try environment variable first
        env_credentials = os.getenv("HAKAI_API_CREDENTIALS")
        if env_credentials is not None:
            logger.debug("Loading credentials from environment variable")
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
            logger.debug("Loading cached credentials from file")
            return self.get_credentials_from_file()

        # Prompt user for new credentials
        logger.info("No valid cached credentials found, starting web authentication flow")
        return self._get_credentials_from_web_input()

    def _get_credentials_from_web_input(self) -> dict:
        """Get user credentials from web sign-in with user input prompt.

        Prompts the user to copy and paste credentials from the login page.

        Returns:
            A dict containing the credentials parsed from user input.

        Raises:
            ValueError: If the input format is invalid or cannot be split properly.
            AttributeError: If the input string lacks expected string methods.
        """
        logger.info(f"Please go here and authorize: {self.login_page}")
        print(f"Please go here and authorize: {self.login_page}")
        response = input("\nCopy and paste your credentials from the login page here and press <enter>:\n")

        logger.debug("Parsing credentials from user input")
        try:
            # Reformat response to dict
            credentials = dict(map(lambda x: x.split("="), response.split("&")))
            credentials = self._check_keys_convert_types(credentials)
            logger.debug("Successfully parsed web credentials")
            return credentials
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to parse credentials from input: {e}")
            raise

    def refresh_token(self, credentials: dict) -> dict | None:
        """Refresh the access token using the refresh token.

        Args:
            credentials: Current credentials dictionary containing refresh_token.

        Returns:
            Updated credentials dictionary if successful, None otherwise.
        """
        if "refresh_token" not in credentials:
            logger.debug("No refresh token available, cannot refresh")
            return None

        logger.debug("Attempting to refresh access token")

        import requests

        refresh_url = f"{self.api_root}/auth/refresh"
        data = {
            "refresh_token": credentials["refresh_token"],
            "client_type": "web",
        }

        try:
            response = requests.post(refresh_url, json=data, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Token refresh failed with status {response.status_code}")
                return None

            new_tokens = response.json()

            # Update credentials
            updated_credentials = credentials.copy()
            updated_credentials["access_token"] = new_tokens["access_token"]
            updated_credentials["expires_at"] = new_tokens["expires_at"]
            updated_credentials["expires_in"] = new_tokens["expires_in"]

            logger.info("Access token refreshed successfully")
            return updated_credentials

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Token refresh failed with exception: {e}")
            return None
