import os
from datetime import datetime

from hakai_api import Client


def test_get_valid_credentials_from_file():
    """Test that credentials can be read from a file."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Create a client object
    now = datetime.now()
    client = Client(credentials={
        "token_type": "Bearer",
        "access_token": "test_access_token",
        "expires_in": 3600,
        "expires_at": now.timestamp() + 3600,
    })

    # Check that the credentials are cached
    assert client.credentials is not None

    # Check that the cached credentials are valid
    assert client.file_credentials_are_valid()

    # Check that the cached credentials can be read
    credentials = client._get_credentials_from_file()
    assert credentials is not None

    # Check that credentials can be deleted
    Client.reset_credentials()
    assert not client.file_credentials_are_valid()
    assert not os.path.exists(client._credentials_file)


def test_expired_credentials_are_handled():
    """Test that expired credentials are removed properly."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Create a client object
    now = datetime.now()
    client = Client(credentials={
        "token_type": "Bearer",
        "access_token": "test_access_token",
        "expires_in": 3600,
        "expires_at": now.timestamp() - 3600,
    })

    # Check that the credentials are cached
    assert client.credentials is not None

    # Check that the cached credentials are not valid
    assert not client.file_credentials_are_valid()

    # Check that the cached credentials were deleted
    assert not os.path.exists(client._credentials_file)


def test_custom_api_root():
    """Test that a customized api root can be set."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Create a client object
    now = datetime.now()
    client = Client(credentials={
        "token_type": "Bearer",
        "access_token": "test_access_token",
        "expires_in": 3600,
        "expires_at": now.timestamp() + 3600,
    }, api_root='https://example.com/api')

    # Check that api root is set
    assert client.api_root == 'https://example.com/api'


def test_custom_login_page():
    """Test that a customized login page can be set."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Create a client object
    now = datetime.now()
    client = Client(credentials={
        "token_type": "Bearer",
        "access_token": "test_access_token",
        "expires_in": 3600,
        "expires_at": now.timestamp() + 3600,
    }, login_page='https://example.com/login')

    # Check that login page is set
    assert client.login_page == 'https://example.com/login'
