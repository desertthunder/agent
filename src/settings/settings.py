import os

from dotenv import load_dotenv

load_dotenv()

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
