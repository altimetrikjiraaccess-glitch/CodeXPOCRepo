# CodeXPOCRepo

CodeX POC repository Creation

## Offline test generation

You can execute the Jira test generation utility without network access by
providing an exported issue payload:

```bash
python codex_jira_test_gen.py --jira-key DEMO-1 --issue-json sample_issue.json --mode repo
```

The `sample_issue.json` file in this repository illustrates the expected
structure and will generate Markdown and Gherkin artifacts under
`tests/generated/DEMO-1/`.
