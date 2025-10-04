"""Unit tests for query parser."""

import pytest

from src.services.query_parser import QueryParser


class TestQueryParser:
    """Tests for QueryParser class."""

    @pytest.fixture
    def parser(self):
        """Create a query parser instance."""
        return QueryParser()

    def test_parse_what_is_working_on(self, parser):
        """Should extract username from 'What is [Name] working on' questions."""
        result = parser.parse("What is John working on these days?")

        assert result["username"] == "John"
        assert result["query_type"] == "all"
        assert result["original_query"] == "What is John working on these days?"

    def test_parse_show_me_recent_activity(self, parser):
        """Should extract username from 'Show me recent activity' questions."""
        result = parser.parse("Show me recent activity for Sarah")

        assert result["username"] == "Sarah"
        assert result["query_type"] == "all"

    def test_parse_what_has_been_working(self, parser):
        """Should extract username from 'What has [Name] been working' questions."""
        result = parser.parse("What has Mike been working on this week?")

        assert result["username"] == "Mike"
        assert result["query_type"] == "all"

    def test_parse_jira_tickets_question(self, parser):
        """Should extract username and identify JIRA query type."""
        result = parser.parse("What JIRA tickets is John working on?")

        assert result["username"] == "John"
        assert result["query_type"] == "jira"

    def test_parse_show_current_issues(self, parser):
        """Should extract username from 'Show me [Name]'s current issues'."""
        result = parser.parse("Show me Sarah's current issues")

        assert result["username"] == "Sarah"
        assert result["query_type"] == "jira"

    def test_parse_github_commits_question(self, parser):
        """Should extract username and identify GitHub query type."""
        result = parser.parse("What has Mike committed this week?")

        assert result["username"] == "Mike"
        assert result["query_type"] == "github"

    def test_parse_show_recent_pull_requests(self, parser):
        """Should extract username from PR questions."""
        result = parser.parse("Show me Lisa's recent pull requests")

        assert result["username"] == "Lisa"
        assert result["query_type"] == "github"

    def test_parse_full_name(self, parser):
        """Should handle full names (first and last)."""
        result = parser.parse("What is Sarah Johnson working on?")

        assert result["username"] == "Sarah Johnson"
        assert result["query_type"] == "all"

    def test_parse_for_pattern(self, parser):
        """Should extract username from 'for [Name]' pattern."""
        result = parser.parse("Show recent activity for John")

        assert result["username"] == "John"

    def test_parse_about_pattern(self, parser):
        """Should extract username from 'about [Name]' pattern."""
        result = parser.parse("Tell me about Sarah's work")

        assert result["username"] == "Sarah"

    def test_parse_no_username_found(self, parser):
        """Should return None when no username is found."""
        result = parser.parse("What is the status of the project?")

        assert result["username"] is None
        assert result["query_type"] == "all"

    def test_determine_query_type_jira(self, parser):
        """Should identify JIRA-specific queries."""
        result = parser.parse("Show me John's JIRA tasks")

        assert result["query_type"] == "jira"

    def test_determine_query_type_github(self, parser):
        """Should identify GitHub-specific queries."""
        result = parser.parse("What repositories has Sarah committed to?")

        assert result["query_type"] == "github"

    def test_determine_query_type_all(self, parser):
        """Should default to 'all' when no specific platform mentioned."""
        result = parser.parse("What is John working on?")

        assert result["query_type"] == "all"

    def test_parse_case_insensitive(self, parser):
        """Should handle queries in different cases."""
        result1 = parser.parse("what is john working on?")
        result2 = parser.parse("WHAT IS JOHN WORKING ON?")

        assert result1["username"] is not None
        assert result2["username"] is not None

    def test_parse_possessive_form(self, parser):
        """Should handle possessive forms like Sarah's."""
        result = parser.parse("What are Sarah's recent commits?")

        assert result["username"] == "Sarah"
        assert result["query_type"] == "github"
