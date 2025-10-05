"""Unit tests for Flask API."""

from unittest.mock import Mock, patch

import pytest

from src.api.app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    return app.test_client()


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Health check should return 200 OK."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "team-activity-monitor"


class TestStatusEndpoint:
    """Tests for connection status endpoint."""

    @patch("src.api.app.JiraClient")
    @patch("src.api.app.GitHubClient")
    def test_status_all_connected(self, mock_github_cls, mock_jira_cls, client):
        """Should return connected status when both services are available."""
        mock_jira_instance = Mock()
        mock_jira_instance.test_connection.return_value = {"status": "connected"}
        mock_jira_cls.return_value = mock_jira_instance

        mock_github_instance = Mock()
        mock_github_instance.test_connection.return_value = {"status": "connected"}
        mock_github_cls.return_value = mock_github_instance

        response = client.get("/api/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["services"]["jira"] == "connected"
        assert data["services"]["github"] == "connected"

    @patch("src.api.app.JiraClient")
    @patch("src.api.app.GitHubClient")
    def test_status_jira_error(self, mock_github_cls, mock_jira_cls, client):
        """Should return degraded status when JIRA connection fails."""
        from src.providers.jira import JiraConnError

        mock_jira_instance = Mock()
        mock_jira_instance.test_connection.side_effect = JiraConnError(
            "Connection failed"
        )
        mock_jira_cls.return_value = mock_jira_instance

        mock_github_instance = Mock()
        mock_github_instance.test_connection.return_value = {"status": "connected"}
        mock_github_cls.return_value = mock_github_instance

        response = client.get("/api/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "degraded"
        assert "error" in data["services"]["jira"]


class TestQueryEndpoint:
    """Tests for query processing endpoint."""

    @patch("src.api.app.response_generator")
    @patch("src.api.app.data_aggregator")
    @patch("src.api.app.query_parser")
    def test_query_success(self, mock_parser, mock_aggregator, mock_generator, client):
        """Should successfully process a valid query."""
        mock_parser.parse.return_value = {
            "username": "John",
            "query_type": "all",
            "original_query": "What is John working on?",
        }

        mock_aggregator.get_user_activity.return_value = {
            "username": "John",
            "jira_issues": [{"key": "PROJ-1", "summary": "Test"}],
            "github_commits": [],
            "github_prs": [],
            "has_activity": True,
            "errors": [],
        }
        mock_aggregator.format_summary.return_value = "Activity summary for John..."
        mock_generator.generate_response.return_value = (
            "John has been working on PROJ-1..."
        )

        response = client.post("/api/query", json={"query": "What is John working on?"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["query"] == "What is John working on?"
        assert data["parsed"]["username"] == "John"
        assert "summary" in data
        assert "activity" in data
        assert "ai_response" in data

    def test_query_missing_query_field(self, client):
        """Should return 400 when query field is missing."""
        response = client.post("/api/query", json={})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_query_empty_query_string(self, client):
        """Should return 400 when query is empty."""
        response = client.post("/api/query", json={"query": ""})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_query_invalid_days(self, client):
        """Should return 400 when days parameter is invalid."""
        response = client.post(
            "/api/query", json={"query": "What is John working on?", "days": 500}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    @patch("src.api.app.query_parser")
    def test_query_no_username_extracted(self, mock_parser, client):
        """Should return 400 when username cannot be extracted."""
        mock_parser.parse.return_value = {
            "username": None,
            "query_type": "all",
            "original_query": "What is happening?",
        }

        response = client.post("/api/query", json={"query": "What is happening?"})

        assert response.status_code == 400
        data = response.get_json()
        assert "Could not extract username" in data["error"]
        assert "suggestion" in data

    @patch("src.api.app.data_aggregator")
    @patch("src.api.app.query_parser")
    def test_query_with_custom_days(self, mock_parser, mock_aggregator, client):
        """Should pass custom days parameter to aggregator."""
        mock_parser.parse.return_value = {
            "username": "John",
            "query_type": "all",
            "original_query": "What is John working on?",
        }

        mock_aggregator.get_user_activity.return_value = {
            "username": "John",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": [],
        }
        mock_aggregator.format_summary.return_value = "No activity"

        response = client.post(
            "/api/query", json={"query": "What is John working on?", "days": 14}
        )

        assert response.status_code == 200
        mock_aggregator.get_user_activity.assert_called_once_with(
            username="John", query_type="all", days=14
        )


class TestErrorHandlers:
    """Tests for error handlers."""

    def test_404_error(self, client):
        """Should return 404 JSON response for non-existent endpoints."""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Not found"
