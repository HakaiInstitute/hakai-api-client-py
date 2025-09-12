from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from time import mktime
from typing import Any, NoReturn
from unittest.mock import Mock, patch

import pytest

from hakai_api import Client
from src.hakai_api.auth.web import WebAuthStrategy


def test_get_valid_credentials_from_file():
    """Test that credentials can be read from a file."""
    # Remove the cached credentials file if it exists
    Client.reset_credentials()

    # Create a client object
    now = datetime.now(timezone.utc)
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
    now = datetime.now(timezone.utc)
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
    now = datetime.now(timezone.utc)
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
    now = datetime.now(timezone.utc)
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
    now = datetime.now(timezone.utc)
    os.environ["HAKAI_API_CREDENTIALS"] = "&".join([
        "token_type=Bearer",
        "access_token=test_access_token",
        f"expires_at={now.timestamp() + 3600}",
        "expires_in=3600",
    ])
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
    now = datetime.now(timezone.utc)
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


@pytest.fixture
def temp_credentials_file():
    """Create a temporary credentials file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_file = f.name

    yield temp_file

    # Cleanup
    try:
        os.unlink(temp_file)
    except OSError:
        pass


@pytest.fixture
def valid_credentials():
    """Sample valid credentials for testing."""
    future_timestamp = int(mktime(datetime.now(timezone.utc).timetuple()) + 3600)
    return {
        "access_token": "valid_token",
        "token_type": "Bearer",
        "expires_at": future_timestamp,
        "expires_in": 3600,
    }


@pytest.fixture
def expired_credentials():
    """Sample expired credentials for testing."""
    now_utc = datetime.now(timezone.utc)
    past_timestamp = int(now_utc.timestamp() - 3600)  # Use UTC timestamp
    return {
        "access_token": "expired_token",
        "token_type": "Bearer",
        "expires_at": past_timestamp,
        "expires_in": 3600,
    }


@pytest.fixture
def credentials_with_refresh():
    """Sample credentials with refresh token."""
    future_timestamp = int(mktime(datetime.now(timezone.utc).timetuple()) + 3600)
    return {
        "access_token": "token_with_refresh",
        "token_type": "Bearer",
        "expires_at": future_timestamp,
        "expires_in": 3600,
        "refresh_token": "refresh_token_123",
    }


class TestClientCredentialScenarios:
    """Test various credential scenarios."""

    def test_valid_credentials_no_401(self, valid_credentials):
        """Test client with valid credentials that don't trigger 401."""
        with patch("requests_oauthlib.OAuth2Session.request") as mock_request:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"user": "test@example.com"}
            mock_request.return_value = mock_response

            # Create client with valid credentials
            client = Client(credentials=valid_credentials)

            # Make request
            response = client.request("GET", "/whoami")

            # Should get successful response without re-authentication
            assert response.status_code == 200
            assert mock_request.call_count == 1  # Only one call, no retry
            assert client.credentials["access_token"] == "valid_token"  # noqa: S105

    def test_401_response_with_refresh_token_success(self, credentials_with_refresh):
        """Test 401 response with successful token refresh."""
        call_count = 0

        def mock_request(method, uri, **kwargs: dict[str, Any]):
            nonlocal call_count
            call_count += 1

            mock_response = Mock()
            if call_count == 1:
                # First call returns 401
                mock_response.status_code = 401
                mock_response.json.return_value = {"error": "token expired"}
            else:
                # Second call after refresh returns success
                mock_response.status_code = 200
                mock_response.json.return_value = {"user": "test@example.com"}

            return mock_response

        def mock_refresh_success() -> bool:
            # Mock successful token refresh
            return True

        with patch("requests_oauthlib.OAuth2Session.request", side_effect=mock_request):
            client = Client(credentials=credentials_with_refresh)

            # Mock the refresh_token method to succeed
            with patch.object(client, "refresh_token", side_effect=mock_refresh_success):
                response = client.request("GET", "/whoami")

                # Should get successful response after refresh
                assert response.status_code == 200
                assert call_count == 2  # Two calls: original + retry after refresh

    def test_401_response_with_refresh_token_failure_fallback_to_reauth(self, credentials_with_refresh):
        """Test 401 response with failed token refresh, falling back to full re-authentication."""
        call_count = 0

        def mock_request(method, uri, **kwargs: dict[str, Any]):
            nonlocal call_count
            call_count += 1

            mock_response = Mock()
            if call_count == 1:
                # First call returns 401
                mock_response.status_code = 401
                mock_response.json.return_value = {"error": "token expired"}
            else:
                # Second call after full re-auth returns success
                mock_response.status_code = 200
                mock_response.json.return_value = {"user": "test@example.com"}

            return mock_response

        def mock_refresh_failure() -> bool:
            # Mock failed token refresh
            return False

        def mock_get_credentials():
            # Mock getting new credentials from strategy
            return {
                "access_token": "new_token",
                "token_type": "Bearer",
                "expires_at": int(mktime(datetime.now(timezone.utc).timetuple()) + 3600),
                "expires_in": 3600,
            }

        with patch("requests_oauthlib.OAuth2Session.request", side_effect=mock_request):
            client = Client(credentials=credentials_with_refresh)

            # Mock refresh to fail, then full re-auth to succeed
            with patch.object(client, "refresh_token", side_effect=mock_refresh_failure):
                with patch.object(client._auth_strategy, "get_credentials", side_effect=mock_get_credentials):
                    response = client.request("GET", "/whoami")

                    # Should get successful response after full re-auth
                    assert response.status_code == 200
                    assert call_count == 2  # Two calls: original + retry after re-auth
                    assert client.credentials["access_token"] == "new_token"

    def test_401_response_without_refresh_token_reauth(self, valid_credentials):
        """Test 401 response without refresh token, triggering full re-authentication."""
        call_count = 0

        def mock_request(method, uri, **kwargs: dict[str, Any]):
            nonlocal call_count
            call_count += 1

            mock_response = Mock()
            if call_count == 1:
                # First call returns 401
                mock_response.status_code = 401
                mock_response.json.return_value = {"error": "token expired"}
            else:
                # Second call after re-auth returns success
                mock_response.status_code = 200
                mock_response.json.return_value = {"user": "test@example.com"}

            return mock_response

        def mock_get_credentials():
            # Mock getting new credentials from strategy
            return {
                "access_token": "new_token",
                "token_type": "Bearer",
                "expires_at": int(mktime(datetime.now(timezone.utc).timetuple()) + 3600),
                "expires_in": 3600,
            }

        with patch("requests_oauthlib.OAuth2Session.request", side_effect=mock_request):
            client = Client(credentials=valid_credentials)  # No refresh token

            with patch.object(client._auth_strategy, "get_credentials", side_effect=mock_get_credentials):
                response = client.request("GET", "/whoami")

                # Should get successful response after re-auth
                assert response.status_code == 200
                assert call_count == 2  # Two calls: original + retry after re-auth
                assert client.credentials["access_token"] == "new_token"

    def test_401_response_reauth_failure_returns_original_401(self, valid_credentials):
        """Test 401 response where re-authentication fails, should return original 401."""
        call_count = 0

        def mock_request(method, uri, **kwargs: dict[str, Any]):
            nonlocal call_count
            call_count += 1

            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "token expired"}

            return mock_response

        def mock_get_credentials() -> NoReturn:
            # Mock re-authentication failure
            raise ValueError("Re-authentication failed")

        with patch("requests_oauthlib.OAuth2Session.request", side_effect=mock_request):
            client = Client(credentials=valid_credentials)

            with patch.object(client._auth_strategy, "get_credentials", side_effect=mock_get_credentials):
                response = client.request("GET", "/whoami")

                # Should return original 401 response
                assert response.status_code == 401
                assert call_count == 1  # Only one call, no retry due to re-auth failure

    def test_expired_cached_credentials_are_rejected(self, temp_credentials_file, expired_credentials):
        """Test that expired cached credentials are automatically rejected."""
        # Save expired credentials to file
        with open(temp_credentials_file, "w") as f:
            json.dump(expired_credentials, f)

        def mock_get_credentials():
            # Mock strategy returning fresh credentials
            now_utc = datetime.now(timezone.utc)
            return {
                "access_token": "fresh_token",
                "token_type": "Bearer",
                "expires_at": int(now_utc.timestamp() + 3600),  # Use UTC timestamp
                "expires_in": 3600,
            }

        def mock_save_credentials(credentials):
            # Save the fresh credentials to our temp file
            with open(temp_credentials_file, "w") as f:
                json.dump(credentials, f)

        # Remove any existing default cached credentials first
        default_creds_file = os.path.expanduser("~/.hakai-api-auth")
        if os.path.exists(default_creds_file):
            os.remove(default_creds_file)

        # Mock the auth strategy creation to use our temp file
        original_init = WebAuthStrategy.__init__

        def mock_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.credentials_file = temp_credentials_file

        with patch.object(WebAuthStrategy, "__init__", mock_init):
            with patch(
                "hakai_api.auth.web.WebAuthStrategy._get_credentials_from_web_input",
                side_effect=mock_get_credentials,
            ):
                with patch.object(WebAuthStrategy, "save_credentials_to_file", mock_save_credentials):
                    client = Client()

                    # Should have fresh credentials, not the expired ones
                    assert client.credentials["access_token"] == "fresh_token"
                    # File should now contain fresh credentials, not expired ones
                    with open(temp_credentials_file) as f:
                        cached_creds = json.load(f)
                    assert cached_creds["access_token"] == "fresh_token"

    @patch.dict(os.environ, {}, clear=True)  # Clear environment
    def test_expired_env_credentials_are_rejected(self):
        """Test that expired environment credentials are rejected."""
        # Set expired credentials in environment
        now_utc = datetime.now(timezone.utc)
        past_timestamp = int(now_utc.timestamp() - 3600)  # Use UTC timestamp
        expired_env_creds = (
            f"access_token=expired_env_token&token_type=Bearer&expires_at={past_timestamp}&expires_in=3600"
        )

        def mock_get_credentials():
            # Mock strategy returning fresh credentials after rejecting expired env vars
            return {
                "access_token": "fresh_token_after_env_rejection",
                "token_type": "Bearer",
                "expires_at": int(now_utc.timestamp() + 3600),  # Use UTC timestamp
                "expires_in": 3600,
            }

        # Remove any existing cached credentials first
        cached_creds_file = os.path.expanduser("~/.hakai-api-auth")
        if os.path.exists(cached_creds_file):
            os.remove(cached_creds_file)

        with patch.dict(os.environ, {"HAKAI_API_CREDENTIALS": expired_env_creds}):
            with patch(
                "hakai_api.auth.web.WebAuthStrategy._get_credentials_from_web_input",
                side_effect=mock_get_credentials,
            ):
                client = Client()

                # Should have fresh credentials, not the expired environment ones
                assert client.credentials["access_token"] == "fresh_token_after_env_rejection"

    def test_multiple_401_responses_only_one_reauth_attempt(self, valid_credentials):
        """Test that multiple 401s don't cause infinite re-authentication loops."""
        call_count = 0

        def mock_request(method, uri, **kwargs: dict[str, Any]):
            nonlocal call_count
            call_count += 1

            mock_response = Mock()
            if call_count == 1:
                # First call returns 401
                mock_response.status_code = 401
                mock_response.json.return_value = {"error": "token expired"}
            elif call_count == 2:
                # Second call after re-auth also returns 401 (simulating server issues)
                mock_response.status_code = 401
                mock_response.json.return_value = {"error": "still unauthorized"}
            else:
                # This shouldn't happen due to no retry loop
                mock_response.status_code = 500
                mock_response.json.return_value = {"error": "unexpected call"}

            return mock_response

        def mock_get_credentials():
            return {
                "access_token": "new_token",
                "token_type": "Bearer",
                "expires_at": int(mktime(datetime.now(timezone.utc).timetuple()) + 3600),
                "expires_in": 3600,
            }

        with patch("requests_oauthlib.OAuth2Session.request", side_effect=mock_request):
            client = Client(credentials=valid_credentials)

            with patch.object(client._auth_strategy, "get_credentials", side_effect=mock_get_credentials):
                response = client.request("GET", "/whoami")

                # Should get 401 from retry, but no further re-auth attempts
                assert response.status_code == 401
                assert call_count == 2  # Original + one retry, no infinite loop

    def test_non_401_responses_are_not_intercepted(self, valid_credentials):
        """Test that non-401 responses (like 403, 500) are not intercepted."""

        def mock_request(method, uri, **kwargs: dict[str, Any]):
            mock_response = Mock()
            mock_response.status_code = 403  # Forbidden, not Unauthorized
            mock_response.json.return_value = {"error": "access denied"}
            return mock_response

        with patch("requests_oauthlib.OAuth2Session.request", side_effect=mock_request):
            client = Client(credentials=valid_credentials)

            response = client.request("GET", "/whoami")

            # Should return 403 as-is, no re-authentication attempted
            assert response.status_code == 403
            assert client.credentials["access_token"] == "valid_token"  # noqa: S105  # Unchanged


class TestClientRefreshTokenScenarios:
    """Test refresh token functionality."""

    def test_refresh_token_success_desktop_strategy(self):
        """Test successful token refresh with desktop strategy."""
        credentials_with_refresh = {
            "access_token": "old_token",
            "token_type": "Bearer",
            "expires_at": int(mktime(datetime.now(timezone.utc).timetuple()) + 3600),
            "expires_in": 3600,
            "refresh_token": "refresh123",
        }

        def mock_refresh_token(creds):
            # Mock successful refresh
            return {
                "access_token": "refreshed_token",
                "token_type": "Bearer",
                "expires_at": int(mktime(datetime.now(timezone.utc).timetuple()) + 7200),
                "expires_in": 7200,
                "refresh_token": "refresh123",
            }

        client = Client(credentials=credentials_with_refresh, auth_flow="desktop")

        with patch.object(client._auth_strategy, "refresh_token", side_effect=mock_refresh_token):
            result = client.refresh_token()

            assert result is True
            assert client.credentials["access_token"] == "refreshed_token"  # noqa: S105

    def test_refresh_token_success_web_strategy(self):
        """Test successful token refresh with web strategy."""
        credentials_with_refresh = {
            "access_token": "old_token",
            "token_type": "Bearer",
            "expires_at": int(mktime(datetime.now(timezone.utc).timetuple()) + 3600),
            "expires_in": 3600,
            "refresh_token": "refresh123",
        }

        def mock_post(url, json=None, timeout=None):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "refreshed_web_token",
                "expires_at": int(mktime(datetime.now(timezone.utc).timetuple()) + 7200),
                "expires_in": 7200,
            }
            return mock_response

        client = Client(credentials=credentials_with_refresh, auth_flow="web")

        with patch("requests.post", side_effect=mock_post):
            result = client.refresh_token()

            assert result is True
            assert client.credentials["access_token"] == "refreshed_web_token"  # noqa: S105

    def test_refresh_token_no_refresh_token_available(self, valid_credentials):
        """Test refresh token when no refresh token is available."""
        client = Client(credentials=valid_credentials)  # No refresh token

        result = client.refresh_token()

        assert result is False
        assert client.credentials["access_token"] == "valid_token"  # noqa: S105  # Unchanged

    def test_refresh_token_failure(self):
        """Test failed token refresh."""
        credentials_with_refresh = {
            "access_token": "old_token",
            "token_type": "Bearer",
            "expires_at": int(mktime(datetime.now(timezone.utc).timetuple()) + 3600),
            "expires_in": 3600,
            "refresh_token": "invalid_refresh",
        }

        def mock_post(url, json=None, timeout=None):
            mock_response = Mock()
            mock_response.status_code = 400  # Bad request
            return mock_response

        client = Client(credentials=credentials_with_refresh, auth_flow="web")

        with patch("requests.post", side_effect=mock_post):
            result = client.refresh_token()

            assert result is False
            assert client.credentials["access_token"] == "old_token"  # noqa: S105  # Unchanged
