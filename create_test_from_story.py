import json
import logging
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class JiraConfig:
    base_url: str
    email: str
    token: str
    project_key: str
    story_key: str
    test_type: str
    issue_link_type: str
    ac_field_id: str = "customfield_10059"


def load_config() -> JiraConfig:
    """Load and validate required configuration from environment variables."""

    required_env_vars = {
        "JIRA_BASE_URL": os.getenv("JIRA_BASE_URL"),
        "JIRA_EMAIL": os.getenv("JIRA_EMAIL"),
        "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN"),
    }

    missing = [name for name, value in required_env_vars.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(sorted(missing))
        )

    base_url = required_env_vars["JIRA_BASE_URL"].rstrip("/")
    email = required_env_vars["JIRA_EMAIL"]
    token = required_env_vars["JIRA_API_TOKEN"]

    project_key = os.getenv("JIRA_PROJECT_KEY", "SCRUM")
    story_key = os.getenv("STORY_KEY", "SCRUM-1")
    test_type = os.getenv("TEST_ISSUE_TYPE", "Test")
    issue_link_type = os.getenv("ISSUE_LINK_TYPE", "Relates")

    return JiraConfig(
        base_url=base_url,
        email=email,
        token=token,
        project_key=project_key,
        story_key=story_key,
        test_type=test_type,
        issue_link_type=issue_link_type,
    )

def get_story(config: JiraConfig) -> dict[str, Any]:
    url = f"{config.base_url}/rest/api/3/issue/{config.story_key}"
    params = {"fields": f"summary,{config.ac_field_id}"}
    response = requests.get(
        url,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=params,
        auth=(config.email, config.token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def ac_to_test_description(config: JiraConfig, story_summary: str, ac_value: Any) -> str:
    """
    Convert AC content to a test description.
    Handles either plain text or list/bullets.
    """
    if not ac_value:
        ac_text = f"_No Acceptance Criteria found in {config.ac_field_id}._"
    elif isinstance(ac_value, Iterable) and not isinstance(ac_value, (str, bytes)):
        # Many teams store AC as a list of strings
        ac_text = "\n".join(f"- {item}" for item in ac_value if item)
    else:
        # Assume plain text
        ac_text = str(ac_value).strip()

    description = (
        f"*Generated from story:* {config.story_key} — {story_summary}\n\n"
        f"*Acceptance Criteria:*\n{ac_text}\n\n"
        f"*Suggested Test Steps:*\n"
        f"1. Review AC and define preconditions\n"
        f"2. Execute steps per AC (Given/When/Then)\n"
        f"3. Capture actual result & evidence\n"
        f"4. Mark pass/fail and link defects"
    )
    return description

def create_test_issue(config: JiraConfig, summary: str, description: str) -> str:
    url = f"{config.base_url}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": config.project_key},
            "summary": f"[Auto-Test] {summary}",
            "issuetype": {"name": config.test_type},
            # JIRA Cloud prefers ADF, but plain string still works for most setups:
            "description": description
        }
    }
    response = requests.post(
        url,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        data=json.dumps(payload),
        auth=(config.email, config.token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["key"]

def link_issues(config: JiraConfig, inward_key: str, outward_key: str) -> None:
    url = f"{config.base_url}/rest/api/3/issueLink"
    payload = {
        "type": {"name": config.issue_link_type},
        "inwardIssue": {"key": inward_key},
        "outwardIssue": {"key": outward_key}
    }
    response = requests.post(
        url,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        data=json.dumps(payload),
        auth=(config.email, config.token),
        timeout=30,
    )
    response.raise_for_status()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s",
    )
    log = logging.getLogger(__name__)

    config = load_config()
    masked_token = f"{config.token[:4]}…" if len(config.token) > 4 else "***"
    log.info(
        "JIRA BASE=%s JIRA Email=%s JIRA Token=%s Project_key=%s Story_Key=%s Test_type=%s",
        config.base_url,
        config.email,
        masked_token,
        config.project_key,
        config.story_key,
        config.test_type,
    )

    story = get_story(config)
    fields = story.get("fields", {})
    story_summary = fields.get("summary", "(no summary)")
    ac_value = fields.get(config.ac_field_id)

    desc = ac_to_test_description(config, story_summary, ac_value)
    test_key = create_test_issue(config, f"Tests for {config.story_key}", desc)
    link_issues(config, test_key, config.story_key)

    print(f"✅ Created test issue {test_key} and linked to {config.story_key}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
