#!/usr/bin/env bash
# Start Alpha OS — backend API + Next.js frontend
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BACKEND_PORT="${ALPHA_OS_PORT:-8080}"
FRONTEND_PORT="${ALPHA_OS_FRONTEND_PORT:-3000}"

# Python: prefer repo venv
if [[ -f "${ROOT}/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.venv/bin/activate"
elif ! python3 -c "import alpha_os" 2>/dev/null; then
  echo "Alpha OS not installed. Run: ./install.sh"
  exit 1
fi

# Node: load nvm if needed
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

echo "▸ Alpha OS"
echo "  Backend  → http://127.0.0.1:${BACKEND_PORT}"
echo "  Frontend → http://127.0.0.1:${FRONTEND_PORT}"
echo ""

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
export NEXT_PUBLIC_API_URL="http://127.0.0.1:${BACKEND_PORT}"

cleanup() {
  trap - EXIT INT TERM
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python3 -m uvicorn alpha_os.server:app \
  --host 127.0.0.1 \
  --port "${BACKEND_PORT}" \
  --reload &

cd "${ROOT}/frontend"
exec npm run dev -- --port "${FRONTEND_PORT}" --hostname 127.0.0.1