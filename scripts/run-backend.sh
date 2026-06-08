#!/usr/bin/env bash
# Alpha OS backend — used by systemd and manual production start
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

RUNTIME_ENV="${HOME}/.alpha-os/runtime.env"
if [[ -f "${RUNTIME_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${RUNTIME_ENV}"
fi

if [[ -f "${ROOT}/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.venv/bin/activate"
else
  echo "Alpha OS venv missing. Run: ./scripts/install.sh" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$(dirname "$0")/_load-ports.sh"
_alpha_os_load_ports
BACKEND_PORT="${ALPHA_OS_PORT:-9000}"
BACKEND_HOST="${ALPHA_OS_HOST:-127.0.0.1}"

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
export ALPHA_OS_LOG="${ALPHA_OS_LOG:-${ROOT}/alpha-os.log}"

# When wired to Hermes, wait briefly for the API server to come up first.
if [[ "${ALPHA_OS_RUNTIME:-}" == "hermes" && -n "${HERMES_HOME:-}" ]]; then
  gw="http://127.0.0.1:9999"
  if [[ -f "${HERMES_HOME}/.env" ]]; then
    # shellcheck disable=SC1090
    source "${HERMES_HOME}/.env"
    gw="${HERMES_GATEWAY_URL:-http://${API_SERVER_HOST:-127.0.0.1}:${API_SERVER_PORT:-9999}}"
  fi
  for _ in $(seq 1 30); do
    if curl -sf "${gw}/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

exec python3 -m uvicorn alpha_os.server:app \
  --host "${BACKEND_HOST}" \
  --port "${BACKEND_PORT}"