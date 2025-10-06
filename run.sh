curl -H "Authorization: Bearer <gh_token>" \
     -H "Accept: application/vnd.github+json" \
     https://api.github.com/repos/altimetrikjiraaccess-glitch/CodeXPOCRepo/dispatches \
     -d '{"event_type":"codex_generate_tests","client_payload":{"jira_key":"SCRUM-1","mode":"jira"}}'
