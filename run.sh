#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Error: GITHUB_TOKEN environment variable is not set." >&2
  echo "Please export GITHUB_TOKEN before running this script." >&2
  exit 1
fi

curl -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/altimetrikjiraaccess-glitch/CodeXPOCRepo/dispatches
