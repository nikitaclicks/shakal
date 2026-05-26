#!/usr/bin/env bash
# Build a standalone single-file binary (no Python install required to run).
# Output: dist/gh-to-email
#
# Run this once on the same OS+arch you want to ship to (a macOS arm64 build
# only runs on macOS arm64). For Intel macs, run this on an Intel mac.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d .venv ]]; then
  echo "creating venv..."
  python3 -m venv .venv
fi

echo "installing pyinstaller..."
PIP_USER=0 .venv/bin/pip install --quiet --upgrade pip pyinstaller

echo "building..."
rm -rf build dist gh-to-email.spec
.venv/bin/pyinstaller --onefile --name gh-to-email --console gh_to_email.py

echo "copying lookup.command into dist/..."
cp lookup.command dist/lookup.command
chmod +x dist/lookup.command

echo "cleaning intermediate build artifacts..."
rm -rf build gh-to-email.spec

echo
echo "built dist/:"
ls -lh dist/
file dist/gh-to-email
