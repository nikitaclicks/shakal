#!/usr/bin/env bash
# Build a standalone macOS .app bundle plus a CLI binary.
#
# Outputs (under dist/):
#   gh-to-email.app             — double-clickable macOS app with dialog UI
#   gh-to-email                 — bare CLI binary (for terminal users)
#   <version-folder>/           — assembled release folder
#   <version-folder>.zip        — release artifact ready to upload to GitHub

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="$(awk -F'"' '/^__version__/ {print $2; exit}' gh_to_email.py)"
if [[ -z "$VERSION" ]]; then
  echo "could not parse __version__ from gh_to_email.py" >&2
  exit 1
fi
ARCH="$(uname -m)"
OS="macos"
RELEASE_NAME="gh-to-email-${VERSION}-${OS}-${ARCH}"

echo "version: $VERSION  target: $OS-$ARCH"

if [[ ! -d .venv ]]; then
  echo "creating venv..."
  python3 -m venv .venv
fi

echo "installing pyinstaller..."
PIP_USER=0 .venv/bin/pip install --quiet --upgrade pip pyinstaller

echo "building CLI binary..."
rm -rf build dist gh-to-email.spec
.venv/bin/pyinstaller --onefile --name gh-to-email --console gh_to_email.py

echo "compiling .app bundle..."
osacompile -o dist/gh-to-email.app app.applescript
cp dist/gh-to-email dist/gh-to-email.app/Contents/Resources/gh-to-email
chmod +x dist/gh-to-email.app/Contents/Resources/gh-to-email

echo "ad-hoc signing .app bundle..."
codesign --force --deep --sign - dist/gh-to-email.app 2>&1 | sed 's/^/  /'

echo "assembling release folder..."
REL="dist/$RELEASE_NAME"
rm -rf "$REL"
mkdir -p "$REL"
cp -R dist/gh-to-email.app "$REL/"
cp dist/gh-to-email "$REL/"
cp release-readme.txt "$REL/README.txt"

echo "zipping release..."
(cd dist && zip -qr "${RELEASE_NAME}.zip" "$RELEASE_NAME")

echo "cleaning intermediate build artifacts..."
rm -rf build gh-to-email.spec

echo
echo "built:"
ls -lh "dist/${RELEASE_NAME}.zip"
echo "  contents:"
unzip -l "dist/${RELEASE_NAME}.zip" | sed 's/^/    /'
