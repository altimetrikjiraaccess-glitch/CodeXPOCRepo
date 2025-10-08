CodeXPOCRepo
============

Proof-of-concept utilities for automating Jira test creation.

## Usage

1. Copy the example environment file and populate it with your Jira details:

   ```bash
   cp .env.example .env
   # edit .env with your Jira base URL, email, API token, etc.
   ```

2. Run the helper script to execute `create_test_from_story.py` with the configured environment:

   ```bash
   ./scriptrunner.sh
   ```

The script will refuse to run unless all required environment variables are provided, helping prevent accidental commits of real credentials.
