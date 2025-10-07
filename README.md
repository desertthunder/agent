# Team Activity Monitor

An AI-powered chatbot that integrates with JIRA and GitHub APIs to answer questions about team member activities.

## Overview

This project command-line tool and REST API that allows you to query team member activities across JIRA and GitHub using natural language questions.
It combines data from both platforms and presents it in a conversational, easy-to-understand format.

## Features

- Natural language query processing
- JIRA integration (issues, status, updates)
- GitHub integration (commits, pull requests)
- AI-style response generation using templates
- Interactive CLI mode
- REST API server made with flask
- rich terminal output with tables and colors
- Comprehensive error handling
- Full test coverage (135 tests, 100% passing) with pytest

## Tech Stack

**Backend:**

- Flask - REST API framework
- Python 3.13+ - Core language

**Integrations:**

- JIRA REST API - Issue tracking
- GitHub REST API - Code activity

**CLI:**

- Click - Command-line interface framework
- Rich - Terminal formatting and tables

**Code Quality:**

- Pytest - Testing framework
- Ruff - Code linter and formatter
- Loguru - Logging

## Installation

### Prerequisites

- Python 3.13 or higher
- Poetry (Python package manager)
- JIRA account with API access
- GitHub account with personal access token

### Setup

Clone the repository

```bash
git clone https://github.com/desertthunder/agent
cd agent
```

Setup poetry & virtual environment

```bash
pip install poetry
poetry env use python3.13
source .venv/bin/activate
```

Install dependencies

```sh
poetry install
```

Configure environment variables:

Create a `.env` file in the project root (`cp .env.example .env`)

```sh
# JIRA Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your_jira_api_token

# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token
```

## Usage

### CLI Commands

The CLI provides multiple ways to interact with the system:

#### Single Query

Ask a one-time question about team member activity:

```bash
poetry run python -m cli query "What is John working on?"
```

With options:

```bash
# Look back 14 days instead of default 7
poetry run python -m cli query "Show me Sarah's commits" --days 14

# Show detailed tables with structured data
poetry run python -m cli query "What has Mike been working on?" --table
```

#### 2. Interactive Mode

Start an interactive session for multiple queries:

```bash
poetry run python -m cli interactive
```

In interactive mode:

- Ask multiple questions without restarting
- Type `exit` or `quit` to leave
- Press Ctrl+C to see exit instructions

Example session:

```text
Ask a question: What is John working on?
[Response with John's activity...]

Ask a question: Show me Sarah's pull requests
[Response with Sarah's PRs...]

Ask a question: exit
```

#### 3. Check API Status

Verify your JIRA and GitHub connections:

```bash
poetry run python -m cli status
```

This will show connection status for both services and identify any authentication issues.

#### 4. Start API Server

Run the Flask API server:

```bash
poetry run python -m cli serve
```

Options:

```bash
# Custom port
poetry run python -m cli serve --port 8080

# Custom host
poetry run python -m cli serve --host localhost --port 8080

# Production mode (disable debug)
poetry run python -m cli serve --no-debug
```

### REST API Endpoints

Once the server is running, you can use these endpoints:

#### Health Check

```bash
curl http://localhost:5000/api/health
```

#### Connection Status

```bash
curl http://localhost:5000/api/status
```

#### Query Activity

```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is John working on?",
    "days": 7
  }'
```

Response format:

```json
{
  "query": "What is John working on?",
  "parsed": {
    "username": "John",
    "query_type": "all"
  },
  "activity": {
    "username": "John",
    "jira_issues": "[...]",
    "github_commits": "[...]",
    "github_prs": "[...]",
    "has_activity": true,
    "errors": []
  },
  "summary": "Activity summary for John...",
  "ai_response": "Here's what I found about John's recent activity..."
}
```

## Example Queries

The system understands various natural language questions:

**General Activity:**

- "What is John working on?"
- "Show me Sarah's recent activity"
- "What has Mike been working on this week?"

**JIRA Specific:**

- "What JIRA tickets is John working on?"
- "Show me Sarah's current issues"
- "What tickets does Mike have?"

**GitHub Specific:**

- "What has Mike committed this week?"
- "Show me Lisa's recent pull requests"
- "What repositories has John contributed to?"

## Project Structure

```sh
autonomize/
├── src/
│   ├── api/
│   │   └── app.py              # Flask REST API
│   ├── cli/
│   │   ├── __main__.py         # CLI commands
│   │   └── view.py             # Rich display components
│   ├── providers/
│   │   ├── github.py           # GitHub API client
│   │   ├── jira.py             # JIRA API client
│   │   ├── openai.py           # Response generator (template-based)
│   │   └── exceptions.py       # Custom exceptions
│   ├── services/
│   │   ├── data_aggregator.py  # Combines JIRA + GitHub data
│   │   └── query_parser.py     # Parses natural language queries
│   └── settings/
│       └── settings.py         # Configuration management
├── tests/
│   ├── test_api.py             # API endpoint tests
│   ├── test_cli.py             # CLI command tests
│   ├── test_error_scenarios.py # Error handling tests
│   ├── test_*.py               # Component tests
│   └── conftest.py             # Test fixtures
├── SPEC.md                     # Project specification
├── DEMO.md                     # Demo presentation
└── README.md                   # This file
```

## Development

### Running Tests

Run all tests:

```bash
poetry run pytest
```

Run with verbose output:

```bash
poetry run pytest -v
```

Run specific test file:

```bash
poetry run pytest tests/test_cli.py
```

### Code Quality

Format code with Ruff:

```bash
poetry run ruff check --fix
```

## Error Handling

The system gracefully handles various error scenarios:

- **User not found:** Returns helpful message indicating no activity found
- **No recent activity:** Informs user that the person has been inactive
- **API connection errors:** Shows which service failed and why
- **Authentication errors:** Provides clear guidance on credential issues
- **Invalid queries:** Suggests proper query format
- **Partial data:** Works with available data from one service if the other fails

## Architecture

### Data Flow

1. **Query Input** → User asks a natural language question
2. **Query Parsing** → Extracts username and query type
3. **Data Fetching** → Retrieves data from JIRA and GitHub in parallel
4. **Data Aggregation** → Combines and structures the data
5. **Response Generation** → Creates natural language response
6. **Output** → Displays formatted response with tables (CLI) or JSON (API)

### Key Components

**QueryParser:** Extracts username and determines query intent from natural language

**DataAggregator:** Fetches data from both APIs and combines them into unified structure

**ResponseGenerator:** Creates conversational responses using contextual templates

**API Clients:** Handle authentication and communication with JIRA/GitHub

## Troubleshooting

### Authentication Issues

**JIRA "Invalid credentials" error:**

- Verify `JIRA_EMAIL` matches your Atlassian account email
- Ensure `JIRA_API_TOKEN` is copied correctly (no extra spaces)
- Check `JIRA_BASE_URL` format: `https://your-domain.atlassian.net`

**GitHub "Invalid token" error:**

- Regenerate token at <https://github.com/settings/tokens>
- Ensure token has `repo` and `read:user` scopes
- Verify token is copied correctly to `.env`

### Connection Issues

**"Connection timeout" errors:**

- Check your internet connection
- Verify firewall isn't blocking requests
- Ensure API URLs are correct

### Query Not Working

**"Could not extract username" error:**

- Include a name in your query: "What is [Name] working on?"
- Try variations: "Show me [Name]'s activity"
- Names are case-insensitive

## License

This project was created as part of a technical assessment.
