"""Layer 2: Mock integration tests for client.py — mock garminconnect library.

Note: Garmin is imported INSIDE functions in client.py, so we patch 'garminconnect.Garmin'.
"""

from unittest.mock import patch, MagicMock
from pathlib import Path

from garmin_agent.client import GarminClient

# 测试用虚拟凭证
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "test-pass-123"
TEST_PASSWORD_SECRET = "test-secret-456"


class TestGarminClientConnect:
    """Test connection flow: token restore → credential login."""

    @patch("garminconnect.Garmin")
    def test_connect_with_stored_tokens(self, MockGarmin):
        mock_garmin = MagicMock()
        mock_garmin.get_full_name.return_value = "Test User"
        MockGarmin.return_value = mock_garmin

        client = GarminClient()
        client.tokenstore = Path("/fake/tokens")

        with patch.object(Path, "exists", return_value=True):
            result = client.connect()

        assert result is True
        assert client.is_authenticated is True
        mock_garmin.login.assert_called_once()

    @patch("garminconnect.Garmin")
    def test_connect_token_fail_credential_success(self, MockGarmin):
        mock_garmin = MagicMock()
        # First call (token) raises, second call (credential) succeeds
        mock_garmin.login.side_effect = [Exception("token expired"), None]
        mock_garmin.get_full_name.return_value = "Test User"
        MockGarmin.return_value = mock_garmin

        client = GarminClient(email=TEST_EMAIL, password=TEST_PASSWORD)
        client.tokenstore = Path("/fake/tokens")

        with patch.object(Path, "exists", return_value=True):
            result = client.connect()

        assert result is True
        assert client.is_authenticated is True

    @patch("garminconnect.Garmin")
    def test_connect_no_tokens_no_credentials(self, MockGarmin):
        client = GarminClient()
        client.tokenstore = Path("/nonexistent")

        result = client.connect()
        assert result is False

    @patch("garminconnect.Garmin")
    def test_connect_password_deleted_after_login(self, MockGarmin):
        mock_garmin = MagicMock()
        mock_garmin.login.return_value = None
        mock_garmin.get_full_name.return_value = "Test User"
        MockGarmin.return_value = mock_garmin

        client = GarminClient(email=TEST_EMAIL, password=TEST_PASSWORD_SECRET)
        client.tokenstore = Path("/fake/tokens")

        with patch.object(Path, "exists", return_value=False):
            with patch.object(Path, "mkdir"):
                client.connect()

        assert client.password is None


class TestGarminClientAPIs:
    """Test API wrapper methods delegate to garminconnect client."""

    def _make_connected_client(self):
        """Helper: create a connected client with mocked garminconnect."""
        client = GarminClient()
        client._client = MagicMock()
        client._authenticated = True
        return client

    def test_get_activities(self):
        client = self._make_connected_client()
        client._client.get_activities.return_value = [{"activityId": 1}]
        result = client.get_activities(limit=5)
        assert result == [{"activityId": 1}]
        client._client.get_activities.assert_called_once_with(0, 5)

    def test_get_activities_by_date(self):
        client = self._make_connected_client()
        client._client.get_activities_by_date.return_value = []
        result = client.get_activities_by_date("2026-01-01", "2026-05-01")
        client._client.get_activities_by_date.assert_called_once_with("2026-01-01", "2026-05-01", "running")

    def test_get_activity(self):
        client = self._make_connected_client()
        client._client.get_activity.return_value = {"activityId": 123}
        result = client.get_activity(123)
        assert result["activityId"] == 123

    def test_not_connected_raises(self):
        client = GarminClient()
        try:
            client.get_activities()
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "Not connected" in str(e)
