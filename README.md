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
