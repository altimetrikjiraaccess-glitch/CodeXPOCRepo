#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  # Load environment variables from local .env file without exporting secrets to the repo.
  set -a
  source .env
  set +a
fi

: "${JIRA_BASE_URL:?Set JIRA_BASE_URL in the environment or .env file}"
: "${JIRA_EMAIL:?Set JIRA_EMAIL in the environment or .env file}"
: "${JIRA_API_TOKEN:?Set JIRA_API_TOKEN in the environment or .env file}"
: "${JIRA_PROJECT_KEY:?Set JIRA_PROJECT_KEY in the environment or .env file}"
: "${STORY_KEY:?Set STORY_KEY in the environment or .env file}"
: "${TEST_ISSUE_TYPE:?Set TEST_ISSUE_TYPE in the environment or .env file}"
: "${ISSUE_LINK_TYPE:?Set ISSUE_LINK_TYPE in the environment or .env file}"

python3 create_test_from_story.py "$@"
