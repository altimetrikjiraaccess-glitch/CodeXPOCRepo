# CodeXPOCRepo
CodeX POC repository Creation 
## Triggering the workflow dispatch

The `run.sh` script triggers the GitHub repository dispatch hook used by the
project. To avoid committing long-lived personal access tokens, the script now
expects a token to be provided via the `GITHUB_TOKEN` environment variable.

```bash
export GITHUB_TOKEN="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"
./run.sh
```
