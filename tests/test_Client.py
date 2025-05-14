import os
from datetime import datetime

from hakai_api import Client


def test_get_valid_credentials_from_file():
    """Test that credentials can be read from a file."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Create a client object
    now = datetime.now()
    client = Client(
        credentials={
            "token_type": "Bearer",
            "access_token": "test_access_token",
            "expires_in": 3600,
            "expires_at": now.timestamp() + 3600,
        }
    )

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
    client = Client(
        credentials={
            "token_type": "Bearer",
            "access_token": "test_access_token",
            "expires_in": 3600,
            "expires_at": now.timestamp() - 3600,
        }
    )

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
    client = Client(
        credentials={
            "token_type": "Bearer",
            "access_token": "test_access_token",
            "expires_in": 3600,
            "expires_at": now.timestamp() + 3600,
        },
        api_root="https://example.com/api",
    )

    # Check that api root is set
    assert client.api_root == "https://example.com/api"


def test_custom_login_page():
    """Test that a customized login page can be set."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Create a client object
    now = datetime.now()
    client = Client(
        credentials={
            "token_type": "Bearer",
            "access_token": "test_access_token",
            "expires_in": 3600,
            "expires_at": now.timestamp() + 3600,
        },
        login_page="https://example.com/login",
    )

    # Check that login page is set
    assert client.login_page == "https://example.com/login"


def test_credentials_from_env_variable():
    """Test setting credentials with HAKAI_API_CREDENTIALS environment variable."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Create a client object
    now = datetime.now()
    os.environ["HAKAI_API_CREDENTIALS"] = "&".join(
        [
            "token_type=Bearer",
            "access_token=test_access_token",
            f"expires_at={now.timestamp() + 3600}",
        ]
    )
    client = Client()

    assert client.credentials is not None

    # Check that credentials are cached and valid
    assert client.file_credentials_are_valid()

    # Check that the cached credentials can be read
    credentials = client._get_credentials_from_file()
    assert credentials is not None

    # Check that credentials can be deleted
    Client.reset_credentials()
    assert not client.file_credentials_are_valid()
    assert not os.path.exists(client._credentials_file)

    # Remove the environment variable
    del os.environ["HAKAI_API_CREDENTIALS"]


def test_user_agent_header():
    """Test that User-Agent header is correctly set."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Make sure environment variable is not set for this test
    if Client.USER_AGENT_ENV_VAR in os.environ:
        del os.environ[Client.USER_AGENT_ENV_VAR]

    # Create a client object with default User-Agent
    now = datetime.now()
    client = Client(
        credentials={
            "token_type": "Bearer",
            "access_token": "test_access_token",
            "expires_in": 3600,
            "expires_at": now.timestamp() + 3600,
        },
    )

    # Check that the default User-Agent header is set correctly
    assert "User-Agent" in client.headers
    assert client.headers["User-Agent"] == "hakai-api-client-py"

    # Test with a custom User-Agent set via environment variable
    custom_agent = "these-are-not-the-droids-you-are-looking-for"
    os.environ[Client.USER_AGENT_ENV_VAR] = custom_agent

    # Create a new client with the environment variable set
    client_env = Client(
        credentials={
            "token_type": "Bearer",
            "access_token": "test_access_token",
            "expires_in": 3600,
            "expires_at": now.timestamp() + 3600,
        },
    )

    # Check that the custom User-Agent header from env var is set correctly
    assert "User-Agent" in client_env.headers
    assert client_env.headers["User-Agent"] == custom_agent

    # Clean up - remove the environment variable
    del os.environ[Client.USER_AGENT_ENV_VAR]
