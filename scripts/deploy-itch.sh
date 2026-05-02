#!/usr/bin/env bash
# Build the web bundle and push it to itch.io via butler.
#
# Prereqs (one-time):
#   - butler installed: `brew install butler` (or download from https://itch.io/app)
#   - BUTLER_API_KEY exported in your shell (e.g. ~/.zshrc):
#       export BUTLER_API_KEY=...   # from https://itch.io/user/settings/api-keys
#   - itch.io project page already created (web UI; butler can't create projects)
#
# Usage:
#   scripts/deploy-itch.sh v0.1.1
#
# Optional env overrides:
#   ITCH_PROJECT (default: fableworks/tank-2d)
#   ITCH_CHANNEL (default: html5)
#   PYTHON       (default: .venv/bin/python)

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    echo "usage: $0 <version>   e.g. $0 v0.1.1" >&2
    exit 2
fi

if [[ -z "${BUTLER_API_KEY:-}" ]]; then
    echo "error: BUTLER_API_KEY is not set." >&2
    echo "       add 'export BUTLER_API_KEY=...' to your shell rc and reload." >&2
    exit 2
fi

if ! command -v butler >/dev/null 2>&1; then
    echo "error: butler not on PATH. install via 'brew install butler'." >&2
    exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-.venv/bin/python}"
PROJECT="${ITCH_PROJECT:-fableworks/tank-2d}"
CHANNEL="${ITCH_CHANNEL:-html5}"

if [[ ! -x "$PYTHON" ]]; then
    echo "error: python not found at $PYTHON. set PYTHON=... or activate the env." >&2
    exit 2
fi

echo ">>> building web bundle"
rm -rf build
"$PYTHON" -m pygbag --build --width 1024 --height 640 --title "Tank Game" main.py

echo ">>> pushing to ${PROJECT}:${CHANNEL} as ${VERSION}"
butler push "build/web" "${PROJECT}:${CHANNEL}" --userversion "$VERSION"

echo ">>> recent builds:"
butler status "$PROJECT"
