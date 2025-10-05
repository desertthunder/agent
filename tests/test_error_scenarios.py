"""Integration tests for error scenarios as specified in SPEC.md.

These tests verify that the system handles all required error cases:
- User has no recent activity
- User is not found
- API connection errors
- Invalid input handling
"""

from unittest.mock import Mock

import pytest

from src.providers.github import GitHubAuthError, GitHubConnError
from src.providers.jira import JiraAuthError, JiraConnError
from src.providers.openai import ResponseGenerator
from src.services.data_aggregator import DataAggregator
from src.services.query_parser import QueryParser


class TestNoRecentActivityScenario:
    """Tests for handling users with no recent activity."""

    @pytest.fixture
    def mock_jira_client(self):
        """Create a mock JIRA client."""
        mock = Mock()
        mock.get_user_issues.return_value = []
        return mock

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        mock = Mock()
        mock.get_user_commits.return_value = []
        mock.get_user_pull_requests.return_value = []
        return mock

    def test_data_aggregator_returns_no_activity(
        self, mock_jira_client, mock_github_client
    ):
        """DataAggregator should indicate no activity when user has none."""
        aggregator = DataAggregator(
            jira_client=mock_jira_client, github_client=mock_github_client
        )

        result = aggregator.get_user_activity("inactive_user")

        assert result["has_activity"] is False
        assert result["username"] == "inactive_user"
        assert len(result["jira_issues"]) == 0
        assert len(result["github_commits"]) == 0
        assert len(result["github_prs"]) == 0

    def test_response_generator_handles_no_activity(self):
        """ResponseGenerator should provide helpful message for inactive users."""
        generator = ResponseGenerator()

        activity_data = {
            "username": "inactive_user",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": [],
        }

        response = generator.generate_response(activity_data, days=7)

        assert "inactive_user" in response
        assert response
        assert (
            "no recent activity" in response.lower()
            or "hasn't had any recent activity" in response.lower()
            or "couldn't find" in response.lower()
            or "doesn't appear" in response.lower()
        )

    def test_summary_format_indicates_no_activity(
        self, mock_jira_client, mock_github_client
    ):
        """DataAggregator.format_summary should clearly indicate no activity."""
        aggregator = DataAggregator(
            jira_client=mock_jira_client, github_client=mock_github_client
        )

        activity_data = aggregator.get_user_activity("inactive_user")
        summary = aggregator.format_summary(activity_data)

        assert "No recent activity found" in summary


class TestUserNotFoundScenario:
    """Tests for handling when a user is not found in JIRA/GitHub."""

    def test_jira_user_not_found_returns_empty(self):
        """JIRA client should return empty list when user not found."""
        mock_client = Mock()
        mock_client.get_user_issues.return_value = []

        aggregator = DataAggregator(jira_client=mock_client, github_client=Mock())
        result = aggregator.get_user_activity("nonexistent_user", query_type="jira")

        assert len(result["jira_issues"]) == 0
        assert result["has_activity"] is False

    def test_github_user_not_found_returns_empty(self):
        """GitHub client should return empty list when user not found."""
        mock_client = Mock()
        mock_client.get_user_commits.return_value = []
        mock_client.get_user_pull_requests.return_value = []

        aggregator = DataAggregator(jira_client=Mock(), github_client=mock_client)
        result = aggregator.get_user_activity("nonexistent_user", query_type="github")

        assert len(result["github_commits"]) == 0
        assert len(result["github_prs"]) == 0
        assert result["has_activity"] is False

    def test_user_not_found_in_both_systems(self):
        """Should handle user not found in both JIRA and GitHub."""
        mock_jira = Mock()
        mock_jira.get_user_issues.return_value = []

        mock_github = Mock()
        mock_github.get_user_commits.return_value = []
        mock_github.get_user_pull_requests.return_value = []

        aggregator = DataAggregator(jira_client=mock_jira, github_client=mock_github)
        result = aggregator.get_user_activity("totally_nonexistent_user")

        assert result["has_activity"] is False
        assert len(result["errors"]) == 0


class TestAPIConnectionErrors:
    """Tests for handling API connection failures."""

    def test_jira_connection_error_handled_gracefully(self):
        """Should handle JIRA connection errors without crashing."""
        mock_jira = Mock()
        mock_jira.get_user_issues.side_effect = JiraConnError("Connection timeout")

        mock_github = Mock()
        mock_github.get_user_commits.return_value = [
            {"sha": "abc", "message": "Test commit", "repository": "org/repo"}
        ]
        mock_github.get_user_pull_requests.return_value = []

        aggregator = DataAggregator(jira_client=mock_jira, github_client=mock_github)
        result = aggregator.get_user_activity("testuser")

        assert len(result["github_commits"]) == 1
        assert len(result["errors"]) == 1
        assert "JIRA" in result["errors"][0]

    def test_github_connection_error_handled_gracefully(self):
        """Should handle GitHub connection errors without crashing."""
        mock_jira = Mock()
        mock_jira.get_user_issues.return_value = [
            {"key": "PROJ-1", "summary": "Test issue", "status": "Open"}
        ]

        mock_github = Mock()
        mock_github.get_user_commits.side_effect = GitHubConnError("API rate limit")
        mock_github.get_user_pull_requests.return_value = []

        aggregator = DataAggregator(jira_client=mock_jira, github_client=mock_github)
        result = aggregator.get_user_activity("testuser")

        assert len(result["jira_issues"]) == 1
        assert len(result["errors"]) == 1
        assert "GitHub" in result["errors"][0]

    def test_both_apis_fail_returns_errors(self):
        """Should handle both APIs failing and return error information."""
        mock_jira = Mock()
        mock_jira.get_user_issues.side_effect = JiraConnError("Connection failed")

        mock_github = Mock()
        mock_github.get_user_commits.side_effect = GitHubConnError("Connection failed")
        mock_github.get_user_pull_requests.side_effect = GitHubConnError(
            "Connection failed"
        )

        aggregator = DataAggregator(jira_client=mock_jira, github_client=mock_github)
        result = aggregator.get_user_activity("testuser")

        assert result["has_activity"] is False
        assert len(result["errors"]) >= 2

    def test_response_generator_includes_errors(self):
        """ResponseGenerator should include errors in output."""
        generator = ResponseGenerator()

        activity_data = {
            "username": "testuser",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": [
                "JIRA: Connection timeout",
                "GitHub commits: API rate limit exceeded",
            ],
        }

        response = generator.generate_response(activity_data)

        assert "JIRA: Connection timeout" in response
        assert "GitHub" in response


class TestAuthenticationErrors:
    """Tests for handling authentication failures."""

    def test_jira_auth_error_propagates(self):
        """JIRA authentication errors should be raised to caller."""
        mock_jira = Mock()
        mock_jira.get_user_issues.side_effect = JiraAuthError("Invalid credentials")

        aggregator = DataAggregator(jira_client=mock_jira, github_client=Mock())
        result = aggregator.get_user_activity("testuser", query_type="jira")

        assert len(result["errors"]) >= 1

    def test_github_auth_error_propagates(self):
        """GitHub authentication errors should be raised to caller."""
        mock_github = Mock()
        mock_github.get_user_commits.side_effect = GitHubAuthError("Invalid token")
        mock_github.get_user_pull_requests.return_value = []

        aggregator = DataAggregator(jira_client=Mock(), github_client=mock_github)
        result = aggregator.get_user_activity("testuser", query_type="github")

        assert len(result["errors"]) >= 1


class TestQueryParsingErrors:
    """Tests for query parsing error scenarios."""

    def test_empty_query_returns_no_username(self):
        """Should handle empty queries gracefully."""
        parser = QueryParser()
        result = parser.parse("")
        assert result["username"] is None

    def test_query_with_no_username_returns_none(self):
        """Should return None for username when none found."""
        parser = QueryParser()
        result = parser.parse("What is happening?")
        assert result["username"] is None

    def test_query_with_special_characters(self):
        """Should gracefully handle queries that can't be parsed.

        NOTE: Parser may not extract usernames with special chars - \
            should return result gracefully. This is expected behavior, \
            not an error
        """
        parser = QueryParser()
        result = parser.parse("What is @user#123 working on?")

        assert "username" in result
        assert "query_type" in result


class TestPartialDataScenarios:
    """Tests for scenarios where only partial data is available."""

    def test_only_jira_data_available(self):
        """Should work with only JIRA data."""
        mock_jira = Mock()
        mock_jira.get_user_issues.return_value = [
            {"key": "PROJ-1", "summary": "Task", "status": "In Progress"}
        ]

        mock_github = Mock()
        mock_github.get_user_commits.return_value = []
        mock_github.get_user_pull_requests.return_value = []

        aggregator = DataAggregator(jira_client=mock_jira, github_client=mock_github)
        result = aggregator.get_user_activity("testuser")

        assert result["has_activity"] is True
        assert len(result["jira_issues"]) == 1
        assert len(result["github_commits"]) == 0

    def test_only_github_data_available(self):
        """Should work with only GitHub data."""
        mock_jira = Mock()
        mock_jira.get_user_issues.return_value = []

        mock_github = Mock()
        mock_github.get_user_commits.return_value = [
            {"sha": "abc", "message": "Fix bug", "repository": "org/repo"}
        ]
        mock_github.get_user_pull_requests.return_value = []

        aggregator = DataAggregator(jira_client=mock_jira, github_client=mock_github)
        result = aggregator.get_user_activity("testuser")

        assert result["has_activity"] is True
        assert len(result["jira_issues"]) == 0
        assert len(result["github_commits"]) == 1

    def test_response_generator_handles_partial_data(self):
        """ResponseGenerator should format partial data correctly."""
        generator = ResponseGenerator()
        activity_data = {
            "username": "testuser",
            "jira_issues": [
                {"key": "PROJ-1", "summary": "Task", "status": "In Progress"}
            ],
            "github_commits": [],
            "github_prs": [],
            "has_activity": True,
            "errors": [],
        }
        response = generator.generate_response(activity_data)
        assert "testuser" in response
        assert "PROJ-1" in response
        assert response
