"""Flask API for team activity monitoring chatbot.

Provides REST endpoints for querying team member activities from JIRA and GitHub.
"""

from flask import Flask, jsonify, request
from loguru import logger

from providers.github import GitHubAuthError, GitHubClient, GitHubConnError
from providers.jira import JiraAuthError, JiraClient, JiraConnError
from providers.openai import ResponseGenerator
from services.data_aggregator import DataAggregator
from services.query_parser import QueryParser

app = Flask(__name__)


query_parser = QueryParser()
data_aggregator = DataAggregator()
response_generator = ResponseGenerator()


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint.

    Returns:
        JSON response with health status
    """
    return jsonify({"status": "healthy", "service": "team-activity-monitor"})


@app.route("/api/status", methods=["GET"])
def connection_status():
    """Check API connections to JIRA and GitHub.

    Returns:
        JSON response with connection status for each service
    """
    status = {"jira": "unknown", "github": "unknown"}

    try:
        jira_client = JiraClient()
        jira_client.test_connection()
        status["jira"] = "connected"
    except (JiraAuthError, JiraConnError) as e:
        status["jira"] = f"error: {e!s}"
        logger.warning(f"JIRA connection check failed: {e}")
    except Exception as e:
        status["jira"] = "error: unexpected error"
        logger.error(f"Unexpected error checking JIRA: {e}")

    try:
        github_client = GitHubClient()
        github_client.test_connection()
        status["github"] = "connected"
    except (GitHubAuthError, GitHubConnError) as e:
        status["github"] = f"error: {e!s}"
        logger.warning(f"GitHub connection check failed: {e}")
    except Exception as e:
        status["github"] = "error: unexpected error"
        logger.error(f"Unexpected error checking GitHub: {e}")

    overall_status = (
        "healthy" if all("connected" in str(v) for v in status.values()) else "degraded"
    )

    return jsonify({"status": overall_status, "services": status})


@app.route("/api/query", methods=["POST"])
def query_activity():
    """Process natural language query about team member activity.

    Request JSON:
        {
            "query": "What is John working on?",
            "days": 7  # optional, defaults to 7
        }

    Returns:
        JSON response with activity data and formatted summary
    """
    if not request.json or "query" not in request.json:
        return (jsonify({"error": "Missing 'query' field in request body"}), 400)

    query_text = request.json["query"]
    days = request.json.get("days", 7)

    if not isinstance(query_text, str) or not query_text.strip():
        return jsonify({"error": "Query must be a non-empty string"}), 400

    if not isinstance(days, int) or days < 1 or days > 365:
        return jsonify({"error": "Days must be an integer between 1 and 365"}), 400

    try:
        logger.info(f"Processing query: {query_text}")
        parsed = query_parser.parse(query_text)

        if not parsed["username"]:
            return (
                jsonify(
                    {
                        "error": "Could not extract username from query",
                        "suggestion": "Try asking 'What is [Name] working on?'",
                        "query": query_text,
                    }
                ),
                400,
            )

        activity_data = data_aggregator.get_user_activity(
            username=parsed["username"], query_type=parsed["query_type"], days=days
        )

        summary = data_aggregator.format_summary(activity_data)
        ai_response = response_generator.generate_response(activity_data, days=days)

        response = {
            "query": query_text,
            "parsed": {
                "username": parsed["username"],
                "query_type": parsed["query_type"],
            },
            "activity": activity_data,
            "summary": summary,
            "ai_response": ai_response,
        }

        logger.info(f"Successfully processed query for {parsed['username']}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return (jsonify({"error": "Internal server error", "message": str(e)}), 500)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors.

    Args:
        error: The error object

    Returns:
        JSON error response
    """
    return (
        jsonify(
            {"error": "Not found", "message": "The requested endpoint does not exist"}
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors.

    Args:
        error: The error object

    Returns:
        JSON error response
    """
    logger.error(f"Internal server error: {error}")
    return (
        jsonify(
            {
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            }
        ),
        500,
    )


if __name__ == "__main__":
    logger.info("Starting Team Activity Monitor API")
    app.run(debug=True, host="0.0.0.0", port=5000)
