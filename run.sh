

set -euo pipefail

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is not set. Please export a GitHub token before running this script." >&2
  exit 1
fi

curl -X POST \
 -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
   https://api.github.com/repos/altimetrikjiraaccess-glitch/CodeXPOCRepo/dispatches
