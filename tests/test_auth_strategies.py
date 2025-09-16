"""Tests for authentication strategies."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import mktime
from typing import Any, Generator
from unittest.mock import Mock, patch

import pytest

from hakai_api.auth import AuthStrategy, DesktopAuthStrategy, WebAuthStrategy


class ConcreteAuthStrategy(AuthStrategy):
    """Concrete implementation for testing the abstract base class."""

    def get_credentials(self) -> dict:
        now_utc = datetime.now(timezone.utc)
        return {
            "access_token": "test_token",
            "token_type": "bearer",
            "expires_at": int(now_utc.timestamp() + 3600),  # Use UTC timestamp
            "expires_in": 3600,
        }

    @property
    def client_type(self) -> str:
        """Get the client type for test strategy."""
        return "test"


@pytest.fixture
def temp_credentials_file() -> Generator[Path, None, None]:
    """Create a temporary credentials file for testing.

    Yields:
        str: Path to the temporary credentials file.
    """
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_file = Path(f.name)

    yield temp_file

    # Cleanup
    try:
        temp_file.unlink()
    except OSError:
        pass


@pytest.fixture
def valid_credentials() -> dict:
    """Sample valid credentials for testing.

    Returns:
        dict: Dictionary containing valid test credentials.
    """
    now_utc = datetime.now(timezone.utc)
    future_timestamp = int(now_utc.timestamp() + 3600)  # Use UTC timestamp
    return {
        "access_token": "test_access_token",
        "token_type": "bearer",
        "expires_at": future_timestamp,
        "expires_in": 3600,
    }


@pytest.fixture
def expired_credentials() -> dict:
    """Sample expired credentials for testing.

    Returns:
        dict: Dictionary containing expired test credentials.
    """
    now_utc = datetime.now(timezone.utc)
    past_timestamp = int(now_utc.timestamp() - 3600)  # Use UTC timestamp
    return {
        "access_token": "expired_access_token",
        "token_type": "bearer",
        "expires_at": past_timestamp,
        "expires_in": 3600,
    }


class TestAuthStrategy:
    """Tests for the base AuthStrategy class."""

    def test_init(self) -> None:
        """Test AuthStrategy initialization."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        assert strategy.api_root == "https://api.example.com"
        assert strategy.credentials_file == Path.home() / ".hakai-api-auth"

    def test_save_and_get_credentials_from_file(self, temp_credentials_file: str, valid_credentials: dict) -> None:
        """Test saving and loading credentials from file."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        strategy.credentials_file = temp_credentials_file

        # Save credentials
        strategy.save_credentials_to_file(valid_credentials)

        # Load credentials
        loaded_credentials = strategy.get_credentials_from_file()

        assert loaded_credentials == valid_credentials

    def test_file_credentials_are_valid_with_valid_file(
        self, temp_credentials_file: str, valid_credentials: dict
    ) -> None:
        """Test file_credentials_are_valid with valid credentials."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        strategy.credentials_file = temp_credentials_file

        # Save valid credentials
        with open(temp_credentials_file, "w") as f:
            json.dump(valid_credentials, f)

        assert strategy.file_credentials_are_valid() is True

    def test_file_credentials_are_valid_with_expired_file(
        self, temp_credentials_file: str, expired_credentials: dict
    ) -> None:
        """Test file_credentials_are_valid with expired credentials."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        strategy.credentials_file = temp_credentials_file

        # Save expired credentials
        with open(temp_credentials_file, "w") as f:
            json.dump(expired_credentials, f)

        assert strategy.file_credentials_are_valid() is False
        # File should be removed after validation fails
        assert not os.path.exists(temp_credentials_file)

    def test_file_credentials_are_valid_no_file(self) -> None:
        """Test file_credentials_are_valid with no file."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        strategy.credentials_file = Path("/nonexistent/file")

        assert strategy.file_credentials_are_valid() is False

    def test_parse_credentials_string_valid(self) -> None:
        """Test parsing a valid credentials string."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        cred_string = "access_token=test123&token_type=bearer&expires_at=1234567890&expires_in=3600"

        result = strategy.parse_credentials_string(cred_string)

        expected = {
            "access_token": "test123",
            "token_type": "bearer",
            "expires_at": 1234567890,
            "expires_in": 3600,
        }
        assert result == expected

    def test_parse_credentials_string_missing_required_keys(self) -> None:
        """Test parsing credentials string with missing required keys."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        cred_string = "access_token=test123&expires_in=3600"  # Missing token_type and expires_at

        with pytest.raises(ValueError, match="missing required keys"):
            strategy.parse_credentials_string(cred_string)

    def test_check_keys_convert_types_valid(self) -> None:
        """Test _check_keys_convert_types with valid data."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        input_creds = {
            "access_token": "test123",
            "token_type": "bearer",
            "expires_at": "1234567890.5",  # String that can be converted
            "expires_in": "3600",  # String that can be converted
        }

        result = strategy._check_keys_convert_types(input_creds)

        expected = {
            "access_token": "test123",
            "token_type": "bearer",
            "expires_at": 1234567890,
            "expires_in": 3600,
        }
        assert result == expected

    def test_reset_credentials(self, temp_credentials_file: str) -> None:
        """Test resetting (deleting) credentials file."""
        strategy = ConcreteAuthStrategy("https://api.example.com", credentials_file=Path.home() / ".hakai-api-auth")
        strategy.credentials_file = temp_credentials_file

        # Create file
        with open(temp_credentials_file, "w") as f:
            f.write('{"test": "data"}')

        assert os.path.exists(temp_credentials_file)

        # Reset credentials
        strategy.reset_credentials()

        assert not os.path.exists(temp_credentials_file)


class TestWebAuthStrategy:
    """Tests for the WebAuthStrategy class."""

    def test_init(self) -> None:
        """Test WebAuthStrategy initialization."""
        strategy = WebAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )
        assert strategy.api_root == "https://api.example.com"
        assert strategy.login_page == "https://login.example.com"

    def test_get_credentials_from_env(self) -> None:
        """Test getting credentials from environment variable."""
        # Use a future timestamp to ensure credentials aren't expired
        future_timestamp = int(mktime(datetime.now(timezone.utc).timetuple()) + 3600)
        env_value = f"access_token=env_token&token_type=bearer&expires_at={future_timestamp}&expires_in=3600"

        with patch.dict(os.environ, {"HAKAI_API_CREDENTIALS": env_value}):
            strategy = WebAuthStrategy(
                "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
            )

            result = strategy.get_credentials()

            expected = {
                "access_token": "env_token",
                "token_type": "bearer",
                "expires_at": future_timestamp,
                "expires_in": 3600,
            }
            assert result == expected

    def test_get_credentials_from_cached_file(self, temp_credentials_file: Path, valid_credentials: dict) -> None:
        """Test getting credentials from cached file."""
        strategy = WebAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )
        strategy.credentials_file = temp_credentials_file

        # Save valid credentials to file
        with open(temp_credentials_file, "w") as f:
            json.dump(valid_credentials, f)

        result = strategy.get_credentials()

        assert result == valid_credentials

    @patch(
        "builtins.input",
        return_value="access_token=input_token&token_type=bearer&expires_at=1234567890&expires_in=3600",
    )
    def test_get_credentials_from_web_input(self, mock_input: Any) -> None:
        """Test getting credentials from web input."""
        strategy = WebAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )
        strategy.credentials_file = Path("/nonexistent/file")  # Ensure no cached file

        with patch.dict(os.environ, {}, clear=True):  # Clear environment
            result = strategy.get_credentials()

        expected = {
            "access_token": "input_token",
            "token_type": "bearer",
            "expires_at": 1234567890,
            "expires_in": 3600,
        }
        assert result == expected

    @patch("builtins.input", return_value="invalid_format")
    def test_get_credentials_web_input_invalid_format(self, mock_input: Any) -> None:
        """Test web input with invalid format."""
        strategy = WebAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )
        strategy.credentials_file = "/nonexistent/file"

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises((ValueError, AttributeError)):
                strategy.get_credentials()


class TestDesktopAuthStrategy:
    """Tests for the DesktopAuthStrategy class."""

    def test_init(self) -> None:
        """Test DesktopAuthStrategy initialization."""
        strategy = DesktopAuthStrategy(
            "https://api.example.com",
            local_port=8080,
            credentials_file=Path.home() / ".hakai-api-auth",
        )
        assert strategy.api_root == "https://api.example.com"
        assert strategy.local_port == 8080
        assert strategy._state is None
        assert strategy._code_verifier is None
        assert strategy._authorization_code is None

    def test_get_credentials_from_env(self) -> None:
        """Test getting credentials from environment variable."""
        # Use a future timestamp to ensure credentials aren't expired
        future_timestamp = int(mktime(datetime.now(timezone.utc).timetuple()) + 3600)
        env_value = f"access_token=env_token&token_type=bearer&expires_at={future_timestamp}&expires_in=3600"

        with patch.dict(os.environ, {"HAKAI_API_CREDENTIALS": env_value}):
            strategy = DesktopAuthStrategy(
                "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
            )

            result = strategy.get_credentials()

            expected = {
                "access_token": "env_token",
                "token_type": "bearer",
                "expires_at": future_timestamp,
                "expires_in": 3600,
            }
            assert result == expected

    def test_get_credentials_from_cached_file(self, temp_credentials_file: str, valid_credentials: dict) -> None:
        """Test getting credentials from cached file."""
        strategy = DesktopAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )
        strategy.credentials_file = temp_credentials_file

        # Save valid credentials to file
        with open(temp_credentials_file, "w") as f:
            json.dump(valid_credentials, f)

        result = strategy.get_credentials()

        assert result == valid_credentials

    @patch("webbrowser.open")
    @patch("requests.post")
    def test_oauth_flow_success(self, mock_post: Any, mock_browser: Any) -> None:
        """Test successful OAuth flow."""
        strategy = DesktopAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )
        strategy.credentials_file = Path("/nonexistent/file")

        # Mock token exchange response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "oauth_token",
            "token_type": "bearer",
            "expires_at": 1234567890,
            "expires_in": 3600,
            "refresh_token": "refresh123",
        }
        mock_post.return_value = mock_response

        # Mock successful callback
        with patch.object(strategy, "_wait_for_callback", return_value="auth_code_123"):
            with patch.dict(os.environ, {}, clear=True):
                result = strategy.get_credentials()

        expected = {
            "access_token": "oauth_token",
            "token_type": "bearer",
            "expires_at": 1234567890,
            "expires_in": 3600,
            "refresh_token": "refresh123",
        }
        assert result == expected
        mock_browser.assert_called_once()

    @patch("requests.post")
    def test_refresh_token_success(self, mock_post: Any) -> None:
        """Test successful token refresh."""
        strategy = DesktopAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )

        # Mock refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_at": 1234567890,
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        credentials = {
            "access_token": "old_token",
            "refresh_token": "refresh123",
            "expires_at": 1234560000,
            "expires_in": 3600,
        }

        result = strategy.refresh_token(credentials)

        expected = {
            "access_token": "new_token",
            "refresh_token": "refresh123",
            "expires_at": 1234567890,
            "expires_in": 3600,
        }
        assert result == expected

    def test_refresh_token_no_refresh_token(self) -> None:
        """Test refresh token with no refresh token available."""
        strategy = DesktopAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )

        credentials = {
            "access_token": "token",
            "expires_at": 1234567890,
            "expires_in": 3600,
        }

        result = strategy.refresh_token(credentials)
        assert result is None

    @patch("requests.post")
    def test_refresh_token_failure(self, mock_post: Any) -> None:
        """Test failed token refresh."""
        strategy = DesktopAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )

        # Mock failed refresh response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        credentials = {
            "access_token": "old_token",
            "refresh_token": "refresh123",
            "expires_at": 1234560000,
            "expires_in": 3600,
        }

        result = strategy.refresh_token(credentials)
        assert result is None

    @patch("requests.post")
    def test_exchange_code_for_tokens_failure(self, mock_post: Any) -> None:
        """Test token exchange failure."""
        strategy = DesktopAuthStrategy(
            "https://api.example.com", "https://login.example.com", credentials_file=Path.home() / ".hakai-api-auth"
        )
        strategy._authorization_code = "test_code"
        strategy._code_verifier = "test_verifier"
        strategy.local_port = 65500

        # Mock failed exchange response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid code"
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Token exchange failed"):
            strategy._exchange_code_for_tokens()
