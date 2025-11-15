#!/usr/bin/env zsh
set -euo pipefail

# Install project requirements from the repository root regardless of current working dir
REPO_DIR=${0:A:h}/..
cd "$REPO_DIR"

python3 -m pip install -U pip
if [ -f requirements.txt ]; then
  python3 -m pip install -U -r requirements.txt || true
fi
if [ -f requirements-build.txt ]; then
  python3 -m pip install -U -r requirements-build.txt
else
  python3 -m pip install -U pyinstaller
fi

echo "Dependencies installed (requirements.txt and requirements-build.txt if present)."
