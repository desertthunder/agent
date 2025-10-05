"""Pytest configuration and fixtures."""

import os

os.environ["JIRA_BASE_URL"] = "https://test.atlassian.net"
os.environ["JIRA_EMAIL"] = "test@example.com"
os.environ["JIRA_API_TOKEN"] = "test_token"
os.environ["GITHUB_TOKEN"] = "test_github_token"
os.environ["OPENAI_API_KEY"] = "test_openai_key"
