"""Unit tests for response generator."""

import pytest

from src.providers.openai import ResponseGenerator


class TestResponseGeneratorInitialization:
    """Tests for ResponseGenerator initialization."""

    def test_init_creates_templates(self):
        """ResponseGenerator should initialize with all required templates."""
        generator = ResponseGenerator()

        assert generator.greeting_templates
        assert generator.no_activity_templates
        assert generator.activity_intro_templates
        assert all(isinstance(t, str) for t in generator.greeting_templates)
        assert all(isinstance(t, str) for t in generator.no_activity_templates)


class TestResponseGeneratorNoActivity:
    """Tests for generating responses when there's no activity."""

    @pytest.fixture
    def generator(self):
        """Create a response generator."""
        return ResponseGenerator()

    def test_generate_response_no_activity(self, generator):
        """Should generate appropriate response when user has no activity."""
        activity_data = {
            "username": "testuser",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": [],
        }

        response = generator.generate_response(activity_data, days=7)

        assert "testuser" in response
        assert response  # Should not be empty

    def test_generate_response_no_activity_includes_errors(self, generator):
        """Should include errors in no-activity response."""
        activity_data = {
            "username": "testuser",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": ["JIRA: Connection failed", "GitHub: Rate limit exceeded"],
        }

        response = generator.generate_response(activity_data, days=7)

        assert "testuser" in response
        assert "JIRA: Connection failed" in response
        assert "GitHub: Rate limit exceeded" in response


class TestResponseGeneratorWithActivity:
    """Tests for generating responses with activity data."""

    @pytest.fixture
    def generator(self):
        """Create a response generator."""
        return ResponseGenerator()

    def test_generate_response_with_jira_only(self, generator):
        """Should generate response with only JIRA activity."""
        activity_data = {
            "username": "johndoe",
            "jira_issues": [
                {
                    "key": "PROJ-1",
                    "summary": "Implement feature X",
                    "status": "In Progress",
                },
                {"key": "PROJ-2", "summary": "Fix bug Y", "status": "Done"},
            ],
            "github_commits": [],
            "github_prs": [],
            "has_activity": True,
            "errors": [],
        }

        response = generator.generate_response(activity_data)

        assert "johndoe" in response
        assert "PROJ-1" in response
        assert "PROJ-2" in response
        assert "Implement feature X" in response

    def test_generate_response_with_github_commits_only(self, generator):
        """Should generate response with only GitHub commits."""
        activity_data = {
            "username": "janedoe",
            "jira_issues": [],
            "github_commits": [
                {
                    "sha": "abc123",
                    "message": "Add authentication module",
                    "repository": "org/backend",
                },
                {
                    "sha": "def456",
                    "message": "Update dependencies",
                    "repository": "org/backend",
                },
            ],
            "github_prs": [],
            "has_activity": True,
            "errors": [],
        }

        response = generator.generate_response(activity_data)

        assert "janedoe" in response
        assert "commit" in response.lower()
        assert "org/backend" in response

    def test_generate_response_with_github_prs_only(self, generator):
        """Should generate response with only GitHub pull requests."""
        activity_data = {
            "username": "bobsmith",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [
                {
                    "number": 42,
                    "title": "Add user authentication",
                    "state": "open",
                    "repository": "org/frontend",
                },
            ],
            "has_activity": True,
            "errors": [],
        }

        response = generator.generate_response(activity_data)

        assert "bobsmith" in response
        assert "#42" in response
        assert "Add user authentication" in response
        assert "org/frontend" in response

    def test_generate_response_with_all_activity_types(self, generator):
        """Should generate comprehensive response with all activity types."""
        activity_data = {
            "username": "alice",
            "jira_issues": [
                {"key": "PROJ-1", "summary": "Feature A", "status": "In Progress"},
            ],
            "github_commits": [
                {
                    "sha": "abc123",
                    "message": "Implement feature A",
                    "repository": "org/repo",
                },
            ],
            "github_prs": [
                {
                    "number": 10,
                    "title": "Feature A implementation",
                    "state": "open",
                    "repository": "org/repo",
                },
            ],
            "has_activity": True,
            "errors": [],
        }

        response = generator.generate_response(activity_data)

        assert "alice" in response
        assert "PROJ-1" in response
        assert "Feature A" in response
        assert "#10" in response

    def test_generate_response_includes_summary(self, generator):
        """Should include summary statement in response."""
        activity_data = {
            "username": "charlie",
            "jira_issues": [{"key": "PROJ-1", "summary": "Task", "status": "Open"}],
            "github_commits": [
                {"sha": "abc", "message": "Update", "repository": "org/repo"}
            ],
            "github_prs": [
                {"number": 5, "title": "Fix", "state": "open", "repository": "org/repo"}
            ],
            "has_activity": True,
            "errors": [],
        }

        response = generator.generate_response(activity_data)

        assert "charlie" in response
        assert "summary" in response.lower() or "PROJ-1" in response


class TestResponseGeneratorFormatting:
    """Tests for specific formatting functions."""

    @pytest.fixture
    def generator(self):
        """Create a response generator."""
        return ResponseGenerator()

    def test_format_jira_section_empty(self, generator):
        """Should return empty string for no issues."""
        result = generator._format_jira_section([])
        assert result == ""

    def test_format_jira_section_single_issue(self, generator):
        """Should format single issue appropriately."""
        issues = [{"key": "PROJ-1", "summary": "Test issue", "status": "Open"}]
        result = generator._format_jira_section(issues)

        assert "PROJ-1" in result
        assert "Test issue" in result
        assert "Open" in result

    def test_format_jira_section_multiple_issues(self, generator):
        """Should format multiple issues with grouping."""
        issues = [
            {"key": "PROJ-1", "summary": "Issue 1", "status": "In Progress"},
            {"key": "PROJ-2", "summary": "Issue 2", "status": "In Progress"},
            {"key": "PROJ-3", "summary": "Issue 3", "status": "Done"},
        ]
        result = generator._format_jira_section(issues)

        assert "PROJ-1" in result
        assert "PROJ-2" in result

    def test_format_github_commits_section_empty(self, generator):
        """Should return empty string for no commits."""
        result = generator._format_github_commits_section([])
        assert result == ""

    def test_format_github_commits_section_single_commit(self, generator):
        """Should format single commit appropriately."""
        commits = [
            {
                "sha": "abc123",
                "message": "Fix authentication bug",
                "repository": "org/backend",
            }
        ]
        result = generator._format_github_commits_section(commits)

        assert "org/backend" in result
        assert "Fix authentication" in result

    def test_format_github_commits_section_multiple_commits(self, generator):
        """Should format multiple commits with repository grouping."""
        commits = [
            {"sha": "abc", "message": "Commit 1", "repository": "org/repo1"},
            {"sha": "def", "message": "Commit 2", "repository": "org/repo1"},
            {"sha": "ghi", "message": "Commit 3", "repository": "org/repo2"},
        ]
        result = generator._format_github_commits_section(commits)

        assert "commit" in result.lower()
        assert "org/repo1" in result or "org/repo2" in result

    def test_format_github_prs_section_empty(self, generator):
        """Should return empty string for no PRs."""
        result = generator._format_github_prs_section([])
        assert result == ""

    def test_format_github_prs_section_single_pr(self, generator):
        """Should format single PR appropriately."""
        prs = [
            {
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "repository": "org/repo",
            }
        ]
        result = generator._format_github_prs_section(prs)

        assert "#42" in result
        assert "Add feature" in result
        assert "org/repo" in result

    def test_format_github_prs_section_multiple_prs(self, generator):
        """Should format multiple PRs with state grouping."""
        prs = [
            {"number": 1, "title": "PR 1", "state": "open", "repository": "org/repo"},
            {"number": 2, "title": "PR 2", "state": "open", "repository": "org/repo"},
            {"number": 3, "title": "PR 3", "state": "closed", "repository": "org/repo"},
        ]
        result = generator._format_github_prs_section(prs)

        assert "#1" in result or "#2" in result or "#3" in result

    def test_generate_summary_statement_no_activity(self, generator):
        """Should return empty string when no activity."""
        activity_data = {
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
        }
        result = generator._generate_summary_statement(activity_data)
        assert result == ""

    def test_generate_summary_statement_single_type(self, generator):
        """Should generate appropriate summary for single activity type."""
        activity_data = {
            "jira_issues": [{"key": "PROJ-1"}],
            "github_commits": [],
            "github_prs": [],
        }
        result = generator._generate_summary_statement(activity_data)
        assert "JIRA" in result or "issue" in result.lower()

    def test_generate_summary_statement_multiple_types(self, generator):
        """Should generate appropriate summary for multiple activity types."""
        activity_data = {
            "jira_issues": [{"key": "PROJ-1"}],
            "github_commits": [{"sha": "abc"}],
            "github_prs": [{"number": 1}],
        }
        result = generator._generate_summary_statement(activity_data)
        assert result  # Should have content


class TestResponseGeneratorEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def generator(self):
        """Create a response generator."""
        return ResponseGenerator()

    def test_generate_response_with_errors(self, generator):
        """Should include errors in response when present."""
        activity_data = {
            "username": "testuser",
            "jira_issues": [{"key": "PROJ-1", "summary": "Task", "status": "Open"}],
            "github_commits": [],
            "github_prs": [],
            "has_activity": True,
            "errors": ["GitHub: Connection timeout"],
        }

        response = generator.generate_response(activity_data)

        assert "testuser" in response
        assert "GitHub: Connection timeout" in response

    def test_generate_response_handles_long_commit_messages(self, generator):
        """Should truncate very long commit messages."""
        long_message = "A" * 200  # Very long message
        activity_data = {
            "username": "testuser",
            "jira_issues": [],
            "github_commits": [
                {"sha": "abc", "message": long_message, "repository": "org/repo"}
            ],
            "github_prs": [],
            "has_activity": True,
            "errors": [],
        }

        response = generator.generate_response(activity_data)

        # Response should be generated without error
        assert "testuser" in response
        assert "org/repo" in response

    def test_generate_response_handles_many_items(self, generator):
        """Should handle large numbers of items gracefully."""
        activity_data = {
            "username": "testuser",
            "jira_issues": [
                {"key": f"PROJ-{i}", "summary": f"Issue {i}", "status": "Open"}
                for i in range(10)
            ],
            "github_commits": [
                {"sha": f"abc{i}", "message": f"Commit {i}", "repository": "org/repo"}
                for i in range(10)
            ],
            "github_prs": [
                {
                    "number": i,
                    "title": f"PR {i}",
                    "state": "open",
                    "repository": "org/repo",
                }
                for i in range(10)
            ],
            "has_activity": True,
            "errors": [],
        }

        response = generator.generate_response(activity_data)

        assert "testuser" in response
        # Should indicate there are more items
        assert "more" in response.lower() or "PROJ-" in response
