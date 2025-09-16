"""Web authentication strategy using copy/paste credentials."""

from __future__ import annotations

import os

from loguru import logger

from .base import AuthStrategy


class WebAuthStrategy(AuthStrategy):
    """Web authentication strategy using copy/paste from login page.

    This is the traditional authentication flow where users visit a login page,
    authenticate, and copy/paste the resulting credentials string.
    """

    def __init__(self, api_root: str, login_page: str, **kwargs: object) -> None:
        """Initialize the authentication strategy.

        Args:
            api_root: The base url of the hakai api.
            login_page: The url of the login page to direct users to.
            **kwargs: Additional parameters passed to the base authentication strategy.
        """
        super().__init__(api_root, **kwargs)
        self.login_page = login_page

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

        logger.trace("Parsing credentials from user input")
        try:
            # Reformat response to dict
            credentials = dict(map(lambda x: x.split("="), response.split("&")))
            credentials = self._check_keys_convert_types(credentials)
            logger.trace("Successfully parsed web credentials")
            return credentials
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to parse credentials from input: {e}")
            raise

    @property
    def client_type(self) -> str:
        """Get the client type for web authentication strategy."""
        return "web"

    # refresh_token method is now inherited from AuthStrategy base class
