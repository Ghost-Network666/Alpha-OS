#!/usr/bin/env bash
# Start Alpha OS in production mode — built Next.js + uvicorn (no reload)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT}/scripts/lib/runtime-env.sh"
load_runtime_env

BACKEND_HOST="${ALPHA_OS_HOST:-127.0.0.1}"
BACKEND_PORT="${ALPHA_OS_PORT:-8080}"
FRONTEND_HOST="${ALPHA_OS_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${ALPHA_OS_FRONTEND_PORT:-3000}"
WORKERS="${ALPHA_OS_WORKERS:-1}"

if [[ -f "${ROOT}/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.venv/bin/activate"
elif ! python3 -c "import alpha_os" 2>/dev/null; then
  echo "Alpha OS not installed. Run: ./install.sh"
  exit 1
fi

export NVM_DIR="${HOME}/.nvm"
[[ -s "${NVM_DIR}/nvm.sh" ]] && . "${NVM_DIR}/nvm.sh"

if [[ ! -d "${ROOT}/frontend/node_modules" ]]; then
  echo "Frontend not installed. Run: ./install.sh"
  exit 1
fi

if ! command -v node &>/dev/null; then
  echo "Node.js not found. Run: ./install.sh"
  exit 1
fi

echo "▸ Alpha OS (production)"
echo "  Config       → ~/.hermes/.env + ~/.openclaw/.env"
echo "  Backend      → http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "  Frontend     → http://${FRONTEND_HOST}:${FRONTEND_PORT}"
if [[ -n "${ALPHA_OS_API_TOKEN:-}" ]]; then
  echo "  API auth     → enabled (ALPHA_OS_API_TOKEN in ~/.hermes/.env)"
else
  echo "  API auth     → disabled"
fi
echo ""

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
export ALPHA_OS_HOST="${BACKEND_HOST}"
export ALPHA_OS_PORT="${BACKEND_PORT}"
export ALPHA_OS_API_TOKEN="${ALPHA_OS_API_TOKEN:-}"

cleanup() {
  trap - EXIT INT TERM
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "▸ Building frontend…"
cd "${ROOT}/frontend"
npm run build --silent

echo "▸ Starting backend (workers=${WORKERS})…"
cd "${ROOT}"
python3 -m uvicorn alpha_os.server:app \
  --host "${BACKEND_HOST}" \
  --port "${BACKEND_PORT}" \
  --workers "${WORKERS}" &

cd "${ROOT}/frontend"
exec npm run start -- --port "${FRONTEND_PORT}" --hostname "${FRONTEND_HOST}"