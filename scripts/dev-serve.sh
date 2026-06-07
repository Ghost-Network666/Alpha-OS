#!/usr/bin/env bash
# Local dev — no venv required if deps are installed globally
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
PORT="${ALPHA_OS_PORT:-8080}"
HOST="${ALPHA_OS_HOST:-127.0.0.1}"
echo "Alpha OS dev server → http://${HOST}:${PORT}"
exec python3 -m uvicorn alpha_os.server:app --host "$HOST" --port "$PORT" --reload