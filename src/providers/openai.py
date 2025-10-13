"""Response generator using template-based approach.

This module provides a template-based response generator that formats
activity data into natural language responses, simulating AI-powered responses
without requiring external API calls.
"""

import random
from typing import Any

from loguru import logger


class ResponseGenerator:
    """Template-based response generator for team activity queries.

    Formats structured activity data into natural, conversational responses
    using templates and contextual logic. This approach provides AI-like
    responses without external API dependencies.

    Attributes:
        greeting_templates: List of greeting variations
        no_activity_templates: List of no-activity response templates
        activity_intro_templates: List of activity introduction templates
    """

    def __init__(self):
        """Initialize response generator with templates."""
        self.greeting_templates = [
            "Here's what I found about {username}'s recent activity:",
            "Let me tell you what {username} has been working on:",
            "Based on the recent data, here's what {username} is up to:",
            "I've gathered {username}'s recent activity:",
        ]

        self.no_activity_templates = [
            "I couldn't find any recent activity for {username}. They might be working on something not tracked in JIRA or GitHub, or they might be on a break.",
            "It looks like {username} hasn't had any recent activity in JIRA or GitHub over the specified time period.",
            "{username} doesn't appear to have any recent activity. This could mean they're working offline or on tasks not yet committed.",
            "No recent activity found for {username} in the past {days} days. They might be in planning or research mode.",
        ]

        self.activity_intro_templates = [
            "{username} has been quite active! ",
            "{username} is making good progress on multiple fronts. ",
            "Looks like {username} has been busy! ",
            "{username} is actively working on several things. ",
        ]

        logger.info("ResponseGenerator initialized with template system")

    def _format_jira_section(self, issues: list[dict[str, Any]]) -> str:
        """Format JIRA issues into natural language.

        Args:
            issues: List of JIRA issues

        Returns:
            Formatted string describing JIRA issues
        """
        if not issues:
            return ""

        count = len(issues)
        sections = []

        in_progress = [i for i in issues if i.get("status") == "In Progress"]
        done_recently = [i for i in issues if i.get("status") == "Done"]
        todo = [i for i in issues if i.get("status") in ("To Do", "Open", "Backlog")]

        if count == 1:
            issue = issues[0]
            sections.append(
                f'On the JIRA side, they\'re working on {issue["key"]}: "{issue["summary"]}" '
                f"(currently {issue['status']})."
            )
        else:
            sections.append(f"They have {count} JIRA tickets on their plate:")

            if in_progress:
                if len(in_progress) == 1:
                    issue = in_progress[0]
                    sections.append(
                        f'  " Currently working on {issue["key"]}: "{issue["summary"]}"'
                    )
                else:
                    sections.append(f'  " {len(in_progress)} issues in progress:')
                    sections.extend(
                        f'    - {issue["key"]}: "{issue["summary"]}"'
                        for issue in in_progress[:3]
                    )
                    if len(in_progress) > 3:
                        sections.append(f"    ... and {len(in_progress) - 3} more")

            if done_recently:
                if len(done_recently) == 1:
                    issue = done_recently[0]
                    sections.append(
                        f'  " Recently completed {issue["key"]}: "{issue["summary"]}"'
                    )
                else:
                    sections.append(
                        f'  " {len(done_recently)} recently completed issues'
                    )

            if todo:
                sections.append(f'  " {len(todo)} items in backlog/planning')

        return "\n".join(sections)

    def _format_github_commits_section(self, commits: list[dict[str, Any]]) -> str:
        """Format GitHub commits into natural language.

        Args:
            commits: List of GitHub commits

        Returns:
            Formatted string describing commits
        """
        if not commits:
            return ""

        count = len(commits)

        repos = {}
        for commit in commits:
            repo = commit.get("repository", "unknown")
            if repo not in repos:
                repos[repo] = []
            repos[repo].append(commit)

        sections = []

        if count == 1:
            commit = commits[0]
            message = commit["message"].split("\n")[0]
            sections.append(
                f'They pushed 1 commit to {commit["repository"]}: "{message}"'
            )
        elif len(repos) == 1:
            repo_name = list(repos.keys())[0]
            sections.append(f"They've made {count} commits to {repo_name}, including:")
            for commit in commits[:3]:
                message = commit["message"].split("\n")[0][:60]
                sections.append(f'  " "{message}"')
            if count > 3:
                sections.append(f"  ... and {count - 3} more commits")
        else:
            sections.append(
                f"They've been active across {len(repos)} repositories with {count} total commits:"
            )
            for repo, repo_commits in list(repos.items())[:3]:
                sections.append(
                    f'  " {repo}: {len(repo_commits)} commit{"s" if len(repo_commits) > 1 else ""}'
                )
            if len(repos) > 3:
                sections.append(f"  ... and {len(repos) - 3} more repositories")

        return "\n".join(sections)

    def _format_github_prs_section(self, prs: list[dict[str, Any]]) -> str:
        """Format GitHub pull requests into natural language.

        Args:
            prs: List of GitHub pull requests

        Returns:
            Formatted string describing pull requests
        """
        if not prs:
            return ""

        count = len(prs)
        open_prs = [pr for pr in prs if pr.get("state") == "open"]
        merged_prs = [pr for pr in prs if pr.get("state") == "closed"]

        sections = []

        if count == 1:
            pr = prs[0]
            state_str = "has an open" if pr["state"] == "open" else "recently closed a"
            sections.append(
                f'They {state_str} pull request: #{pr["number"]} "{pr["title"]}" in {pr["repository"]}'
            )
        else:
            parts = []
            if open_prs:
                parts.append(f"{len(open_prs)} open")
            if merged_prs:
                parts.append(f"{len(merged_prs)} closed")

            sections.append(
                f"They have {' and '.join(parts)} pull request{'s' if count > 1 else ''}:"
            )

            for pr in prs[:3]:
                state_indicator = "=5" if pr["state"] == "open" else ""
                sections.append(
                    f'  {state_indicator} #{pr["number"]}: "{pr["title"]}" in {pr["repository"]}'
                )

            if count > 3:
                sections.append(f"  ... and {count - 3} more")

        return "\n".join(sections)

    def _generate_summary_statement(self, activity_data: dict[str, Any]) -> str:
        """Generate a summary statement about overall activity.

        Args:
            activity_data: Activity data dictionary

        Returns:
            Summary statement string
        """
        jira_count = len(activity_data.get("jira_issues", []))
        commit_count = len(activity_data.get("github_commits", []))
        pr_count = len(activity_data.get("github_prs", []))

        parts = []
        if jira_count:
            parts.append(f"{jira_count} JIRA issue{'s' if jira_count > 1 else ''}")
        if commit_count:
            parts.append(f"{commit_count} commit{'s' if commit_count > 1 else ''}")
        if pr_count:
            parts.append(f"{pr_count} pull request{'s' if pr_count > 1 else ''}")

        if not parts:
            return ""

        if len(parts) == 1:
            return f"\n\nIn summary, they're actively working on {parts[0]}."
        elif len(parts) == 2:
            return f"\n\nIn summary, they're juggling {parts[0]} and {parts[1]}."
        else:
            return f"\n\nIn summary, they're balancing {parts[0]}, {parts[1]}, and {parts[2]}."

    def generate_response(self, activity_data: dict[str, Any], days: int = 7) -> str:
        """Generate natural language response from activity data.

        Creates a conversational response that summarizes the user's activity
        across JIRA and GitHub using contextual templates.

        Args:
            activity_data: Activity data from DataAggregator
            days: Number of days covered (used in no-activity messages)

        Returns:
            Natural language response string
        """
        username = activity_data.get("username", "the user")

        if not activity_data.get("has_activity"):
            template = random.choice(self.no_activity_templates)
            response = template.format(username=username, days=days)

            if activity_data.get("errors"):
                response += "\n\nNote: There were some issues fetching data:"
                response += "".join(
                    [f'\n  " {error}' for error in activity_data["errors"]]
                )

            logger.info(f"Generated no-activity response for {username}")
            return response

        greeting = random.choice(self.greeting_templates).format(username=username)
        sections = [greeting, ""]

        jira_section = self._format_jira_section(activity_data.get("jira_issues", []))
        if jira_section:
            sections.append(jira_section)

        commits_section = self._format_github_commits_section(
            activity_data.get("github_commits", [])
        )
        if commits_section:
            if jira_section:
                sections.append("")
            sections.append(commits_section)

        prs_section = self._format_github_prs_section(
            activity_data.get("github_prs", [])
        )
        if prs_section:
            if jira_section or commits_section:
                sections.append("")
            sections.append(prs_section)

        summary = self._generate_summary_statement(activity_data)
        if summary:
            sections.append(summary)

        if activity_data.get("errors"):
            sections.append("\n\nNote: Some data may be incomplete due to errors:")
            sections.extend(f'  " {error}' for error in activity_data["errors"])

        response = "\n".join(sections)
        logger.info(f"Generated activity response for {username}")
        return response
