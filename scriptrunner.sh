pip install responses

export JIRA_BASE_URL="https://altimetrikjiraaccess.atlassian.net"
export JIRA_EMAIL="altimetrikjiraaccess@gmail.com"
export JIRA_API_TOKEN="Sub_Codex_POC"
export JIRA_PROJECT_KEY="SCRUM"
export STORY_KEY="SCRUM-1"
export TEST_ISSUE_TYPE="Test"           # or "Test Case" (Zephyr), etc.
export ISSUE_LINK_TYPE="Relates"        # or "Tests", "Blocks", depending on your scheme

python3 create_test_from_story.py
