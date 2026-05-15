#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RADON_BIN="$(command -v radon || true)"
XENON_BIN="$(command -v xenon || true)"

if [[ -z "$RADON_BIN" && -x "$ROOT_DIR/.venv/bin/radon" ]]; then
  RADON_BIN="$ROOT_DIR/.venv/bin/radon"
fi

if [[ -z "$XENON_BIN" && -x "$ROOT_DIR/.venv/bin/xenon" ]]; then
  XENON_BIN="$ROOT_DIR/.venv/bin/xenon"
fi

if [[ -z "$RADON_BIN" ]]; then
  echo "radon is not installed. Run: pip install -r requirements-optional.txt"
  exit 1
fi

if [[ -z "$XENON_BIN" ]]; then
  echo "xenon is not installed. Run: pip install -r requirements-optional.txt"
  exit 1
fi

echo "== Radon cyclomatic complexity report (backend/services, backend/routers, backend/llm) =="
"$RADON_BIN" cc backend/services backend/routers backend/llm -s -a

echo
# Baseline thresholds for phase-1 guardrails:
# - Max block grade: E
# - Max module average: C
# - Max overall average: C
# These are intentionally permissive to establish a first gate in a legacy codebase.
echo "== Xenon baseline thresholds (max-absolute E, max-modules C, max-average C) =="
"$XENON_BIN" --max-absolute E --max-modules C --max-average C backend/services backend/routers backend/llm

echo
echo "Complexity checks completed."
