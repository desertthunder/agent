"""Data aggregator for combining JIRA and GitHub activity data.

This module fetches and combines data from multiple sources to provide
a comprehensive view of team member activities.
"""

from typing import Any

from loguru import logger

from providers.github import GitHubClient, GitHubConnError
from providers.jira import JiraClient, JiraConnError


class DataAggregator:
    """Aggregates data from JIRA and GitHub for team activity queries.

    Fetches and combines data from both platforms to provide a unified
    view of what team members are working on.

    Attributes:
        jira_client: Initialized JIRA client
        github_client: Initialized GitHub client
    """

    def __init__(
        self,
        jira_client: JiraClient | None = None,
        github_client: GitHubClient | None = None,
    ):
        """Initialize data aggregator with API clients.

        Args:
            jira_client: JIRA client instance (creates new if not provided)
            github_client: GitHub client instance (creates new if not provided)
        """
        self.jira_client = jira_client or JiraClient()
        self.github_client = github_client or GitHubClient()

    def _fetch_jira_data(self, username: str, result: dict[str, Any]) -> None:
        """Fetch JIRA issues for user and update result dictionary.

        Args:
            username: Display name or email to search for
            result: Result dictionary to update with issues and errors
        """
        try:
            logger.info(f"Resolving JIRA user for {username}")
            user_info = None
            try:
                if hasattr(self.jira_client, "find_user"):
                    user_info = self.jira_client.find_user(username)
            except Exception as e:
                logger.error(f"Unexpected error resolving JIRA user: {e}")
                result["errors"].append(f"JIRA: Unexpected error - {e!s}")
                result["jira_issues"] = []
                return

            if not user_info:
                logger.warning(f"No JIRA user found for '{username}'")
                result["errors"].append(f"JIRA: User '{username}' not found")
                result["jira_issues"] = []
                return

            account_id = user_info.get("accountId", username)
            display_name = user_info.get("displayName", username)
            logger.info(f"Fetching JIRA issues for {display_name} ({account_id})")

            try:
                issues = self.jira_client.get_user_issues(account_id)
                result["jira_issues"] = list(issues or [])
                if result["jira_issues"]:
                    result["has_activity"] = True
            except JiraConnError as e:
                logger.error(f"Error fetching JIRA data for {username}: {e}")
                result["errors"].append(f"JIRA: {e!s}")
                if "410" in str(e):
                    result["errors"].append(
                        f"JIRA: User '{username}' has no Jira product access (license required)"
                    )
            except Exception as e:
                logger.error(f"Unexpected error fetching JIRA issues: {e}")
                result["errors"].append(f"JIRA: Unexpected error - {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error fetching JIRA data: {e}")
            result["errors"].append(f"JIRA: Unexpected error - {e!s}")

    def _fetch_github_commits(
        self, username: str, days: int, result: dict[str, Any]
    ) -> None:
        """Fetch GitHub commits for user and update result dictionary.

        Args:
            username: Username to search for
            days: Number of days to look back
            result: Result dictionary to update with commits and errors
        """
        try:
            logger.info(f"Fetching GitHub commits for {username}")
            result["github_commits"] = self.github_client.get_user_commits(
                username, days=days
            )
            if result["github_commits"]:
                result["has_activity"] = True
        except GitHubConnError as e:
            logger.error(f"Error fetching GitHub commits for {username}: {e}")
            result["errors"].append(f"GitHub commits: {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error fetching GitHub commits: {e}")
            result["errors"].append(f"GitHub commits: Unexpected error - {e!s}")

    def _fetch_github_prs(
        self, username: str, days: int, result: dict[str, Any]
    ) -> None:
        """Fetch GitHub pull requests for user and update result dictionary.

        Args:
            username: Username to search for
            days: Number of days to look back
            result: Result dictionary to update with PRs and errors
        """
        try:
            logger.info(f"Fetching GitHub pull requests for {username}")
            result["github_prs"] = self.github_client.get_user_pull_requests(
                username, days=days
            )
            if result["github_prs"]:
                result["has_activity"] = True
        except GitHubConnError as e:
            logger.error(f"Error fetching GitHub PRs for {username}: {e}")
            result["errors"].append(f"GitHub PRs: {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error fetching GitHub PRs: {e}")
            result["errors"].append(f"GitHub PRs: Unexpected error - {e!s}")

    def get_user_activity(
        self, username: str, query_type: str = "all", days: int = 7
    ) -> dict[str, Any]:
        """Fetch combined activity data for a user.

        Retrieves data from JIRA and/or GitHub based on query type
        and combines into a single response.

        Args:
            username: Username to search for
            query_type: Type of data to fetch ('jira', 'github', or 'all')
            days: Number of days to look back for GitHub data

        Returns:
            Dictionary containing:
                - username: The username searched for
                - jira_issues: List of JIRA issues (if applicable)
                - github_commits: List of commits (if applicable)
                - github_prs: List of pull requests (if applicable)
                - has_activity: Whether any activity was found
                - errors: List of errors encountered
        """
        result = {
            "username": username,
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": [],
        }

        if query_type in ("jira", "all"):
            self._fetch_jira_data(username, result)

        if query_type in ("github", "all"):
            self._fetch_github_commits(username, days, result)
            self._fetch_github_prs(username, days, result)

        logger.info(
            f"Aggregated data for {username}: "
            f"{len(result['jira_issues'])} issues, "
            f"{len(result['github_commits'])} commits, "
            f"{len(result['github_prs'])} PRs"
        )

        return result

    def _format_jira_section(self, issues: list[dict[str, Any]]) -> list[str]:
        """Format JIRA issues section.

        Args:
            issues: List of JIRA issues

        Returns:
            List of formatted lines for JIRA section
        """
        if not issues:
            return []

        lines = [f"\nJIRA Issues ({len(issues)}):"]
        lines.extend(
            f"  - [{issue['key']}] {issue['summary']} ({issue['status']})"
            for issue in issues[:5]
        )

        if len(issues) > 5:
            lines.append(f"  ... and {len(issues) - 5} more")

        return lines

    def _format_commits_section(self, commits: list[dict[str, Any]]) -> list[str]:
        """Format GitHub commits section.

        Args:
            commits: List of GitHub commits

        Returns:
            List of formatted lines for commits section
        """
        if not commits:
            return []

        lines = [f"\nGitHub Commits ({len(commits)}):"]
        for commit in commits[:5]:
            repo = commit["repository"]
            message = commit["message"].split("\n")[0][:60]
            lines.append(f"  - [{repo}] {message}")

        if len(commits) > 5:
            lines.append(f"  ... and {len(commits) - 5} more")

        return lines

    def _format_prs_section(self, prs: list[dict[str, Any]]) -> list[str]:
        """Format GitHub pull requests section.

        Args:
            prs: List of GitHub pull requests

        Returns:
            List of formatted lines for PRs section
        """
        if not prs:
            return []

        lines = [f"\nGitHub Pull Requests ({len(prs)}):"]
        lines.extend(
            f"  - [{pr['repository']}] #{pr['number']}: {pr['title']} ({pr['state']})"
            for pr in prs[:5]
        )

        if len(prs) > 5:
            lines.append(f"  ... and {len(prs) - 5} more")

        return lines

    def format_summary(self, activity_data: dict[str, Any]) -> str:
        """Format activity data into human-readable summary.

        Creates a concise text summary of the user's recent activity
        across JIRA and GitHub.

        Args:
            activity_data: Data returned from get_user_activity()

        Returns:
            Formatted string summary of user activity
        """
        username = activity_data["username"]
        lines = [f"Activity summary for {username}:"]

        lines.extend(self._format_jira_section(activity_data["jira_issues"]))
        lines.extend(self._format_commits_section(activity_data["github_commits"]))
        lines.extend(self._format_prs_section(activity_data["github_prs"]))

        if not activity_data["has_activity"]:
            lines.append("\nNo recent activity found.")

        if activity_data["errors"]:
            lines.append("\nErrors encountered:")
            lines.extend(f"  - {error}" for error in activity_data["errors"])

        return "\n".join(lines)
