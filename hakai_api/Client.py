"""Get authorized requests to the Hakai API using the requests library.

Written by: Taylor Denouden, Chris Davis, and Nate Rosenstock
Last updated: April 2021
"""

import json
import os
from datetime import datetime
from time import mktime
from typing import Dict, Union

from requests_oauthlib import OAuth2Session


class Client(OAuth2Session):
    _credentials_file = os.path.expanduser("~/.hakai-api-auth")
    DEFAULT_API_ROOT = "https://hecate.hakai.org/api"
    DEFAULT_LOGIN_PAGE = "https://hecate.hakai.org/api-client-login"

    def __init__(
            self,
            api_root: str = DEFAULT_API_ROOT,
            login_page: str = DEFAULT_LOGIN_PAGE,
            credentials: Union[str, Dict] = None,
    ):
        """Create a new Client class with credentials.

        Params:
            api_root: The base url of the hakai api you want to call.
                      Defaults to the production server.
            credentials (str, Dict): Credentials token retrieved from the hakai api login page.
                                     If `None`, loads cached credentials or prompts for log in.
        """
        self._api_root = api_root
        self._login_page = login_page
        self._credentials = None

        if isinstance(credentials, dict):
            self._credentials = credentials
        elif isinstance(credentials, str):
            # Parse credentials from string
            self._credentials = dict(
                map(lambda x: x.split("="), credentials.split("&")))
        elif self.file_credentials_are_valid():
            self._credentials = self._get_credentials_from_file()
        else:
            self._credentials = self._get_credentials_from_web()

        if self._credentials is None:
            raise ValueError("Credentials could not be set.")

        # Cache the credentials
        self._save_credentials_to_file(self._credentials)

        # Init the OAuth2Session parent class with credentials
        super(Client, self).__init__(token=self._credentials)

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

        with open(cls._credentials_file, "rb"):
            try:
                credentials = cls._get_credentials_from_file()
                expires_at = int(credentials["expires_at"])
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
                os.remove(cls._credentials_file)
                return False

        return True

    @classmethod
    def _get_credentials_from_file(cls) -> Dict:
        """Get user credentials from a cached file."""
        with open(cls._credentials_file, "rb") as infile:
            return json.load(infile)

    def _get_credentials_from_web(self) -> Dict:
        """Get user credentials from a web sign-in."""
        print("Please go here and authorize:")
        print(self.login_page, flush=True)
        response = input("\nCopy and past your credentials from the login page:\n")

        # Reformat response to dict
        credentials = dict(map(lambda x: x.split("="), response.split("&")))
        return credentials
