"""Base authentication strategy interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from time import mktime
from typing import TYPE_CHECKING

import requests
from loguru import logger

if TYPE_CHECKING:
    from pathlib import Path


class AuthStrategy(ABC):
    """Abstract base class for authentication strategies."""

    def __init__(self, api_root: str, credentials_file: Path, **kwargs: object) -> None:
        """Initialize the authentication strategy.

        Args:
            api_root: The base url of the hakai api.
            login_page: The url of the login page to direct users to.
            credentials_file: The path to the credentials file.
            **kwargs: Additional strategy-specific parameters.
        """
        self.api_root = api_root
        self.credentials_file = credentials_file

    @abstractmethod
    def get_credentials(self) -> dict:
        """Get authentication credentials using this strategy.

        Returns:
            A dictionary containing the authentication credentials.

        Raises:
            ValueError: If credentials could not be obtained.
        """
        pass

    @property
    @abstractmethod
    def client_type(self) -> str:
        """Get the client type for this authentication strategy.

        Returns:
            The client type string (e.g., 'web', 'desktop').
        """
        pass

    def save_credentials_to_file(self, credentials: dict) -> None:
        """Save the credentials object to a file.

        Args:
            credentials: Credentials object.

        Raises:
            OSError: If file cannot be created or written to.
            TypeError: If credentials cannot be serialized to JSON.
        """
        try:
            # Ensure parent directory exists
            self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
            with self.credentials_file.open("w") as outfile:
                json.dump(credentials, outfile)
            logger.trace(f"Credentials saved to {self.credentials_file}")
        except (OSError, TypeError) as e:
            logger.error(f"Failed to save credentials to file: {e}")
            raise

    def get_credentials_from_file(self) -> dict:
        """Get user credentials from a cached file.

        Loads and validates credentials from the cached credentials file.

        Returns:
            A dict containing the credentials with required keys and proper types.
        """
        with self.credentials_file.open() as infile:
            result = json.load(infile)
        result = self._check_keys_convert_types(result)
        return result

    def file_credentials_are_valid(self) -> bool:
        """Check if the cached credentials exist and are valid.

        Validates that the credentials file exists, can be parsed,
        contains required fields, and has not expired.

        Returns:
            True if the credentials are valid, False otherwise.
        """
        if not self.credentials_file.is_file():
            logger.trace("No cached credentials file found")
            return False

        try:
            credentials = self.get_credentials_from_file()
            expires_at = credentials["expires_at"]
        except (KeyError, ValueError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"Invalid cached credentials file, removing: {e}")
            try:
                self.credentials_file.unlink()
            except OSError:
                pass  # File might already be gone
            return False

        now = int(mktime(datetime.now().timetuple()) + datetime.now().microsecond / 1000000.0)

        if now > expires_at:
            logger.debug("Cached credentials have expired, removing")
            self.reset_credentials()
            return False

        logger.trace("Cached credentials are valid")
        return True

    def reset_credentials(self) -> None:
        """Remove the cached credentials file.

        Deletes the credentials file from the filesystem if it exists.
        """
        if self.credentials_file.is_file():
            logger.debug("Removing cached credentials file")
            self.credentials_file.unlink()
        else:
            logger.trace("No cached credentials file to remove")

    def parse_credentials_string(self, credentials: str) -> dict:
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
        logger.trace("Parsing credentials string")
        try:
            result = dict(map(lambda x: x.split("="), credentials.split("&")))
            result = self._check_keys_convert_types(result)
            logger.trace("Successfully parsed and validated credentials string")
            return result
        except (ValueError, AttributeError, KeyError) as e:
            logger.error(f"Failed to parse credentials string: {e}")
            raise

    def _check_keys_convert_types(self, credentials: dict) -> dict:
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
            logger.trace(f"Credentials expire at timestamp: {credentials['expires_at']}")
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

    def _are_credentials_expired(self, credentials: dict) -> bool:
        """Check if the provided credentials are expired.

        Args:
            credentials: Credentials dictionary to check.

        Returns:
            True if credentials are expired, False otherwise.
        """
        try:
            expires_at = credentials.get("expires_at")
            if expires_at is None:
                return False  # If no expiry, assume valid

            now = int(mktime(datetime.now().timetuple()) + datetime.now().microsecond / 1000000.0)
            return now > expires_at
        except (TypeError, ValueError):
            return True  # If we can't parse the expiry, consider it expired

    def refresh_token(self, credentials: dict) -> dict | None:
        """Refresh the access token using the refresh token.

        Args:
            credentials: Current credentials dictionary containing refresh_token.

        Returns:
            Updated credentials dictionary if successful, None otherwise.
        """
        if "refresh_token" not in credentials:
            logger.trace("No refresh token available, cannot refresh")
            return None

        logger.trace("Attempting to refresh access token")

        refresh_url = f"{self.api_root}/auth/refresh"
        data = {
            "refresh_token": credentials["refresh_token"],
            "client_type": self.client_type,
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

            logger.trace("Access token refreshed successfully")
            return updated_credentials

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Token refresh failed with exception: {e}")
            return None
