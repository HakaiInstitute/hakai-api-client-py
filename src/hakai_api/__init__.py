"""Hakai API Python Client.

A Python library for making authenticated HTTP requests to the Hakai API
resource server. Extends the functionality of the Python requests library
to supply Hakai OAuth2 credentials with URL requests.

The client supports both web-based authentication (copy/paste credentials)
and desktop OAuth2 flows with PKCE for secure credential management.

Example:
    Basic usage:

    >>> from hakai_api import Client
    >>> client = Client()
    >>> response = client.get("/eims/views/output/stations")
    >>> data = response.json()

Classes:
    Client: Main API client class for authenticated requests.
"""

from hakai_api.client import Client

__all__ = ["Client"]
