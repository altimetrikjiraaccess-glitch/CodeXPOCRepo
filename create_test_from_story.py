import json
import os
import sys
from dataclasses import dataclass
from typing import Mapping

import requests


AC_FIELD_ID = "customfield_10059"


@dataclass
class JiraConfig:
    base_url: str
    email: str
    token: str
    project_key: str
    story_key: str
    test_type: str
    issue_link_type: str

    @property
    def auth(self):
        return self.email, self.token

    @property
    def headers(self):
        return {"Accept": "application/json", "Content-Type": "application/json"}


def load_config(env: Mapping[str, str] | None = None) -> JiraConfig:
    """Create a :class:`JiraConfig` from environment variables.

    Parameters
    ----------
    env:
        Optional mapping used for tests. Defaults to :data:`os.environ`.
    """

    if env is None:
        env = os.environ

    missing = [key for key in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN") if not env.get(key)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(sorted(missing))}")

    return JiraConfig(
        base_url=env["JIRA_BASE_URL"].rstrip("/"),
        email=env["JIRA_EMAIL"],
        token=env["JIRA_API_TOKEN"],
        project_key=env.get("JIRA_PROJECT_KEY", "SCRUM"),
        story_key=env.get("STORY_KEY", "SCRUM-1"),
        test_type=env.get("TEST_ISSUE_TYPE", "Test"),
        issue_link_type=env.get("ISSUE_LINK_TYPE", "Relates"),
    )

def get_story(config: JiraConfig, key: str):
    url = f"{config.base_url}/rest/api/3/issue/{key}"
    params = {"fields": f"summary,{AC_FIELD_ID}"}
    r = requests.get(url, headers=config.headers, params=params, auth=config.auth)
    r.raise_for_status()
    return r.json()

def ac_to_test_description(story_key: str, story_summary, ac_value):
    """
    Convert AC content to a test description, scoped to ``story_key``.
    Handles either plain text or list/bullets.
    """
    if not ac_value:
        ac_text = "_No Acceptance Criteria found in customfield_10059._"
    elif isinstance(ac_value, list):
        # Many teams store AC as a list of strings
        ac_text = "\n".join(f"- {item}" for item in ac_value if item)
    else:
        # Assume plain text
        ac_text = str(ac_value).strip()

    description = (
        f"*Generated from story:* {story_key} — {story_summary}\n\n"
        f"*Acceptance Criteria:*\n{ac_text}\n\n"
        f"*Suggested Test Steps:*\n"
        f"1. Review AC and define preconditions\n"
        f"2. Execute steps per AC (Given/When/Then)\n"
        f"3. Capture actual result & evidence\n"
        f"4. Mark pass/fail and link defects"
    )
    return description

def create_test_issue(config: JiraConfig, summary: str, description: str):
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
    r = requests.post(url, headers=config.headers, data=json.dumps(payload), auth=config.auth)
    r.raise_for_status()
    return r.json()["key"]

def link_issues(config: JiraConfig, inward_key: str, outward_key: str, link_name: str = "Relates"):
    url = f"{config.base_url}/rest/api/3/issueLink"
    payload = {
        "type": {"name": link_name},
        "inwardIssue": {"key": inward_key},
        "outwardIssue": {"key": outward_key}
    }
    r = requests.post(url, headers=config.headers, data=json.dumps(payload), auth=config.auth)
    r.raise_for_status()

def main():
    config = load_config()

    story = get_story(config, config.story_key)
    story_summary = story["fields"].get("summary", "(no summary)")
    ac_value = story["fields"].get(AC_FIELD_ID)

    desc = ac_to_test_description(config.story_key, story_summary, ac_value)
    test_key = create_test_issue(config, f"Tests for {config.story_key}", desc)
    link_issues(config, test_key, config.story_key, link_name=config.issue_link_type)

    print(f"✅ Created test issue {test_key} and linked to {config.story_key}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
