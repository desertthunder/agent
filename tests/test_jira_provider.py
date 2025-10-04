"""Unit tests for JIRA provider."""

import base64
from unittest.mock import Mock, patch

import pytest
import requests

from src.providers.jira import (
    JiraAuthError,
    JiraClient,
    JiraConnError,
)


class TestJiraClientInitialization:
    """Tests for JiraClient initialization and authentication setup."""

    def test_init_with_provided_credentials(self):
        """JiraClient should initialize with explicitly provided credentials."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test_token",
        )

        assert client.base_url == "https://test.atlassian.net"
        assert client.email == "test@example.com"
        assert client.api_token == "test_token"
        assert client.session is not None

    def test_init_strips_trailing_slash_from_url(self):
        """Base URL should have trailing slash removed."""
        client = JiraClient(
            base_url="https://test.atlassian.net/",
            email="test@example.com",
            api_token="test_token",
        )

        assert client.base_url == "https://test.atlassian.net"

    @patch("src.providers.jira.JIRA_BASE_URL", "")
    @patch("src.providers.jira.JIRA_EMAIL", "")
    @patch("src.providers.jira.JIRA_API_TOKEN", "")
    def test_init_raises_error_when_credentials_missing(self):
        """Should raise JiraAuthenticationError when credentials are missing."""
        with pytest.raises(JiraAuthError) as exc_info:
            JiraClient()

        assert "Missing required JIRA credentials" in str(exc_info.value)

    def test_session_has_correct_auth_header(self):
        """Session should have properly encoded Basic Auth header."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test_token",
        )

        expected_auth = base64.b64encode(b"test@example.com:test_token").decode("ascii")
        assert client.session.headers["Authorization"] == f"Basic {expected_auth}"
        assert client.session.headers["Accept"] == "application/json"
        assert client.session.headers["Content-Type"] == "application/json"


class TestJiraClientConnection:
    """Tests for JIRA connection testing."""

    @pytest.fixture
    def client(self):
        """Create a test JIRA client."""
        return JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test_token",
        )

    def test_test_connection_success(self, client):
        """Should successfully connect and return user info."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "displayName": "Test User",
            "emailAddress": "test@example.com",
        }

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.test_connection()

        assert result["status"] == "connected"
        assert result["user"] == "Test User"
        assert result["email"] == "test@example.com"

    def test_test_connection_invalid_credentials(self, client):
        """Should raise JiraAuthenticationError for 401 response."""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(JiraAuthError) as exc_info:
                client.test_connection()

        assert "Invalid JIRA credentials" in str(exc_info.value)

    def test_test_connection_forbidden(self, client):
        """Should raise JiraAuthenticationError for 403 response."""
        mock_response = Mock()
        mock_response.status_code = 403

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(JiraAuthError) as exc_info:
                client.test_connection()

        assert "Access forbidden" in str(exc_info.value)

    def test_test_connection_timeout(self, client):
        """Should raise JiraConnectionError on timeout."""
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(JiraConnError) as exc_info:
                client.test_connection()

        assert "timed out" in str(exc_info.value)

    def test_test_connection_network_error(self, client):
        """Should raise JiraConnectionError on network error."""
        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("Network error"),
        ):
            with pytest.raises(JiraConnError) as exc_info:
                client.test_connection()

        assert "Failed to connect" in str(exc_info.value)


class TestJiraClientGetUserIssues:
    """Tests for fetching user issues."""

    @pytest.fixture
    def client(self):
        """Create a test JIRA client."""
        return JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test_token",
        )

    def test_get_user_issues_success(self, client):
        """Should successfully fetch and parse user issues."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issues": [
                {
                    "key": "PROJ-123",
                    "fields": {
                        "summary": "Test issue",
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "Test User"},
                        "updated": "2024-01-01T12:00:00.000+0000",
                        "created": "2024-01-01T10:00:00.000+0000",
                        "description": "Test description",
                        "priority": {"name": "High"},
                    },
                }
            ]
        }

        with patch.object(client.session, "get", return_value=mock_response):
            issues = client.get_user_issues("testuser")

        assert len(issues) == 1
        assert issues[0]["key"] == "PROJ-123"
        assert issues[0]["summary"] == "Test issue"
        assert issues[0]["status"] == "In Progress"
        assert issues[0]["assignee"] == "Test User"

    def test_get_user_issues_no_results(self, client):
        """Should return empty list when user has no issues."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"issues": []}

        with patch.object(client.session, "get", return_value=mock_response):
            issues = client.get_user_issues("testuser")

        assert issues == []

    def test_get_user_issues_with_max_results(self, client):
        """Should pass max_results parameter correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"issues": []}

        with patch.object(
            client.session, "get", return_value=mock_response
        ) as mock_get:
            client.get_user_issues("testuser", max_results=10)

        call_params = mock_get.call_args[1]["params"]
        assert call_params["maxResults"] == 10

    def test_get_user_issues_timeout(self, client):
        """Should raise JiraConnectionError on timeout."""
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(JiraConnError):
                client.get_user_issues("testuser")


class TestJiraClientGetIssueDetails:
    """Tests for fetching issue details."""

    @pytest.fixture
    def client(self):
        """Create a test JIRA client."""
        return JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test_token",
        )

    def test_get_issue_details_success(self, client):
        """Should successfully fetch and parse issue details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "PROJ-123",
            "fields": {
                "summary": "Test issue",
                "description": "Detailed description",
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "Test User"},
                "reporter": {"displayName": "Reporter User"},
                "priority": {"name": "High"},
                "created": "2024-01-01T10:00:00.000+0000",
                "updated": "2024-01-01T12:00:00.000+0000",
                "resolution": None,
            },
            "changelog": {"histories": []},
        }

        with patch.object(client.session, "get", return_value=mock_response):
            details = client.get_issue_details("PROJ-123")

        assert details["key"] == "PROJ-123"
        assert details["summary"] == "Test issue"
        assert details["status"] == "In Progress"
        assert details["assignee"] == "Test User"
        assert details["reporter"] == "Reporter User"
        assert details["changelog"] == []

    def test_get_issue_details_not_found(self, client):
        """Should raise JiraConnectionError when issue not found."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(JiraConnError) as exc_info:
                client.get_issue_details("PROJ-999")

        assert "not found" in str(exc_info.value)

    def test_get_issue_details_timeout(self, client):
        """Should raise JiraConnectionError on timeout."""
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(JiraConnError):
                client.get_issue_details("PROJ-123")
