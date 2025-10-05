"""View layer & rich abstractions.

This module provides Rich-based display components for the CLI,
including formatted output for activity data, errors, and status information.
"""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def display_welcome():
    """Display welcome banner."""
    welcome_text = Text()
    welcome_text.append("Team Activity Monitor\n", style="bold cyan")
    welcome_text.append("Ask questions about team member activities", style="dim")

    panel = Panel(
        welcome_text,
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


def display_activity_response(response_data: dict[str, Any]):
    """Display formatted activity response.

    Shows the AI-generated response in a nicely formatted panel,
    along with structured data in tables.

    Args:
        response_data: Response data from API containing activity info
    """
    ai_response = response_data.get("ai_response", "No response generated")
    response_panel = Panel(
        ai_response,
        title=f"[bold cyan]Activity for {response_data['parsed']['username']}",
        border_style="green",
        padding=(1, 2),
    )
    console.print(response_panel)

    activity = response_data.get("activity", {})

    if activity.get("jira_issues"):
        _display_jira_table(activity["jira_issues"])

    if activity.get("github_commits"):
        _display_github_commits_table(activity["github_commits"])

    if activity.get("github_prs"):
        _display_github_prs_table(activity["github_prs"])

    if activity.get("errors"):
        _display_errors(activity["errors"])


def _display_jira_table(issues: list[dict[str, Any]]):
    """Display JIRA issues in a table.

    Args:
        issues: List of JIRA issues
    """
    if not issues:
        return

    table = Table(
        title="JIRA Issues",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )

    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Summary", style="white")
    table.add_column("Status", style="yellow")

    for issue in issues[:10]:
        status_style = "green" if issue["status"] == "Done" else "yellow"
        table.add_row(
            issue["key"],
            issue["summary"][:60] + "..."
            if len(issue["summary"]) > 60
            else issue["summary"],
            f"[{status_style}]{issue['status']}[/{status_style}]",
        )

    if len(issues) > 10:
        table.caption = f"Showing 10 of {len(issues)} issues"

    console.print(table)


def _display_github_commits_table(commits: list[dict[str, Any]]):
    """Display GitHub commits in a table.

    Args:
        commits: List of GitHub commits
    """
    if not commits:
        return

    table = Table(
        title="Recent GitHub Commits",
        show_header=True,
        header_style="bold blue",
        border_style="dim",
    )

    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("Message", style="white")
    table.add_column("Date", style="dim")

    for commit in commits[:10]:
        message = commit["message"].split("\n")[0]
        message = message[:50] + "..." if len(message) > 50 else message
        date = commit.get("date", "")[:10]

        table.add_row(commit["repository"], message, date)

    if len(commits) > 10:
        table.caption = f"Showing 10 of {len(commits)} commits"

    console.print(table)


def _display_github_prs_table(prs: list[dict[str, Any]]):
    """Display GitHub pull requests in a table.

    Args:
        prs: List of GitHub pull requests
    """
    if not prs:
        return

    table = Table(
        title="GitHub Pull Requests",
        show_header=True,
        header_style="bold blue",
        border_style="dim",
    )

    table.add_column("PR", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("State", style="yellow")

    for pr in prs[:10]:
        state_style = "green" if pr["state"] == "open" else "dim"
        pr_number = f"#{pr['number']}"
        title = pr["title"][:50] + "..." if len(pr["title"]) > 50 else pr["title"]

        table.add_row(
            pr_number,
            title,
            f"[{state_style}]{pr['state']}[/{state_style}]",
        )

    if len(prs) > 10:
        table.caption = f"Showing 10 of {len(prs)} PRs"

    console.print(table)


def _display_errors(errors: list[str]):
    """Display errors in a warning panel.

    Args:
        errors: List of error messages
    """
    error_text = Text()
    error_text.append(
        "Some errors occurred while fetching data:\n\n", style="bold yellow"
    )

    for error in errors:
        error_text.append(f"  • {error}\n", style="yellow")

    panel = Panel(
        error_text,
        title="[bold yellow]Warnings",
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)


def display_error(message: str, details: str | None = None):
    """Display error message.

    Args:
        message: Main error message
        details: Optional detailed error information
    """
    error_text = Text()
    error_text.append(message, style="bold red")

    if details:
        error_text.append("\n\n", style="")
        error_text.append(details, style="dim red")

    panel = Panel(
        error_text,
        title="[bold red]Error",
        border_style="red",
        padding=(1, 2),
    )
    console.print(panel)


def display_status(jira_status: str, github_status: str):
    """Display API connection status.

    Args:
        jira_status: JIRA connection status
        github_status: GitHub connection status
    """
    table = Table(
        title="API Connection Status",
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
    )

    table.add_column("Service", style="cyan")
    table.add_column("Status", style="white")

    jira_style = "green" if "connected" in jira_status else "red"
    github_style = "green" if "connected" in github_status else "red"

    table.add_row("JIRA", f"[{jira_style}]{jira_status}[/{jira_style}]")
    table.add_row("GitHub", f"[{github_style}]{github_status}[/{github_style}]")

    console.print(table)


def display_suggestion(message: str):
    """Display helpful suggestion.

    Args:
        message: Suggestion message
    """
    suggestion_text = Text(message, style="italic cyan")
    console.print(suggestion_text)


def print_info(message: str):
    """Print informational message.

    Args:
        message: Info message
    """
    console.print(f"[cyan]ℹ[/cyan] {message}")


def print_success(message: str):
    """Print success message.

    Args:
        message: Success message
    """
    console.print(f"[green]✓[/green] {message}")
