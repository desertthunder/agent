"""Unit tests for data aggregator."""

from services.data_aggregator import DataAggregator

from unittest.mock import Mock


from providers.jira import JiraConnError, JiraClient
from providers.github import GitHubConnError, GitHubClient


class TestDataAggregator:
    """Unit tests for DataAggregator class behavior."""

    def setup_method(self):
        self.mock_jira = Mock(spec=JiraClient)
        self.mock_github = Mock(spec=GitHubClient)
        self.aggregator = DataAggregator(
            jira_client=self.mock_jira, github_client=self.mock_github
        )

    def test_get_user_activity_jira_only_success(self):
        """Should aggregate JIRA issues correctly."""
        self.mock_jira.find_user.return_value = {
            "accountId": "abc123",
            "displayName": "Test User",
        }
        self.mock_jira.get_user_issues.return_value = [
            {"key": "PROJ-1", "summary": "Fix bug", "status": "Done"}
        ]

        result = self.aggregator.get_user_activity("Test User", query_type="jira")

        assert result["jira_issues"]
        assert result["has_activity"] is True
        assert result["errors"] == []
        self.mock_jira.get_user_issues.assert_called_once_with("abc123")

    def test_get_user_activity_github_only_success(self):
        """Should aggregate GitHub commits and PRs correctly."""
        self.mock_github.get_user_commits.return_value = [
            {"repository": "repo1", "message": "Initial commit"}
        ]
        self.mock_github.get_user_pull_requests.return_value = [
            {
                "repository": "repo1",
                "number": 1,
                "title": "Add feature",
                "state": "open",
            }
        ]

        result = self.aggregator.get_user_activity("dev", query_type="github", days=7)

        assert result["github_commits"]
        assert result["github_prs"]
        assert result["has_activity"] is True
        assert result["errors"] == []

    def test_get_user_activity_all_sources(self):
        """Should combine JIRA + GitHub data."""
        self.mock_jira.find_user.return_value = {
            "accountId": "acc123",
            "displayName": "Dev",
        }
        self.mock_jira.get_user_issues.return_value = [
            {"key": "PROJ-2", "summary": "Implement feature", "status": "In Progress"}
        ]
        self.mock_github.get_user_commits.return_value = [
            {"repository": "repo2", "message": "Commit msg"}
        ]
        self.mock_github.get_user_pull_requests.return_value = []

        result = self.aggregator.get_user_activity("Dev", query_type="all", days=7)
        assert result["has_activity"] is True
        assert len(result["jira_issues"]) == 1
        assert len(result["github_commits"]) == 1
        assert result["errors"] == []

    def test_jira_user_not_found(self):
        """Should handle unknown JIRA user gracefully."""
        self.mock_jira.find_user.return_value = None
        result = self.aggregator.get_user_activity("Ghost", query_type="jira")
        assert "JIRA: User 'Ghost' not found" in result["errors"][0]
        assert result["has_activity"] is False

    def test_jira_conn_error(self):
        """Should handle JiraConnError correctly."""
        self.mock_jira.find_user.return_value = {
            "accountId": "abc",
            "displayName": "Broken",
        }
        self.mock_jira.get_user_issues.side_effect = JiraConnError("timeout")

        result = self.aggregator.get_user_activity("Broken", query_type="jira")
        assert any("JIRA:" in err for err in result["errors"])
        assert result["has_activity"] is False

    def test_github_conn_error(self):
        """Should handle GitHub connection errors correctly."""
        self.mock_jira.find_user.return_value = {
            "accountId": "ok",
            "displayName": "User",
        }
        self.mock_jira.get_user_issues.return_value = []
        self.mock_github.get_user_commits.side_effect = GitHubConnError("bad gateway")
        self.mock_github.get_user_pull_requests.return_value = []

        result = self.aggregator.get_user_activity("User", query_type="all", days=3)
        assert any("GitHub commits" in e for e in result["errors"])
        assert result["has_activity"] is False

    def test_jira_unexpected_error(self):
        """Should handle generic exceptions from JIRA path."""
        self.mock_jira.find_user.side_effect = Exception("mock fail")

        result = self.aggregator.get_user_activity("Boom", query_type="jira")
        assert any("Unexpected" in e for e in result["errors"])
        assert result["has_activity"] is False

    def test_github_unexpected_error(self):
        """Should handle generic GitHub errors."""
        self.mock_jira.find_user.return_value = {
            "accountId": "ok",
            "displayName": "User",
        }
        self.mock_jira.get_user_issues.return_value = []
        self.mock_github.get_user_commits.side_effect = Exception("random failure")
        self.mock_github.get_user_pull_requests.side_effect = Exception(
            "random failure"
        )

        result = self.aggregator.get_user_activity("User", query_type="github", days=3)
        assert any("Unexpected error" in e for e in result["errors"])
        assert result["has_activity"] is False

    def test_get_user_activity_no_results(self):
        """Should return clean output with no activity."""
        self.mock_jira.find_user.return_value = {
            "accountId": "x",
            "displayName": "Nobody",
        }
        self.mock_jira.get_user_issues.return_value = []
        self.mock_github.get_user_commits.return_value = []
        self.mock_github.get_user_pull_requests.return_value = []

        result = self.aggregator.get_user_activity("Nobody", query_type="all", days=5)
        assert result["has_activity"] is False
        assert result["errors"] == []

    def test_jira_410_gone(self):
        """Should append license restriction message on 410 Gone."""
        self.mock_jira.find_user.return_value = {
            "accountId": "abc",
            "displayName": "GhostUser",
        }
        self.mock_jira.get_user_issues.side_effect = JiraConnError("410 Gone")

        result = self.aggregator.get_user_activity("GhostUser", query_type="jira")
        assert any("license required" in err for err in result["errors"])
        assert result["has_activity"] is False
