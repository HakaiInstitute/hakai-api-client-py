"""Get authorized requests to the Hakai API using the requests library.

Written by: Taylor Denouden, Chris Davis, and Nate Rosenstock
Last updated: April 2021
"""

import os
import pickle
from datetime import datetime
from time import mktime, sleep
from typing import Dict, Union

from pytz import utc
from requests_oauthlib import OAuth2Session


class Client(OAuth2Session):
    _credentials_file = os.path.expanduser("~/.hakai-api-auth")

    def __init__(
        self,
        api_root: str = "https://hecate.hakai.org/api",
        login_page: str = "https://hecate.hakai.org/api-client-login",
        credentials: Union[str,Dict] = None,
    ):
        """Create a new Client class with credentials.

        Params:
            api_root: The base url of the hakai api you want to call.
                      Defaults to the production server.
            credentials (str, Dict): Credentials token retrieved from 
                                     the hakai api login page.
                                     Defaults to the cached credentials or prompt
        """     
        self._api_root = api_root
        self._authorization_base_url = login_page

        # Load credentials from input or file
        if isinstance(credentials, str):
            credentials = dict(map(lambda x: x.split("="), credentials.split("&")))
            
        if credentials is None:
            # Try to get cached credentials
            credentials = self._try_to_load_credentials()
        else:
            self._save_credentials(credentials)

        if credentials:
            self._credentials = credentials
        else:
            # Acquire and store credentials from web sign-in.
            credentials = self._get_credentials_from_web()
            # Cache the credentials
            self._save_credentials(credentials)
            self._credentials = credentials

        # Init the OAuth2Session parent class with credentials
        super(Client, self).__init__(token=self._credentials)

    @property
    def api_root(self) -> str:
        """Return the api base url."""
        return self._api_root

    @property
    def credentials(self) -> Dict:
        """Return the credentials object."""
        return self._credentials

    @classmethod
    def reset_credentials(cls):
        if os.path.isfile(cls._credentials_file):
            os.remove(cls._credentials_file)

    def _save_credentials(self, credentials: Dict):
        """Save the credentials object to a file."""
        with open(self._credentials_file, "wb") as outfile:
            pickle.dump(credentials, outfile)

    def _try_to_load_credentials(self) -> Union[Dict, bool]:
        """Try to load the cached credentials file."""
        if not os.path.isfile(self._credentials_file):
            return False

        with open(self._credentials_file, "rb") as infile:
            try:
                credentials = pickle.load(infile)
                expires_at = int(credentials["expires_at"])
            except (KeyError, ValueError):
                os.remove(self._credentials_file)
                return False

            now = int(
                (
                    mktime(datetime.now(tz=utc).timetuple())
                    + datetime.now(tz=utc).microsecond / 1000000.0
                )
            )  # utc timestamp

            if now > expires_at:
                os.remove(self._credentials_file)
                return False

            return credentials

    def _get_credentials_from_web(self) -> Dict:
        """Get user credentials from a web sign-in."""
        print("Please go here and authorize:")
        print(self._authorization_base_url)

        sleep(0.05)  # Workaround for input / print stream race condition
        response = input("\nCopy and past your credentials from the login page:\n")

        # Reformat response to dict
        credentials = dict(map(lambda x: x.split("="), response.split("&")))
        return credentials
