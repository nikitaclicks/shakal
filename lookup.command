#!/usr/bin/env bash
# Double-click this file in Finder to run gh-to-email.
# It will prompt for a GitHub username and (on first run) a personal access token.
#
# How to make a token (1 minute):
#   1. Open https://github.com/settings/tokens/new
#   2. Note: "gh-to-email"   Expiration: 90 days (or longer)
#   3. No scopes needed for public repos — just click "Generate token"
#   4. Copy the token (starts with ghp_...) and paste it when this script asks

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

CONFIG_DIR="$HOME/.config/gh-to-email"
TOKEN_FILE="$CONFIG_DIR/token"

clear
echo "==========================="
echo "  GitHub email lookup"
echo "==========================="
echo

# Token setup
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  if [[ -f "$TOKEN_FILE" ]]; then
    GITHUB_TOKEN="$(cat "$TOKEN_FILE")"
  else
    echo "First-time setup: need a GitHub personal access token."
    echo
    echo "Open this URL in your browser:"
    echo "   https://github.com/settings/tokens/new"
    echo
    echo "Settings:"
    echo "   Note:        gh-to-email"
    echo "   Expiration:  90 days (or whatever you like)"
    echo "   Scopes:      none needed (just click Generate token)"
    echo
    read -r -p "Paste your token here (ghp_...): " GITHUB_TOKEN
    if [[ -z "$GITHUB_TOKEN" ]]; then
      echo "no token entered, exiting."
      read -r -p "press enter to close..."
      exit 1
    fi
    mkdir -p "$CONFIG_DIR"
    umask 077
    printf '%s' "$GITHUB_TOKEN" > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
    echo "saved to $TOKEN_FILE (you won't be asked again)"
    echo
  fi
fi
export GITHUB_TOKEN

read -r -p "GitHub username or URL: " USER_INPUT
if [[ -z "$USER_INPUT" ]]; then
  echo "no input, exiting."
  read -r -p "press enter to close..."
  exit 1
fi

echo
./gh-to-email "$USER_INPUT" || true
echo
echo "JSON output saved next to this file."
echo
read -r -p "press enter to close..."
