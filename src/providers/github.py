"""GitHub API provider for fetching user commits and pull requests.

This module provides a client for interacting with the GitHub REST API,
supporting authentication via personal access tokens and fetching user activity.
"""

from datetime import datetime, timedelta
from typing import Any

import requests
from loguru import logger

from settings import GITHUB_TOKEN

from .exceptions import GitHubAuthError, GitHubConnError


class GitHubClient:
    """Client for interacting with GitHub REST API.

    Handles authentication using Bearer token and provides methods to fetch
    user commits and pull requests.

    Attributes:
        token: Personal access token for authentication
        base_url: GitHub API base URL
        session: Configured requests session with auth headers
    """

    def __init__(
        self, token: str | None = None, base_url: str = "https://api.github.com"
    ):
        """Initialize GitHub client with authentication token.

        Args:
            token: Personal access token (defaults to GITHUB_TOKEN from settings)
            base_url: GitHub API base URL (defaults to https://api.github.com)

        Raises:
            GitHubAuthError: If token is missing
        """
        self.token = token or GITHUB_TOKEN
        self.base_url = base_url.rstrip("/")

        if not self.token:
            raise GitHubAuthError("Missing required GitHub token")

        self.session = self._create_session()
        logger.info("GitHub client initialized")

    def _create_session(self) -> requests.Session:
        """Create authenticated requests session.

        Sets up Bearer token authentication and common headers
        for GitHub API requests.

        Returns:
            Configured requests.Session with auth headers
        """
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        return session

    def test_connection(self) -> dict[str, Any]:
        """Test connection and authentication to GitHub.

        Makes a request to /user endpoint to verify credentials.

        Returns:
            Dictionary with connection status and authenticated user info

        Raises:
            GitHubConnError: If connection fails
            GitHubAuthError: If authentication fails
        """
        url = f"{self.base_url}/user"

        try:
            logger.debug(f"Testing connection to {url}")
            response = self.session.get(url, timeout=10)

            if response.status_code == 401:
                logger.error("GitHub authentication failed - invalid token")
                raise GitHubAuthError("Invalid GitHub token")

            if response.status_code == 403:
                logger.error("GitHub access forbidden - check token permissions")
                raise GitHubAuthError("Access forbidden - check token permissions")

            response.raise_for_status()
            user_data = response.json()

            logger.info(f"Successfully connected to GitHub as {user_data.get('login')}")
            return {
                "status": "connected",
                "user": user_data.get("login"),
                "name": user_data.get("name"),
                "email": user_data.get("email"),
            }

        except requests.exceptions.Timeout as e:
            logger.error(f"Connection to {self.base_url} timed out")
            raise GitHubConnError(f"Connection to {self.base_url} timed out") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to {self.base_url}: {e}")
            raise GitHubConnError(
                f"Failed to connect to {self.base_url}. Check network."
            ) from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise GitHubConnError(f"HTTP error: {e}") from e

    def get_user_commits(
        self, username: str, days: int = 7, max_results: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch recent commits by a specific user.

        Uses GitHub search API to find commits authored by the user
        across all accessible repositories.

        Args:
            username: GitHub username to search for
            days: Number of days to look back (default: 7)
            max_results: Maximum number of commits to return (default: 100)

        Returns:
            List of commit dictionaries with key information

        Raises:
            GitHubConnError: If API request fails
        """
        url = f"{self.base_url}/search/commits"

        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = f"author:{username} committer-date:>={since_date}"

        params = {
            "q": query,
            "sort": "committer-date",
            "order": "desc",
            "per_page": min(max_results, 100),
        }

        try:
            logger.debug(f"Fetching commits for user: {username}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            commits = data.get("items", [])

            if not commits:
                logger.warning(
                    f"No commits found for user: {username} in last {days} days"
                )
                return []

            parsed_commits = []
            for commit in commits:
                commit_data = commit.get("commit", {})
                parsed_commits.append(
                    {
                        "sha": commit.get("sha"),
                        "message": commit_data.get("message"),
                        "author": commit_data.get("author", {}).get("name"),
                        "date": commit_data.get("author", {}).get("date"),
                        "repository": commit.get("repository", {}).get("full_name"),
                        "url": commit.get("html_url"),
                    }
                )

            logger.info(f"Found {len(parsed_commits)} commits for {username}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out while fetching commits for {username}")
            raise GitHubConnError("Request timed out") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching commits: {e}")
            raise GitHubConnError(f"Failed to fetch commits: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise GitHubConnError(f"Request failed: {e}") from e
        else:
            return parsed_commits

    def get_user_pull_requests(
        self, username: str, days: int = 7, max_results: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch recent pull requests created by a specific user.

        Uses GitHub search API to find pull requests authored by the user
        across all accessible repositories.

        Args:
            username: GitHub username to search for
            days: Number of days to look back (default: 7)
            max_results: Maximum number of PRs to return (default: 100)

        Returns:
            List of pull request dictionaries with key information

        Raises:
            GitHubConnError: If API request fails
        """
        url = f"{self.base_url}/search/issues"

        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = f"is:pr author:{username} created:>={since_date}"

        params = {
            "q": query,
            "sort": "created",
            "order": "desc",
            "per_page": min(max_results, 100),
        }

        try:
            logger.debug(f"Fetching pull requests for user: {username}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            prs = data.get("items", [])

            if not prs:
                logger.warning(
                    f"No pull requests found for user: {username} in last {days} days"
                )
                return []

            parsed_prs = [
                {
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "state": pr.get("state"),
                    "created_at": pr.get("created_at"),
                    "updated_at": pr.get("updated_at"),
                    "repository": pr.get("repository_url", "").split("/repos/")[-1],
                    "url": pr.get("html_url"),
                    "author": pr.get("user", {}).get("login"),
                }
                for pr in prs
            ]

            logger.info(f"Found {len(parsed_prs)} pull requests for {username}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out while fetching PRs for {username}")
            raise GitHubConnError("Request timed out") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching pull requests: {e}")
            raise GitHubConnError(f"Failed to fetch pull requests: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise GitHubConnError(f"Request failed: {e}") from e
        else:
            return parsed_prs
