"""
Comprehensive Pytest suite for the hakai_api.Client class.

This suite uses mocking extensively to test the client's behavior in isolation,
without depending on a live API, the user's actual file system, or interactive input.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import pytest
from freezegun import freeze_time
from requests_oauthlib import OAuth2Session

from hakai_api import Client


@pytest.fixture
def valid_credentials_dict():
    """Provides a valid, non-expired credentials dictionary."""
    return {
        "access_token": "valid_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "valid_refresh_token",
        "scope": "read write",
        # Set expiration to a future timestamp
        "expires_at": int(time.time()) + 3600,
    }


@pytest.fixture
def valid_credentials_str(valid_credentials_dict):
    """Provides the string equivalent of the valid credentials dictionary."""
    return (
        f"access_token={valid_credentials_dict['access_token']}&"
        f"token_type={valid_credentials_dict['token_type']}&"
        f"expires_in={valid_credentials_dict['expires_in']}&"
        f"refresh_token={valid_credentials_dict['refresh_token']}&"
        f"scope={valid_credentials_dict['scope']}&"
        f"expires_at={valid_credentials_dict['expires_at']}"
    )


@pytest.fixture
def expired_credentials_dict():
    """Provides an expired credentials dictionary."""
    return {
        "access_token": "expired_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "expires_at": int(time.time()) - 3600,  # Expired in the past
    }


@pytest.fixture
def mock_home_dir(tmp_path, monkeypatch):
    """
    Fixture to mock the user's home directory and the credentials file path.
    This prevents tests from interacting with the actual ~/.hakai-api-auth file.
    """
    mock_creds_file = tmp_path / ".hakai-api-auth"

    # Patch the AuthStrategy base class to use the mock credentials file
    from hakai_api.auth.base import AuthStrategy

    def mock_init(self, api_root, credentials_file, **kwargs):
        self.api_root = api_root
        self.credentials_file = Path(mock_creds_file)

    monkeypatch.setattr(AuthStrategy, "__init__", mock_init)
    return Path(mock_creds_file)


class TestInitialization:
    """Tests the various paths through the Client.__init__ method."""

    def test_init_with_dict(self, mocker, valid_credentials_dict, mock_home_dir):
        m_super_init = mocker.spy(OAuth2Session, "__init__")
        client = Client(credentials=valid_credentials_dict)
        assert client.credentials == valid_credentials_dict
        m_super_init.assert_called_once_with(mocker.ANY, token=valid_credentials_dict)
        assert os.path.exists(mock_home_dir)

    def test_init_with_string(self, mocker, valid_credentials_str, mock_home_dir):
        m_super_init = mocker.spy(OAuth2Session, "__init__")
        client = Client(credentials=valid_credentials_str)
        creds = client.credentials
        assert creds["access_token"] == "valid_access_token"
        assert isinstance(creds["expires_at"], int)
        assert isinstance(creds["expires_in"], int)
        m_super_init.assert_called_once()
        assert os.path.exists(mock_home_dir)

    def test_init_with_env_var(self, monkeypatch, mocker, valid_credentials_str, mock_home_dir):
        monkeypatch.setenv(Client.CREDENTIALS_ENV_VAR, valid_credentials_str)
        m_super_init = mocker.spy(OAuth2Session, "__init__")
        client = Client()
        assert client.credentials["access_token"] == "valid_access_token"
        m_super_init.assert_called_once()
        assert os.path.exists(mock_home_dir)

    def test_init_with_valid_file_cache(self, mocker, valid_credentials_dict, mock_home_dir):
        with open(mock_home_dir, "w") as f:
            json.dump(valid_credentials_dict, f)
        m_super_init = mocker.spy(OAuth2Session, "__init__")
        client = Client()
        assert client.credentials["access_token"] == valid_credentials_dict["access_token"]
        m_super_init.assert_called_once()

    @freeze_time(datetime.now())
    def test_init_with_expired_file_cache_falls_back_to_web(
        self,
        mocker,
        monkeypatch,
        expired_credentials_dict,
        valid_credentials_str,
        mock_home_dir,
    ):
        with open(mock_home_dir, "w") as f:
            json.dump(expired_credentials_dict, f)
        mocker.patch("builtins.input", return_value=valid_credentials_str)
        m_super_init = mocker.spy(OAuth2Session, "__init__")
        client = Client()
        assert client.credentials["access_token"] == "valid_access_token"
        assert client.credentials["expires_at"] > time.time()
        m_super_init.assert_called_once()
        with open(mock_home_dir) as f:
            cached_creds = json.load(f)
            assert cached_creds["access_token"] == "valid_access_token"

    def test_init_with_web_fallback(self, mocker, monkeypatch, valid_credentials_str, mock_home_dir, capsys):
        mock_input = mocker.patch("builtins.input", return_value=valid_credentials_str)
        m_super_init = mocker.spy(OAuth2Session, "__init__")
        client = Client()
        assert client.credentials["access_token"] == "valid_access_token"
        assert isinstance(client.credentials["expires_at"], int)
        m_super_init.assert_called_once()
        mock_input.assert_called_once()
        assert os.path.exists(mock_home_dir)
        captured = capsys.readouterr()
        assert "Please go here and authorize:" in captured.out
        assert client.DEFAULT_LOGIN_PAGE in captured.out

    def test_init_failed_credentials(self, mocker, mock_home_dir):
        """Test that ValueError is raised if all credential methods fail."""
        # Simulate the web prompt failing by returning None, instead of
        # raising an error. This correctly tests the 'if self._credentials is None'
        # check inside __init__.
        mocker.patch.object(Client, "_get_credentials_from_web", return_value=None)

        with pytest.raises(ValueError, match="Credentials could not be set."):
            Client()
        assert not os.path.exists(mock_home_dir)

    def test_init_uses_custom_urls(self):
        api_root = "http://localhost:8000/api"
        login_page = "http://localhost:8000/login"
        client = Client(
            api_root=api_root,
            login_page=login_page,
            credentials={
                "access_token": "a",
                "token_type": "b",
                "expires_at": time.time() + 100,
            },
        )
        assert client.api_root == api_root
        assert client.login_page == login_page

    def test_init_user_agent_header(self, monkeypatch, valid_credentials_dict):
        client_default = Client(credentials=valid_credentials_dict)
        assert client_default.headers["User-Agent"] == "hakai-api-client-py"
        custom_agent = "my-custom-app/1.0"
        # Set with param
        client_custom = Client(credentials=valid_credentials_dict, user_agent="my-custom-app/1.0")
        assert client_custom.headers["User-Agent"] == custom_agent
        # Set with env variable
        monkeypatch.setenv(Client.USER_AGENT_ENV_VAR, custom_agent)
        client_custom = Client(credentials=valid_credentials_dict)
        assert client_custom.headers["User-Agent"] == custom_agent

    def test_init_user_credentials_file(self, monkeypatch, valid_credentials_dict):
        # Mock save_credentials_to_file to prevent file creation during tests
        from unittest.mock import Mock

        mock_save = Mock()
        monkeypatch.setattr("hakai_api.auth.base.AuthStrategy.save_credentials_to_file", mock_save)

        client_default = Client(credentials=valid_credentials_dict)
        assert client_default.credentials_file == str(Path.home() / ".hakai-api-auth")
        creds_file = str(Path.home() / ".custom_credentials")
        # Set with param
        client_custom = Client(credentials=valid_credentials_dict, credentials_file=creds_file)
        assert client_custom.credentials_file == creds_file
        # Set with env variable
        monkeypatch.setenv(Client.CREDENTIALS_ENV_VAR, creds_file)
        client_custom = Client(credentials=valid_credentials_dict)
        assert client_custom.credentials_file == creds_file


class TestStaticAndClassMethods:
    def test_parse_credentials_string(self, mocker, valid_credentials_dict):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        cred_str = "access_token=token&token_type=bearer&expires_at=1618956241.123&expires_in=3600.0"
        result = client._parse_credentials_string(cred_str)
        assert result["access_token"] == "token"
        assert result["expires_at"] == 1618956241
        assert isinstance(result["expires_at"], int)
        assert result["expires_in"] == 3600
        assert isinstance(result["expires_in"], int)

    def test_check_keys_convert_types_missing_key(self, mocker, valid_credentials_dict):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        bad_creds = {"access_token": "token"}
        with pytest.raises(ValueError) as excinfo:
            client._check_keys_convert_types(bad_creds)
        assert "missing required keys" in str(excinfo.value)

    @freeze_time(datetime.now())
    def test_file_credentials_are_valid(self, mocker, mock_home_dir, valid_credentials_dict):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        with open(mock_home_dir, "w") as f:
            json.dump(valid_credentials_dict, f)
        assert client.file_credentials_are_valid() is True

    @freeze_time(datetime.now())
    def test_file_credentials_are_not_valid_if_expired(
        self, mocker, mock_home_dir, expired_credentials_dict, valid_credentials_dict
    ):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        with open(mock_home_dir, "w") as f:
            json.dump(expired_credentials_dict, f)
        assert client.file_credentials_are_valid() is False
        assert not os.path.exists(mock_home_dir)

    def test_file_credentials_are_not_valid_if_no_file(self, mocker, mock_home_dir, valid_credentials_dict):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        # Remove the credentials file that was created during initialization
        os.remove(mock_home_dir)
        assert client.file_credentials_are_valid() is False

    def test_file_credentials_are_not_valid_if_malformed(self, mocker, mock_home_dir, valid_credentials_dict):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        with open(mock_home_dir, "w") as f:
            f.write('{"access_token": "token"}')
        assert client.file_credentials_are_valid() is False
        assert not os.path.exists(mock_home_dir)

        with open(mock_home_dir, "w") as f:
            f.write("this is not json")
        assert client.file_credentials_are_valid() is False
        assert not os.path.exists(mock_home_dir)

    def test_reset_credentials(self, mocker, mock_home_dir, valid_credentials_dict):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        with open(mock_home_dir, "w") as f:
            f.write("dummy content")
        assert os.path.exists(mock_home_dir)
        client.reset_credentials()
        assert not os.path.exists(mock_home_dir)

    def test_reset_credentials_no_file(self, mocker, mock_home_dir, valid_credentials_dict):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        # Remove the credentials file that was created during initialization
        os.remove(mock_home_dir)
        assert not os.path.exists(mock_home_dir)
        try:
            client.reset_credentials()
        except OSError:
            pytest.fail("client.reset_credentials() raised an unexpected error.")


class TestInternalMethods:
    def test_get_credentials_from_web(self, mocker, valid_credentials_str):
        client = Client(credentials=valid_credentials_str)
        mocker.patch("builtins.input", return_value=valid_credentials_str)
        creds = client._get_credentials_from_web()
        assert isinstance(creds, dict)
        assert creds["access_token"] == "valid_access_token"
        assert isinstance(creds["expires_at"], int)

    def test_get_credentials_from_file(self, mock_home_dir, valid_credentials_dict):
        # Create a client instance to test the instance method
        client = Client(credentials=valid_credentials_dict)
        with open(mock_home_dir, "w") as f:
            json.dump(valid_credentials_dict, f)
        creds = client._get_credentials_from_file()
        assert creds == valid_credentials_dict

    def test_save_credentials_to_file(self, mock_home_dir, valid_credentials_dict):
        """
        Test that _save_credentials_to_file correctly writes and overwrites
        the credentials file.
        """
        # 1. Initialize a client, which performs an initial save.
        client = Client(credentials=valid_credentials_dict)
        assert os.path.exists(mock_home_dir)

        # 2. Define a new credentials object to test overwriting.
        new_credentials = {
            "access_token": "new_and_improved_token",
            "token_type": "Bearer",
            "expires_at": int(time.time()) + 5000,
        }

        # 3. Explicitly call the method under test with the new credentials.
        # This is the key part that was missing before.
        client._save_credentials_to_file(new_credentials)

        # 4. Read the file back and assert it contains the new data.
        with open(mock_home_dir) as f:
            data_on_disk = json.load(f)

        assert data_on_disk != valid_credentials_dict
        assert data_on_disk == new_credentials


class TestProperties:
    @pytest.fixture
    def client(self, valid_credentials_dict):
        return Client(credentials=valid_credentials_dict)

    def test_properties_return_values(self, client, valid_credentials_dict):
        assert client.api_root == Client.DEFAULT_API_ROOT
        assert client.login_page == Client.DEFAULT_LOGIN_PAGE
        assert client.credentials == valid_credentials_dict

    def test_credentials_property_raises_error_if_not_set(self):
        client = Client.__new__(Client)
        client._credentials = None
        with pytest.raises(ValueError, match="Credentials have not been set."):
            _ = client.credentials
