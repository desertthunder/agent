"""Unit tests for GitHub provider."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.providers.github import GitHubAuthError, GitHubClient, GitHubConnError


class TestGitHubClientInitialization:
    """Tests for GitHubClient initialization and authentication setup."""

    def test_init_with_provided_token(self):
        """GitHubClient should initialize with explicitly provided token."""
        client = GitHubClient(token="test_token_123")

        assert client.token == "test_token_123"
        assert client.base_url == "https://api.github.com"
        assert client.session is not None

    def test_init_with_custom_base_url(self):
        """Should accept custom base URL for enterprise instances."""
        client = GitHubClient(
            token="test_token", base_url="https://github.enterprise.com/api/v3"
        )

        assert client.base_url == "https://github.enterprise.com/api/v3"

    def test_init_strips_trailing_slash_from_url(self):
        """Base URL should have trailing slash removed."""
        client = GitHubClient(token="test_token", base_url="https://api.github.com/")

        assert client.base_url == "https://api.github.com"

    @patch("src.providers.github.GITHUB_TOKEN", "")
    def test_init_raises_error_when_token_missing(self):
        """Should raise GitHubAuthError when token is missing."""
        with pytest.raises(GitHubAuthError) as exc_info:
            GitHubClient()

        assert "Missing required GitHub token" in str(exc_info.value)

    def test_session_has_correct_auth_header(self):
        """Session should have proper Bearer token authorization."""
        client = GitHubClient(token="test_token_123")

        assert client.session.headers["Authorization"] == "Bearer test_token_123"
        assert client.session.headers["Accept"] == "application/vnd.github+json"
        assert client.session.headers["X-GitHub-Api-Version"] == "2022-11-28"


class TestGitHubClientConnection:
    """Tests for GitHub connection testing."""

    @pytest.fixture
    def client(self):
        """Create a test GitHub client."""
        return GitHubClient(token="test_token_123")

    def test_test_connection_success(self, client):
        """Should successfully connect and return user info."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
        }

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.test_connection()

        assert result["status"] == "connected"
        assert result["user"] == "testuser"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"

    def test_test_connection_invalid_token(self, client):
        """Should raise GitHubAuthError for 401 response."""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(GitHubAuthError) as exc_info:
                client.test_connection()

        assert "Invalid GitHub token" in str(exc_info.value)

    def test_test_connection_forbidden(self, client):
        """Should raise GitHubAuthError for 403 response."""
        mock_response = Mock()
        mock_response.status_code = 403

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(GitHubAuthError) as exc_info:
                client.test_connection()

        assert "Access forbidden" in str(exc_info.value)

    def test_test_connection_timeout(self, client):
        """Should raise GitHubConnError on timeout."""
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(GitHubConnError) as exc_info:
                client.test_connection()

        assert "timed out" in str(exc_info.value)

    def test_test_connection_network_error(self, client):
        """Should raise GitHubConnError on network error."""
        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("Network error"),
        ):
            with pytest.raises(GitHubConnError) as exc_info:
                client.test_connection()

        assert "Failed to connect" in str(exc_info.value)


class TestGitHubClientGetUserCommits:
    """Tests for fetching user commits."""

    @pytest.fixture
    def client(self):
        """Create a test GitHub client."""
        return GitHubClient(token="test_token_123")

    def test_get_user_commits_success(self, client):
        """Should successfully fetch and parse user commits."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "sha": "abc123",
                    "commit": {
                        "message": "Fix bug in authentication",
                        "author": {
                            "name": "Test User",
                            "date": "2024-01-01T12:00:00Z",
                        },
                    },
                    "repository": {"full_name": "testorg/testrepo"},
                    "html_url": "https://github.com/testorg/testrepo/commit/abc123",
                }
            ]
        }

        with patch.object(client.session, "get", return_value=mock_response):
            commits = client.get_user_commits("testuser")

        assert len(commits) == 1
        assert commits[0]["sha"] == "abc123"
        assert commits[0]["message"] == "Fix bug in authentication"
        assert commits[0]["author"] == "Test User"
        assert commits[0]["repository"] == "testorg/testrepo"

    def test_get_user_commits_no_results(self, client):
        """Should return empty list when user has no commits."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch.object(client.session, "get", return_value=mock_response):
            commits = client.get_user_commits("testuser")

        assert commits == []

    def test_get_user_commits_with_custom_days(self, client):
        """Should construct query with custom days parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch.object(
            client.session, "get", return_value=mock_response
        ) as mock_get:
            client.get_user_commits("testuser", days=14)

        call_params = mock_get.call_args[1]["params"]
        assert "author:testuser" in call_params["q"]
        assert "committer-date:>=" in call_params["q"]

    def test_get_user_commits_with_max_results(self, client):
        """Should respect max_results parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch.object(
            client.session, "get", return_value=mock_response
        ) as mock_get:
            client.get_user_commits("testuser", max_results=50)

        call_params = mock_get.call_args[1]["params"]
        assert call_params["per_page"] == 50

    def test_get_user_commits_timeout(self, client):
        """Should raise GitHubConnError on timeout."""
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(GitHubConnError):
                client.get_user_commits("testuser")


class TestGitHubClientGetUserPullRequests:
    """Tests for fetching user pull requests."""

    @pytest.fixture
    def client(self):
        """Create a test GitHub client."""
        return GitHubClient(token="test_token_123")

    def test_get_user_pull_requests_success(self, client):
        """Should successfully fetch and parse user pull requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "number": 42,
                    "title": "Add new feature",
                    "state": "open",
                    "created_at": "2024-01-01T10:00:00Z",
                    "updated_at": "2024-01-01T12:00:00Z",
                    "repository_url": "https://api.github.com/repos/testorg/testrepo",
                    "html_url": "https://github.com/testorg/testrepo/pull/42",
                    "user": {"login": "testuser"},
                }
            ]
        }

        with patch.object(client.session, "get", return_value=mock_response):
            prs = client.get_user_pull_requests("testuser")

        assert len(prs) == 1
        assert prs[0]["number"] == 42
        assert prs[0]["title"] == "Add new feature"
        assert prs[0]["state"] == "open"
        assert prs[0]["repository"] == "testorg/testrepo"
        assert prs[0]["author"] == "testuser"

    def test_get_user_pull_requests_no_results(self, client):
        """Should return empty list when user has no PRs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch.object(client.session, "get", return_value=mock_response):
            prs = client.get_user_pull_requests("testuser")

        assert prs == []

    def test_get_user_pull_requests_with_custom_days(self, client):
        """Should construct query with custom days parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch.object(
            client.session, "get", return_value=mock_response
        ) as mock_get:
            client.get_user_pull_requests("testuser", days=30)

        call_params = mock_get.call_args[1]["params"]
        assert "is:pr" in call_params["q"]
        assert "author:testuser" in call_params["q"]
        assert "created:>=" in call_params["q"]

    def test_get_user_pull_requests_with_max_results(self, client):
        """Should respect max_results parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch.object(
            client.session, "get", return_value=mock_response
        ) as mock_get:
            client.get_user_pull_requests("testuser", max_results=25)

        call_params = mock_get.call_args[1]["params"]
        assert call_params["per_page"] == 25

    def test_get_user_pull_requests_timeout(self, client):
        """Should raise GitHubConnError on timeout."""
        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(GitHubConnError):
                client.get_user_pull_requests("testuser")
