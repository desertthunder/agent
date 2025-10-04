"""JIRA API provider for fetching user issues and activity.

This module provides a client for interacting with the JIRA REST API,
supporting authentication via API tokens and fetching user-assigned issues.
"""

import base64
from typing import Any

import requests
from loguru import logger

from settings import JIRA_API_TOKEN, JIRA_BASE_URL, JIRA_EMAIL


class JiraAuthError(Exception):
    """Raised when JIRA authentication fails."""

    pass


class JiraConnError(Exception):
    """Raised when connection to JIRA fails."""

    pass


class JiraUserNotFoundError(Exception):
    """Raised when a user is not found in JIRA."""

    pass


class JiraClient:
    """Client for interacting with JIRA REST API.

    Handles authentication using Basic Auth with email and API token,
    and provides methods to fetch user issues and issue details.

    Attributes:
        base_url: The base URL of the JIRA instance
        email: User email for authentication
        api_token: API token for authentication
        session: Configured requests session with auth headers
    """

    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ):
        """Initialize JIRA client with credentials.

        Args:
            base_url: JIRA instance URL (defaults to JIRA_BASE_URL from settings)
            email: User email (defaults to JIRA_EMAIL from settings)
            api_token: API token (defaults to JIRA_API_TOKEN from settings)

        Raises:
            JiraAuthenticationError: If required credentials are missing
        """
        self.base_url = (base_url or JIRA_BASE_URL).rstrip("/")
        self.email = email or JIRA_EMAIL
        self.api_token = api_token or JIRA_API_TOKEN

        if not all([self.base_url, self.email, self.api_token]):
            missing = []
            if not self.base_url:
                missing.append("JIRA_BASE_URL")
            if not self.email:
                missing.append("JIRA_EMAIL")
            if not self.api_token:
                missing.append("JIRA_API_TOKEN")

            message = f"Missing required JIRA credentials: {', '.join(missing)}"
            raise JiraAuthError(message)

        self.session = self._create_session()
        logger.info(f"JIRA client initialized for {self.base_url}")

    def _create_session(self) -> requests.Session:
        """Create authenticated requests session.

        Encodes credentials as Base64 for Basic Auth and sets up
        common headers for all JIRA API requests.

        Returns:
            Configured requests.Session with auth headers
        """
        session = requests.Session()
        auth_string = f"{self.email}:{self.api_token}"
        auth_bytes = auth_string.encode("ascii")
        base64_auth = base64.b64encode(auth_bytes).decode("ascii")

        session.headers.update(
            {
                "Authorization": f"Basic {base64_auth}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        return session

    def test_connection(self) -> dict[str, Any]:
        """Test connection and authentication to JIRA.

        Makes a lightweight API call to verify credentials and connectivity.

        Returns:
            Dictionary with connection status and server info

        Raises:
            JiraConnectionError: If connection fails
            JiraAuthenticationError: If authentication fails
        """
        url = f"{self.base_url}/rest/api/2/myself"

        try:
            logger.debug(f"Testing connection to {url}")
            response = self.session.get(url, timeout=10)

            if response.status_code == 401:
                logger.error("JIRA authentication failed - invalid credentials")
                raise JiraAuthError("Invalid JIRA credentials")

            if response.status_code == 403:
                logger.error("JIRA access forbidden - check permissions")
                raise JiraAuthError("Access forbidden - check API token permissions")

            response.raise_for_status()
            user_data = response.json()

            logger.info(
                f"Successfully connected to JIRA as {user_data.get('emailAddress')}"
            )
            return {
                "status": "connected",
                "user": user_data.get("displayName"),
                "email": user_data.get("emailAddress"),
            }

        except requests.exceptions.Timeout as e:
            logger.error(f"Connection to {self.base_url} timed out")
            raise JiraConnError(f"Connection to {self.base_url} timed out") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to {self.base_url}: {e}")
            raise JiraConnError(
                f"Failed to connect to {self.base_url}. Check URL and network."
            ) from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise JiraConnError(f"HTTP error: {e}") from e

    def get_user_issues(
        self, username: str, max_results: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch issues assigned to a specific user.

        Uses JQL query to search for issues assigned to the user,
        ordered by most recently updated.

        Args:
            username: JIRA username or email to search for
            max_results: Maximum number of issues to return (default: 50)

        Returns:
            List of issue dictionaries with key fields extracted

        Raises:
            JiraConnectionError: If API request fails
            JiraUserNotFoundError: If user has no issues (may not exist)
        """
        url = f"{self.base_url}/rest/api/2/search"
        jql = f'assignee = "{username}" ORDER BY updated DESC'

        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,status,assignee,updated,description,priority,created",
        }

        try:
            logger.debug(f"Fetching issues for user: {username}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            issues = data.get("issues", [])

            if not issues:
                logger.warning(f"No issues found for user: {username}")
                return []

            parsed_issues = []
            for issue in issues:
                fields = issue.get("fields", {})
                parsed_issues.append(
                    {
                        "key": issue.get("key"),
                        "summary": fields.get("summary"),
                        "status": fields.get("status", {}).get("name"),
                        "assignee": fields.get("assignee", {}).get("displayName"),
                        "updated": fields.get("updated"),
                        "created": fields.get("created"),
                        "description": fields.get("description"),
                        "priority": fields.get("priority", {}).get("name"),
                    }
                )

            logger.info(f"Found {len(parsed_issues)} issues for {username}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out while fetching issues for {username}")
            raise JiraConnError("Request timed out") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching issues: {e}")
            raise JiraConnError(f"Failed to fetch issues: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise JiraConnError(f"Request failed: {e}") from e
        else:
            return parsed_issues

    def get_issue_details(self, issue_key: str) -> dict[str, Any]:
        """Fetch detailed information for a specific issue.

        Retrieves full issue details including status, description,
        comments, and update history.

        Args:
            issue_key: JIRA issue key (e.g., "PROJ-123")

        Returns:
            Dictionary with detailed issue information

        Raises:
            JiraConnectionError: If API request fails
        """
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        params = {"expand": "changelog"}

        try:
            logger.debug(f"Fetching details for issue: {issue_key}")
            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 404:
                logger.error(f"Issue not found: {issue_key}")
                raise JiraConnError(f"Issue {issue_key} not found")

            response.raise_for_status()
            data = response.json()
            fields = data.get("fields", {})

            issue_details = {
                "key": data.get("key"),
                "summary": fields.get("summary"),
                "description": fields.get("description"),
                "status": fields.get("status", {}).get("name"),
                "assignee": fields.get("assignee", {}).get("displayName"),
                "reporter": fields.get("reporter", {}).get("displayName"),
                "priority": fields.get("priority", {}).get("name"),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "resolution": fields.get("resolution", {}).get("name")
                if fields.get("resolution")
                else None,
                "changelog": data.get("changelog", {}).get("histories", []),
            }

            logger.info(f"Retrieved details for {issue_key}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out while fetching {issue_key}")
            raise JiraConnError("Request timed out") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching issue {issue_key}: {e}")
            raise JiraConnError(f"Failed to fetch issue: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise JiraConnError(f"Request failed: {e}") from e
        else:
            return issue_details
