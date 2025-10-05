"""Unit tests for CLI."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.cli.__main__ import cli
from src.providers.github import GitHubConnError
from src.providers.jira import JiraAuthError, JiraConnError


class TestCLIQuery:
    """Tests for the query command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @patch("src.cli.__main__.ResponseGenerator")
    @patch("src.cli.__main__.DataAggregator")
    @patch("src.cli.__main__.QueryParser")
    def test_query_success(
        self, mock_parser_cls, mock_aggregator_cls, mock_generator_cls, runner
    ):
        """Should successfully process a query command."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {
            "username": "John",
            "query_type": "all",
        }
        mock_parser_cls.return_value = mock_parser

        mock_aggregator = Mock()
        mock_aggregator.get_user_activity.return_value = {
            "username": "John",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": [],
        }
        mock_aggregator_cls.return_value = mock_aggregator

        mock_generator = Mock()
        mock_generator.generate_response.return_value = "John has no recent activity."
        mock_generator_cls.return_value = mock_generator

        result = runner.invoke(cli, ["query", "What is John working on?"])
        assert result.exit_code == 0
        assert "John has no recent activity" in result.output

    def test_query_no_question(self, runner):
        """Should return error when no question provided."""
        result = runner.invoke(cli, ["query"])
        assert result.exit_code == 1
        assert "No question provided" in result.output

    @patch("src.cli.__main__.QueryParser")
    def test_query_no_username_extracted(self, mock_parser_cls, runner):
        """Should return error when username cannot be extracted."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {
            "username": None,
            "query_type": "all",
        }
        mock_parser_cls.return_value = mock_parser

        result = runner.invoke(cli, ["query", "What is happening?"])
        assert result.exit_code == 1
        assert "Could not extract username" in result.output

    def test_query_invalid_days(self, runner):
        """Should return error for invalid days parameter."""
        result = runner.invoke(
            cli, ["query", "What is John working on?", "--days", "500"]
        )
        assert result.exit_code == 1
        assert "Invalid days value" in result.output

    @patch("src.cli.__main__.ResponseGenerator")
    @patch("src.cli.__main__.DataAggregator")
    @patch("src.cli.__main__.QueryParser")
    def test_query_jira_auth_error(
        self, mock_parser_cls, mock_aggregator_cls, mock_generator_cls, runner
    ):
        """Should handle JIRA authentication errors."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {
            "username": "John",
            "query_type": "all",
        }
        mock_parser_cls.return_value = mock_parser

        mock_aggregator = Mock()
        mock_aggregator.get_user_activity.side_effect = JiraAuthError(
            "Invalid credentials"
        )
        mock_aggregator_cls.return_value = mock_aggregator

        result = runner.invoke(cli, ["query", "What is John working on?"])
        assert result.exit_code == 1
        assert (
            "Authentication Error" in result.output
            or "Invalid credentials" in result.output
        )

    @patch("src.cli.__main__.ResponseGenerator")
    @patch("src.cli.__main__.DataAggregator")
    @patch("src.cli.__main__.QueryParser")
    def test_query_github_conn_error(
        self, mock_parser_cls, mock_aggregator_cls, mock_generator_cls, runner
    ):
        """Should handle GitHub connection errors."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {
            "username": "John",
            "query_type": "all",
        }
        mock_parser_cls.return_value = mock_parser

        mock_aggregator = Mock()
        mock_aggregator.get_user_activity.side_effect = GitHubConnError(
            "Connection timeout"
        )
        mock_aggregator_cls.return_value = mock_aggregator

        result = runner.invoke(cli, ["query", "What is John working on?"])
        assert result.exit_code == 1
        assert (
            "Connection Error" in result.output or "Connection timeout" in result.output
        )

    @patch("src.cli.__main__.ResponseGenerator")
    @patch("src.cli.__main__.DataAggregator")
    @patch("src.cli.__main__.QueryParser")
    def test_query_with_table_flag(
        self, mock_parser_cls, mock_aggregator_cls, mock_generator_cls, runner
    ):
        """Should display tables when --table flag is used."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {
            "username": "John",
            "query_type": "all",
        }
        mock_parser_cls.return_value = mock_parser

        mock_aggregator = Mock()
        mock_aggregator.get_user_activity.return_value = {
            "username": "John",
            "jira_issues": [{"key": "PROJ-1", "summary": "Test", "status": "Open"}],
            "github_commits": [],
            "github_prs": [],
            "has_activity": True,
            "errors": [],
        }
        mock_aggregator_cls.return_value = mock_aggregator

        mock_generator = Mock()
        mock_generator.generate_response.return_value = "John is working on PROJ-1."
        mock_generator_cls.return_value = mock_generator

        result = runner.invoke(cli, ["query", "What is John working on?", "--table"])

        assert result.exit_code == 0

    @patch("src.cli.__main__.ResponseGenerator")
    @patch("src.cli.__main__.DataAggregator")
    @patch("src.cli.__main__.QueryParser")
    def test_query_with_custom_days(
        self, mock_parser_cls, mock_aggregator_cls, mock_generator_cls, runner
    ):
        """Should pass custom days parameter to aggregator."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {
            "username": "John",
            "query_type": "all",
        }
        mock_parser_cls.return_value = mock_parser

        mock_aggregator = Mock()
        mock_aggregator.get_user_activity.return_value = {
            "username": "John",
            "jira_issues": [],
            "github_commits": [],
            "github_prs": [],
            "has_activity": False,
            "errors": [],
        }
        mock_aggregator_cls.return_value = mock_aggregator

        mock_generator = Mock()
        mock_generator.generate_response.return_value = "No activity."
        mock_generator_cls.return_value = mock_generator

        result = runner.invoke(
            cli, ["query", "What is John working on?", "--days", "14"]
        )

        assert result.exit_code == 0
        mock_aggregator.get_user_activity.assert_called_once_with(
            username="John", query_type="all", days=14
        )


class TestCLIStatus:
    """Tests for the status command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @patch("src.cli.__main__.GitHubClient")
    @patch("src.cli.__main__.JiraClient")
    def test_status_all_connected(self, mock_jira_cls, mock_github_cls, runner):
        """Should show success when both APIs are connected."""
        mock_jira = Mock()
        mock_jira.test_connection.return_value = {"user": "jira_user"}
        mock_jira_cls.return_value = mock_jira

        mock_github = Mock()
        mock_github.test_connection.return_value = {"user": "github_user"}
        mock_github_cls.return_value = mock_github

        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "connected" in result.output.lower()

    @patch("src.cli.__main__.GitHubClient")
    @patch("src.cli.__main__.JiraClient")
    def test_status_jira_auth_error(self, mock_jira_cls, mock_github_cls, runner):
        """Should show error when JIRA auth fails."""
        mock_jira = Mock()
        mock_jira.test_connection.side_effect = JiraAuthError("Invalid credentials")
        mock_jira_cls.return_value = mock_jira

        mock_github = Mock()
        mock_github.test_connection.return_value = {"user": "github_user"}
        mock_github_cls.return_value = mock_github

        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 1
        assert (
            "auth failed" in result.output.lower() or "error" in result.output.lower()
        )

    @patch("src.cli.__main__.GitHubClient")
    @patch("src.cli.__main__.JiraClient")
    def test_status_github_conn_error(self, mock_jira_cls, mock_github_cls, runner):
        """Should show error when GitHub connection fails."""
        mock_jira = Mock()
        mock_jira.test_connection.return_value = {"user": "jira_user"}
        mock_jira_cls.return_value = mock_jira

        mock_github = Mock()
        mock_github.test_connection.side_effect = GitHubConnError("Connection timeout")
        mock_github_cls.return_value = mock_github

        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 1
        assert "error" in result.output.lower() or "connection" in result.output.lower()

    @patch("src.cli.__main__.GitHubClient")
    @patch("src.cli.__main__.JiraClient")
    def test_status_both_failed(self, mock_jira_cls, mock_github_cls, runner):
        """Should show error when both APIs fail."""
        mock_jira = Mock()
        mock_jira.test_connection.side_effect = JiraConnError("Failed")
        mock_jira_cls.return_value = mock_jira

        mock_github = Mock()
        mock_github.test_connection.side_effect = GitHubConnError("Failed")
        mock_github_cls.return_value = mock_github

        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 1


class TestCLIHelp:
    """Tests for CLI help and version."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    def test_cli_no_command(self, runner):
        """Should show help when no command provided."""
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Team Activity Monitor" in result.output

    def test_cli_help(self, runner):
        """Should show help with --help flag."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Team Activity Monitor" in result.output
        assert "query" in result.output
        assert "status" in result.output

    def test_query_help(self, runner):
        """Should show query command help."""
        result = runner.invoke(cli, ["query", "--help"])
        assert result.exit_code == 0
        assert "Query team member activity" in result.output

    def test_status_help(self, runner):
        """Should show status command help."""
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "Check API connection status" in result.output

    def test_interactive_help(self, runner):
        """Should show interactive command help."""
        result = runner.invoke(cli, ["interactive", "--help"])
        assert result.exit_code == 0
        assert "interactive mode" in result.output.lower()


class TestCLIDebugMode:
    """Tests for debug mode."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    def test_debug_flag(self, runner):
        """Should accept --debug flag."""
        result = runner.invoke(cli, ["--debug", "--help"])
        assert result.exit_code == 0


class TestCLIServe:
    """Tests for the serve command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    def test_serve_help(self, runner):
        """Should show serve command help."""
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Flask API server" in result.output or "API server" in result.output

    def test_serve_command_exists(self, runner):
        """Should have serve command available."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "serve" in result.output

    def test_serve_with_custom_port(self, runner):
        """Should accept custom port."""
        result = runner.invoke(cli, ["serve", "--port", "8080", "--help"])
        assert result.exit_code == 0
