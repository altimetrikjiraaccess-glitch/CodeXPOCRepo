curl -H "Authorization: Bearer <gh_token>" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/repos/<ORG>/<REPO>/dispatches \
     -d '{"event_type":"codex_generate_tests","client_payload":{"jira_key":"SCRUM-1","mode":"both"}}'
