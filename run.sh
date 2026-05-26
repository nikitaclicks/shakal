#!/usr/bin/env bash
# Wrapper around gh_to_email.py — adds pre-flight checks and friendly errors.
#
# Usage:  ./run.sh <username-or-url> [extra flags forwarded to the script]
# Example: ./run.sh octocat
#          ./run.sh https://github.com/octocat --verbose
#          ./run.sh torvalds --max-pages-per-repo 2

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/gh_to_email.py"

usage() {
  cat <<'USAGE'
usage: ./run.sh <username-or-url> [flags]

flags forwarded to gh_to_email.py:
  --max-pages-per-repo N   cap pagination per repo (default 20)
  --skip-events            don't scan recent events
  --out PATH               output JSON path (default <user>-emails.json)
  --verbose                log every API request
USAGE
}

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 not found in PATH" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI not found. install from https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth token >/dev/null 2>&1; then
  echo "error: not logged in to gh. run: gh auth login" >&2
  exit 1
fi

if [[ ! -f "$PY_SCRIPT" ]]; then
  echo "error: $PY_SCRIPT not found" >&2
  exit 1
fi

exec python3 "$PY_SCRIPT" "$@"
