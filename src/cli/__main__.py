"""Command-line interface for Team Activity Monitor.

This module provides a Click-based CLI for querying team member activities
from JIRA and GitHub with natural language questions.
"""

import sys

import click
from loguru import logger

from cli.view import (
    console,
    display_activity_response,
    display_error,
    display_status,
    display_suggestion,
    display_welcome,
    print_info,
    print_success,
)
from providers.github import GitHubAuthError, GitHubClient, GitHubConnError
from providers.jira import JiraAuthError, JiraClient, JiraConnError
from providers.openai import ResponseGenerator
from services.data_aggregator import DataAggregator
from services.query_parser import QueryParser


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(ctx, debug):
    """Team Activity Monitor - Query team member activities from JIRA and GitHub.

    Ask natural language questions about what team members are working on.

    Examples:
        team-monitor query "What is John working on?"
        team-monitor interactive
        team-monitor status
    """
    if debug:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="ERROR")

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("question", required=False)
@click.option(
    "--days", "-d", default=7, type=int, help="Number of days to look back (default: 7)"
)
@click.option("--table", "-t", is_flag=True, help="Show detailed tables")
def query(question, days, table):
    """Query team member activity with a natural language question.

    QUESTION: Natural language question about team member activity

    Examples:
        team-monitor query "What is Sarah working on?"
        team-monitor query "Show me John's recent commits" --days 14
    """
    if not question:
        display_error(
            "No question provided", "Please provide a question as an argument."
        )
        display_suggestion('Try: team-monitor query "What is John working on?"')
        sys.exit(1)

    if days < 1 or days > 365:
        display_error("Invalid days value", "Days must be between 1 and 365")
        sys.exit(1)

    try:
        query_parser = QueryParser()
        data_aggregator = DataAggregator()
        response_generator = ResponseGenerator()

        print_info(f"Processing query: {question}")
        parsed = query_parser.parse(question)

        if not parsed["username"]:
            display_error(
                "Could not extract username from query",
                f"Query: {question}\n\nTry asking 'What is [Name] working on?'",
            )
            sys.exit(1)

        print_info(f"Looking up activity for {parsed['username']}...")

        activity_data = data_aggregator.get_user_activity(
            username=parsed["username"],
            query_type=parsed["query_type"],
            days=days,
        )

        ai_response = response_generator.generate_response(activity_data, days=days)

        response = {
            "query": question,
            "parsed": {
                "username": parsed["username"],
                "query_type": parsed["query_type"],
            },
            "activity": activity_data,
            "ai_response": ai_response,
        }

        if table:
            display_activity_response(response)
        else:
            console.print(f"\n[green]{ai_response}[/green]\n")

        print_success("Query completed")

    except (JiraAuthError, GitHubAuthError) as e:
        display_error("Authentication Error", str(e))
        sys.exit(1)
    except (JiraConnError, GitHubConnError) as e:
        display_error("Connection Error", str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        display_error("Unexpected Error", str(e))
        sys.exit(1)


@cli.command()
@click.option(
    "--days", "-d", default=7, type=int, help="Number of days to look back (default: 7)"
)
def interactive(days):
    """Start interactive mode for continuous queries.

    In interactive mode, you can ask multiple questions without restarting the tool.
    Type 'exit' or 'quit' to leave interactive mode.

    Examples:
        team-monitor interactive
        team-monitor interactive --days 14
    """
    display_welcome()
    console.print()
    print_info("Interactive mode - Type 'exit' or 'quit' to leave")
    print_info(f"Looking back {days} days for GitHub activity")
    console.print()

    try:
        query_parser = QueryParser()
        data_aggregator = DataAggregator()
        response_generator = ResponseGenerator()

        while True:
            try:
                question = console.input("[cyan]Ask a question:[/cyan] ")

                if not question or not question.strip():
                    continue

                if question.lower().strip() in ("exit", "quit", "q"):
                    print_info("Exiting interactive mode")
                    break

                parsed = query_parser.parse(question)

                if not parsed["username"]:
                    display_error(
                        "Could not extract username",
                        "Try asking 'What is [Name] working on?'",
                    )
                    console.print()
                    continue

                print_info(f"Looking up {parsed['username']}...")

                activity_data = data_aggregator.get_user_activity(
                    username=parsed["username"],
                    query_type=parsed["query_type"],
                    days=days,
                )

                ai_response = response_generator.generate_response(
                    activity_data, days=days
                )

                response = {
                    "query": question,
                    "parsed": {
                        "username": parsed["username"],
                        "query_type": parsed["query_type"],
                    },
                    "activity": activity_data,
                    "ai_response": ai_response,
                }

                display_activity_response(response)
                console.print()

            except KeyboardInterrupt:
                console.print()
                print_info("Use 'exit' or 'quit' to leave interactive mode")
                console.print()
            except Exception as e:
                logger.exception("Error processing query")
                display_error("Error", str(e))
                console.print()

    except (JiraAuthError, GitHubAuthError) as e:
        display_error("Authentication Error", str(e))
        sys.exit(1)
    except (JiraConnError, GitHubConnError) as e:
        display_error("Connection Error", str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        console.print()
        print_info("Goodbye!")
        sys.exit(0)


@cli.command()
def status():
    """Check API connection status for JIRA and GitHub.

    Tests the connection to both JIRA and GitHub APIs and displays
    the current authentication status.

    Examples:
        team-monitor status
    """
    print_info("Checking API connections...")
    console.print()

    jira_status = "unknown"
    github_status = "unknown"

    try:
        jira_client = JiraClient()
        result = jira_client.test_connection()
        jira_status = f"connected as {result['user']}"
        logger.debug(f"JIRA: {jira_status}")
    except JiraAuthError as e:
        jira_status = f"auth failed: {e!s}"
        logger.error(f"JIRA auth error: {e}")
    except JiraConnError as e:
        jira_status = f"connection failed: {e!s}"
        logger.error(f"JIRA connection error: {e}")
    except Exception as e:
        jira_status = f"error: {e!s}"
        logger.exception("Unexpected JIRA error")

    try:
        github_client = GitHubClient()
        result = github_client.test_connection()
        github_status = f"connected as {result['user']}"
        logger.debug(f"GitHub: {github_status}")
    except GitHubAuthError as e:
        github_status = f"auth failed: {e!s}"
        logger.error(f"GitHub auth error: {e}")
    except GitHubConnError as e:
        github_status = f"connection failed: {e!s}"
        logger.error(f"GitHub connection error: {e}")
    except Exception as e:
        github_status = f"error: {e!s}"
        logger.exception("Unexpected GitHub error")

    display_status(jira_status, github_status)

    if "connected" not in jira_status or "connected" not in github_status:
        sys.exit(1)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
@click.option("--port", "-p", default=5000, type=int, help="Port to bind to (default: 5000)")
@click.option("--no-debug", is_flag=True, help="Disable debug mode")
def serve(host, port, no_debug):
    """Start the Flask API server.

    Starts the Team Activity Monitor API server that provides REST endpoints
    for querying team member activities.

    Examples:
        team-monitor serve
        team-monitor serve --port 8000
        team-monitor serve --host localhost --port 8080
    """
    print_info(f"Starting Team Activity Monitor API on {host}:{port}")

    if not no_debug:
        print_info("Debug mode enabled")

    try:
        from api.app import app

        app.run(debug=not no_debug, host=host, port=port)
    except Exception as e:
        logger.exception("Failed to start server")
        display_error("Server Error", str(e))
        sys.exit(1)


if __name__ == "__main__":
    cli()
