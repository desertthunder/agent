"""Query parser for extracting user information from natural language questions.

This module provides simple pattern-matching to extract usernames from
user queries about team member activities.
"""

import re
from typing import Any


class QueryParser:
    """Parser for natural language queries about team member activities.

    Extracts usernames and query intent from questions like:
    - "What is John working on these days?"
    - "Show me Sarah's recent pull requests"
    - "What JIRA tickets is Mike working on?"
    """

    # Common question patterns to match
    PATTERNS = [
        # "What is [Name] working on"
        r"what\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+working\s+on",
        # "recent activity for [Name]"
        r"recent\s+activity\s+for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        # "Show me [Name]'s" (possessive)
        r"show\s+me\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'s\s+",
        # "What are [Name]'s" (possessive)
        r"what\s+are\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'s\s+",
        # "What has [Name] committed/been working"
        r"what\s+has\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:committed|been\s+working)",
        # "What JIRA tickets is [Name] working on"
        r"what\s+(?:jira\s+)?tickets?\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+working",
        # Generic: "for [Name]" or "about [Name]"
        r"(?:for|about)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    ]

    # Intent keywords for determining data sources
    JIRA_KEYWORDS = ["jira", "ticket", "issue", "task"]
    GITHUB_KEYWORDS = ["github", "commit", "pull request", " pr ", "repository", "repo"]

    def parse(self, query: str) -> dict[str, Any]:
        """Parse a natural language query to extract username and intent.

        Args:
            query: Natural language question from the user

        Returns:
            Dictionary containing:
                - username: Extracted username (or None if not found)
                - query_type: Type of query (jira, github, or all)
                - original_query: The original query string
        """
        username = self._extract_username(query)
        query_type = self._determine_query_type(query)

        return {
            "username": username,
            "query_type": query_type,
            "original_query": query,
        }

    def _extract_username(self, query: str) -> str | None:
        """Extract username from query using pattern matching.

        Tries multiple patterns to find a capitalized name in the query.

        Args:
            query: The query string

        Returns:
            Extracted username or None if not found
        """
        for pattern in self.PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fallback: look for any capitalized word that's not at start
        words = query.split()
        for i, word in enumerate(words):
            if i > 0 and word and word[0].isupper() and word.isalpha():
                return word

        return None

    def _determine_query_type(self, query: str) -> str:
        """Determine if query is asking for JIRA, GitHub, or both.

        Args:
            query: The query string

        Returns:
            Query type: 'jira', 'github', or 'all'
        """
        query_lower = query.lower()

        has_jira = any(keyword in query_lower for keyword in self.JIRA_KEYWORDS)
        has_github = any(keyword in query_lower for keyword in self.GITHUB_KEYWORDS)

        if has_jira and not has_github:
            return "jira"
        if has_github and not has_jira:
            return "github"

        return "all"
