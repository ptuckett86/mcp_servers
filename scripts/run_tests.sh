#!/usr/bin/env bash
# Run github and jira test suites with isolated PYTHONPATHs (both use a `client` package).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON=("$ROOT/.venv/bin/python" -m pytest)
else
  PYTHON=(python -m pytest)
fi

echo "==> github tests"
PYTHONPATH="$ROOT/github" "${PYTHON[@]}" "$ROOT/github/tests" -q "$@"

echo "==> jira tests"
PYTHONPATH="$ROOT/jira" "${PYTHON[@]}" "$ROOT/jira/tests" -q "$@"

echo "All tests passed."
