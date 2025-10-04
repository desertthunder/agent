"""Provider exception classes."""


class GitHubAuthError(Exception):
    """Raised when GitHub authentication fails."""

    pass


class GitHubConnError(Exception):
    """Raised when connection to GitHub fails."""

    pass


class JiraAuthError(Exception):
    """Raised when JIRA authentication fails."""

    pass


class JiraConnError(Exception):
    """Raised when connection to JIRA fails."""

    pass


class JiraUserNotFoundError(Exception):
    """Raised when a user is not found in JIRA."""

    pass
