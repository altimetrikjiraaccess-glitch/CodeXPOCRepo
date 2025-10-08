export NO_PROXY=localhost,127.0.0.1,.altimetrikjiraaccess.atlassian.net
# Python requests respects these by default
export JIRA_BASE_URL="https://altimetrikjiraaccess.atlassian.net"
export JIRA_EMAIL="altimetrikjiraaccess@gmail.com"
export JIRA_API_TOKEN="ATATT3xFfGF0IxFZXndLW-YYpfvdofTzX-7t4mqpCsJA5Kysaw5eTrJOU5_a2lxFDC8pP0KFagitT5HwNuWzkYaRiEjd44RFgRBt-mxWGyyArw-VxVXd4uLbtIjLNYrUNylCplAkcD83GN-4Lo4ePH2JyU5NWd_-oVi1vwN7MU3k-1wSu-X4tHQ=D0C300D1"
export JIRA_PROJECT_KEY="SCRUM"
export STORY_KEY="SCRUM-1"
export TEST_ISSUE_TYPE="Test"           # or "Test Case" (Zephyr), etc.
export ISSUE_LINK_TYPE="Relates"        # or "Tests", "Blocks", depending on your scheme



python3 create_test_from_story.py
