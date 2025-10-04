"""Unit tests for data aggregator."""

from unittest.mock import Mock

import pytest

from src.providers.github import GitHubConnError
from src.providers.jira import JiraConnError
from src.services.data_aggregator import DataAggregator


class TestDataAggregator:
    """Tests for DataAggregator class."""

    @pytest.fixture
    def mock_jira_client(self):
        """Create a mock JIRA client."""
        return Mock()

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return Mock()

    @pytest.fixture
    def aggregator(self, mock_jira_client, mock_github_client):
        """Create a data aggregator with mocked clients."""
        return DataAggregator(
            jira_client=mock_jira_client, github_client=mock_github_client
        )

    def test_get_user_activity_all_sources(
        self, aggregator, mock_jira_client, mock_github_client
    ):
        """Should fetch data from both JIRA and GitHub when query_type is 'all'."""
        mock_jira_client.get_user_issues.return_value = [
            {"key": "PROJ-1", "summary": "Test issue"}
        ]
        mock_github_client.get_user_commits.return_value = [
            {"sha": "abc123", "message": "Test commit"}
        ]
        mock_github_client.get_user_pull_requests.return_value = [
            {"number": 42, "title": "Test PR"}
        ]

        result = aggregator.get_user_activity("testuser", query_type="all")

        assert result["username"] == "testuser"
        assert len(result["jira_issues"]) == 1
        assert len(result["github_commits"]) == 1
        assert len(result["github_prs"]) == 1
        assert result["has_activity"] is True
        assert result["errors"] == []

        mock_jira_client.get_user_issues.assert_called_once_with("testuser")
        mock_github_client.get_user_commits.assert_called_once_with("testuser", days=7)
        mock_github_client.get_user_pull_requests.assert_called_once_with(
            "testuser", days=7
        )

    def test_get_user_activity_jira_only(
        self, aggregator, mock_jira_client, mock_github_client
    ):
        """Should only fetch JIRA data when query_type is 'jira'."""
        mock_jira_client.get_user_issues.return_value = [
            {"key": "PROJ-1", "summary": "Test issue"}
        ]

        result = aggregator.get_user_activity("testuser", query_type="jira")

        assert len(result["jira_issues"]) == 1
        assert len(result["github_commits"]) == 0
        assert len(result["github_prs"]) == 0

        mock_jira_client.get_user_issues.assert_called_once()
        mock_github_client.get_user_commits.assert_not_called()
        mock_github_client.get_user_pull_requests.assert_not_called()

    def test_get_user_activity_github_only(
        self, aggregator, mock_jira_client, mock_github_client
    ):
        """Should only fetch GitHub data when query_type is 'github'."""
        mock_github_client.get_user_commits.return_value = [
            {"sha": "abc123", "message": "Test commit"}
        ]
        mock_github_client.get_user_pull_requests.return_value = [
            {"number": 42, "title": "Test PR"}
        ]

        result = aggregator.get_user_activity("testuser", query_type="github")

        assert len(result["jira_issues"]) == 0
        assert len(result["github_commits"]) == 1
        assert len(result["github_prs"]) == 1

        mock_jira_client.get_user_issues.assert_not_called()
        mock_github_client.get_user_commits.assert_called_once()
        mock_github_client.get_user_pull_requests.assert_called_once()

    def test_get_user_activity_no_results(
        self, aggregator, mock_jira_client, mock_github_client
    ):
        """Should handle case when user has no activity."""
        mock_jira_client.get_user_issues.return_value = []
        mock_github_client.get_user_commits.return_value = []
        mock_github_client.get_user_pull_requests.return_value = []

        result = aggregator.get_user_activity("testuser")

        assert result["has_activity"] is False
        assert result["errors"] == []

    def test_get_user_activity_with_custom_days(
        self, aggregator, mock_jira_client, mock_github_client
    ):
        """Should pass custom days parameter to GitHub client."""
        mock_jira_client.get_user_issues.return_value = []
        mock_github_client.get_user_commits.return_value = []
        mock_github_client.get_user_pull_requests.return_value = []

        aggregator.get_user_activity("testuser", days=14)

        mock_github_client.get_user_commits.assert_called_once_with("testuser", days=14)
        mock_github_client.get_user_pull_requests.assert_called_once_with(
            "testuser", days=14
        )

    def test_get_user_activity_handles_jira_error(
        self, aggregator, mock_jira_client, mock_github_client
    ):
        """Should handle JIRA errors gracefully and continue fetching GitHub data."""
        mock_jira_client.get_user_issues.side_effect = JiraConnError(
            "Connection failed"
        )
        mock_github_client.get_user_commits.return_value = [
            {"sha": "abc123", "message": "Test commit"}
        ]
        mock_github_client.get_user_pull_requests.return_value = []

        result = aggregator.get_user_activity("testuser")

        assert len(result["github_commits"]) == 1
        assert len(result["errors"]) == 1
        assert "JIRA" in result["errors"][0]

    def test_get_user_activity_handles_github_error(
        self, aggregator, mock_jira_client, mock_github_client
    ):
        """Should handle GitHub errors gracefully and continue fetching JIRA data."""
        mock_jira_client.get_user_issues.return_value = [
            {"key": "PROJ-1", "summary": "Test issue"}
        ]
        mock_github_client.get_user_commits.side_effect = GitHubConnError(
            "Connection failed"
        )
        mock_github_client.get_user_pull_requests.return_value = []

        result = aggregator.get_user_activity("testuser")

        assert len(result["jira_issues"]) == 1
        assert len(result["errors"]) == 1
        assert "GitHub commits" in result["errors"][0]

    def test_format_summary_with_all_data(self, aggregator):
        """Should format summary with JIRA and GitHub data."""
        activity_data = {
            "username": "testuser",
            "jira_issues": [
                {"key": "PROJ-1", "summary": "Test issue 1", "status": "In Progress"},
                {"key": "PROJ-2", "summary": "Test issue 2", "status": "Done"},
            ],
            "github_commits": [
                {
                    "repository": "org/repo",
                    "message": "Fix bug in authentication",
                    "sha": "abc123",
                }
            ],
            "github_prs": [
                {
                    "repository": "org/repo",
                    "number": 42,
                    "title": "Add new feature",
                    "state": "open",
                }
            ],
            "has_activity": True,
            "errors": [],
        }

        summary = aggregator.format_summary(activity_data)

        assert "Activity summary for testuser" in summary
        assert "JIRA Issues (2)" in summary
        assert "PROJ-1" in summary
        assert "GitHub Commits (1)" in summary
        assert "Fix bug" in summary
        assert "GitHub Pull Requests (1)" in summary
        assert "#42" in summary

    def test_format_summary_no_activity(self, aggregator):
        """Should format appropriate message when no activity found."""
        activity_data = {
            "username": "testuser",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": [],
        }

        summary = aggregator.format_summary(activity_data)

        assert "Activity summary for testuser" in summary
        assert "No recent activity found" in summary

    def test_format_summary_with_errors(self, aggregator):
        """Should include errors in formatted summary."""
        activity_data = {
            "username": "testuser",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": ["JIRA: Connection failed", "GitHub: Rate limit exceeded"],
        }

        summary = aggregator.format_summary(activity_data)

        assert "Errors encountered" in summary
        assert "JIRA: Connection failed" in summary
        assert "GitHub: Rate limit exceeded" in summary

    def test_format_summary_truncates_long_lists(self, aggregator):
        """Should show only top 5 items and indicate more."""
        activity_data = {
            "username": "testuser",
            "jira_issues": [
                {"key": f"PROJ-{i}", "summary": f"Issue {i}", "status": "Open"}
                for i in range(10)
            ],
            "github_commits": [],
            "github_prs": [],
            "has_activity": True,
            "errors": [],
        }

        summary = aggregator.format_summary(activity_data)

        assert "and 5 more" in summary
        assert "PROJ-0" in summary
        assert "PROJ-4" in summary
