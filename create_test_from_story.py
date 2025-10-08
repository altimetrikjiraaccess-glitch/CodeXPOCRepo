import os, requests, sys, json, logging

JIRA_BASE    = os.environ["JIRA_BASE_URL"].rstrip("/")   # e.g. https://your-domain.atlassian.net
JIRA_EMAIL   = os.environ["JIRA_EMAIL"]                   # your Atlassian account email
JIRA_TOKEN   = os.environ["JIRA_API_TOKEN"]               # Atlassian API token
PROJECT_KEY  = os.environ.get("JIRA_PROJECT_KEY", "SCRUM")
STORY_KEY    = os.environ.get("STORY_KEY", "SCRUM-1")
TEST_TYPE    = os.environ.get("TEST_ISSUE_TYPE", "Test")  # e.g. "Test", "Test Case", or "Task"

AC_FIELD_ID  = "customfield_10059"

logging.basicConfig(
    level=logging.INFO,                      # DEBUG/INFO/WARNING/ERROR/CRITICAL
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s"
)
log = logging.getLogger(__name__)

masked_token = f"{JIRA_TOKEN[:4]}…" if len(JIRA_TOKEN) > 4 else "***"
log.info(
    "JIRA BASE=%s JIRA Email=%s JIRA Token=%s Project_key=%s Story_Key=%s Test_type=%s",
    JIRA_BASE,
    JIRA_EMAIL,
    masked_token,
    PROJECT_KEY,
    STORY_KEY,
    TEST_TYPE,
)

auth = (JIRA_EMAIL, JIRA_TOKEN)
headers = {"Accept": "application/json", "Content-Type": "application/json"}

def get_story(key):
    url = f"{JIRA_BASE}/rest/api/3/issue/{key}"
    params = {"fields": f"summary,{AC_FIELD_ID}"}
    r = requests.get(url, headers=headers, params=params, auth=auth)
    r.raise_for_status()
    return r.json()

def ac_to_test_description(story_summary, ac_value):
    """
    Convert AC content to a test description.
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
        f"*Generated from story:* {STORY_KEY} — {story_summary}\n\n"
        f"*Acceptance Criteria:*\n{ac_text}\n\n"
        f"*Suggested Test Steps:*\n"
        f"1. Review AC and define preconditions\n"
        f"2. Execute steps per AC (Given/When/Then)\n"
        f"3. Capture actual result & evidence\n"
        f"4. Mark pass/fail and link defects"
    )
    return description

def create_test_issue(summary, description):
    url = f"{JIRA_BASE}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": f"[Auto-Test] {summary}",
            "issuetype": {"name": TEST_TYPE},
            # JIRA Cloud prefers ADF, but plain string still works for most setups:
            "description": description
        }
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), auth=auth)
    r.raise_for_status()
    return r.json()["key"]

def link_issues(inward_key, outward_key, link_name="Relates"):
    url = f"{JIRA_BASE}/rest/api/3/issueLink"
    payload = {
        "type": {"name": link_name},
        "inwardIssue": {"key": inward_key},
        "outwardIssue": {"key": outward_key}
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), auth=auth)
    r.raise_for_status()

def main():
    story = get_story(STORY_KEY)
    story_summary = story["fields"].get("summary", "(no summary)")
    ac_value = story["fields"].get(AC_FIELD_ID)

    desc = ac_to_test_description(story_summary, ac_value)
    test_key = create_test_issue(f"Tests for {STORY_KEY}", desc)
    link_issues(test_key, STORY_KEY, link_name=os.environ.get("ISSUE_LINK_TYPE", "Relates"))

    print(f"✅ Created test issue {test_key} and linked to {STORY_KEY}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
