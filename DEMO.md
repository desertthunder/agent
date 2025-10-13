---
author: Owais Jamil
date: MMMM dd, YYYY
paging: Slide %d / %d
---

# Team Activity Monitor / Agent

**Author:** Owais Jamil

**Repository:** [desertthunder/agent](https://github.com/desertthunder/agent)

This project presents a prototype AI agent capable of retrieving and synthesizing team activity data from JIRA and GitHub APIs. The system interprets natural language queries (e.g., *“What is John working on?”*) and aggregates related tickets, commits, and pull requests into coherent human-readable summaries.

Developed during a two-day design sprint, this prototype demonstrates rapid API integration, deterministic natural language generation, and robust error handling through a modular CLI + REST architecture with Python technologies.

---

## Use-Case

Engineering managers and team leads often lack a unified view of developer activity across project management and version control systems.

Most analytics dashboards are manual or siloed per platform. This project explores whether a lightweight AI agent can unify these signals into an interpretable daily summary.

**Objective:**
To design a system that automatically answers **“What is [member] working on these days?”** by combining separate data sources in real time.

---

## Methodology

**Approach:**

1. Define query intent schema for natural language inputs
2. Implement modular API providers for JIRA and GitHub
3. Aggregate and normalize cross-source activity data
4. Generate conversational summaries using deterministic templates

**Evaluation Criteria:**

- Functional correctness and data fidelity
- Response clarity and readability
- Fault tolerance under partial API failure
- Development speed and architectural cleanliness

---

## System Architecture Overview

**Tech Stack:**
Python 3.13 · Flask · Click · JIRA & GitHub REST APIs

**Design Principles:**

- Layered architecture with strict separation of concerns
- Deterministic “template-based AI” approach
- Full unit + integration test coverage

---

## Directory Structure

```bash
src/
├── api/
│   └── app.py                # Flask REST API
├── cli/
│   ├── __main__.py           # Click CLI entrypoint
│   └── view.py               # Rich terminal UI
├── providers/
│   ├── github.py             # GitHub integration
│   ├── jira.py               # JIRA integration
│   └── openai.py             # Response generator
└── services/
    ├── query_parser.py       # Natural language query processing
    └── data_aggregator.py    # Data combination and integration logic
```

---

The goal here was to produce a clear separation of concerns:
    - Providers handle APIs
    - Services encapsulate business logic
    - CLI + API expose interfaces

---

## Component Design

1. Provider Pattern
   - Each API has a dedicated client class
   - Consistent authentication and error handling
   - Easily mockable for testing

2. Service Layer
   - `QueryParser`: extracts user intent from free-form text
   - `DataAggregator`: merges GitHub + JIRA datasets
   - `ResponseGenerator`: composes natural-sounding summaries

3. Dependency Injection
   - Configurable dependencies for testing and environment isolation

---

## Testing

```bash
tests/
├── test_api.py
├── test_cli.py
├── test_error_scenarios.py
├── test_github_provider.py
├── test_jira_provider.py
├── test_query_parser.py
├── test_response_generator.py
└── test_data_aggregator.py
```

---

**Coverage:**
135 total tests  ·  100 % pass rate  ·  ~0.35 s runtime

**Validation Focus:**

- Unit isolation of components
- Integration across CLI + API layers
- Controlled fault injection

---

## CLI Query Mode

**Example Query:**

```bash
poetry run python -m cli query "What is John working on?"
```

**Response:**

- Summarized JIRA issues, commits, and pull requests
- Human-readable natural language output
- Graceful handling of missing data

**Advanced Usage:**

```bash
poetry run python -m cli query "Show me Sarah's commits" --days 14
poetry run python -m cli query "What is Mike doing?" --table
```

---

## Demonstration: Interactive Mode

```bash
poetry run python -m cli interactive
```

**Features:**

- Persistent REPL-style interface
- Rich-formatted tables and color output
- Continuous querying without relaunching
- Exit via `quit` or Ctrl + C

---

## Demonstration: REST API Interface

**Start the API server:**

```bash
poetry run python -m cli serve --port 5000
```

**Example query:**

```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is John working on?", "days": 7}'
```

**Output Includes:**

- Parsed query intent
- Aggregated activity data
- AI-style summary
- Metadata and error context

---

## Fault-Tolerance/Error Handling

### User Not Found

```bash
poetry run python -m cli query "What is NonexistentUser doing?"
```

→ “No recent activity found.”

### Invalid Query

```bash
poetry run python -m cli query "What is happening?"
```

→ “Try asking ‘What is [Name] working on?’”

### API Failure

- Continues with available data
- Reports which provider failed
- Produces partial summary

---

## Design Rationale and Challenges

| Challenge                    | Design Decision                                                      |
| ---------------------------- | -------------------------------------------------------------------- |
| **Natural Language Parsing** | Regex-based multi-pattern extraction with fallback heuristics        |
| **Dual API Integration**     | Provider classes with unified interface and shared exceptions        |
| **Error Resilience**         | Try/except per provider · Error aggregation and graceful degradation |
| **Response Generation**      | Template-based NLG → predictable, testable output                    |
| **Speed Constraints**        | Lightweight Flask + Click architecture · No external AI latency      |

---

## Evaluation and Results

**Findings:**

| Metric                 | Result                               |
| ---------------------- | ------------------------------------ |
| Total Tests            | 135 (100 % pass)                     |
| Average CLI Query Time | < 0.2 s                              |
| API Latency            | < 300 ms local                       |
| Coverage               | 100 % branches                       |
| Error Recovery         | 100 % of single-API failures handled |

**Observations:**

- Responses remained readable and contextually relevant
- Error transparency improved user trust
- Modular design simplified debugging

---

## Discussion

**Key Insights:**

- Deterministic templates can approximate AI-like tone while remaining fully interpretable and cost-free.
- Clean separation of providers and services enabled independent parallel development within a 2-day window.
- Full-coverage testing provided measurable confidence in reliability under constrained timelines.

---

## Future Work

1. Caching and Persistence
   - Store previous queries and API responses in SQLite
   - Enable incremental updates and offline access
2. Configuration Management
   - Map JIRA ↔ GitHub usernames
   - Support custom response templates
3. Analytics
   - Trend detection and time-range summaries
   - Team-level dashboards via a web UI
4. Integrations
   - Slack / Teams notifications
   - Confluence and GitLab providers

## References

1. Atlassian Developers. *JIRA REST API Documentation.*
   [https://developer.atlassian.com/server/jira/platform/rest-apis/](https://developer.atlassian.com/server/jira/platform/rest-apis/)
2. GitHub Developers. *REST API v3.*
   [https://docs.github.com/en/rest](https://docs.github.com/en/rest)
3. Pallets Projects. *Flask Documentation.*
   [https://flask.palletsprojects.com](https://flask.palletsprojects.com)
4. Click Documentation. *Command-Line Interface Toolkit.*
   [https://click.palletsprojects.com](https://click.palletsprojects.com)
5. pytest Framework. *Testing and Fixtures.*
   [https://docs.pytest.org](https://docs.pytest.org)

---

## Appendix - Quick Start

```bash
git clone https://github.com/desertthunder/agent
cd agent

pip install poetry
poetry env use python3.13
source .venv/bin/activate
poetry install

poetry run python -m cli query "What is [Name] working on?"
```
