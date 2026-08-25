#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${1:-$SKILL_DIR/.venv/bin/python}"

PYTHONPATH="$SKILL_DIR/scripts" "$PYTHON_BIN" -B -m unittest discover -s "$SCRIPT_DIR" -p 'test_*.py' -v
