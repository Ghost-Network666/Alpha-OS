#!/usr/bin/env bash
# Local dev — backend only with hot reload
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT}/scripts/lib/runtime-env.sh"
load_runtime_env

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
PORT="${ALPHA_OS_PORT:-8080}"
HOST="${ALPHA_OS_HOST:-127.0.0.1}"
echo "Alpha OS dev server → http://${HOST}:${PORT} (config: ~/.hermes/.env + ~/.openclaw/.env)"
exec python3 -m uvicorn alpha_os.server:app --host "$HOST" --port "$PORT" --reload