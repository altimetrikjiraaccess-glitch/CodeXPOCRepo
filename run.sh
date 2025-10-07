#!/usr/bin/env bash
set -euo pipefail

# load env vars if available
if [ -f "envvariable.sh" ]; then
  # shellcheck disable=SC1091
  source envvariable.sh
fi

# compile
javac JiraACToTestsNoDeps.java
# run
java JiraACToTestsNoDeps
