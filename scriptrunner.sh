export JIRA_BASE_URL="https://<your-domain>.atlassian.net"
export JIRA_EMAIL="you@company.com"
export JIRA_API_TOKEN="<token>"
export JIRA_PROJECT_KEY="SCRUM"
export STORY_KEY="SCRUM-1"
export TEST_ISSUE_TYPE="Test"           # or "Test Case" (Zephyr), etc.
export ISSUE_LINK_TYPE="Relates"        # or "Tests", "Blocks", depending on your scheme

python3 create_test_from_story.py
