#!/usr/bin/env bash
# Alpha OS frontend (Next.js production) — used by systemd
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export NVM_DIR="${HOME}/.nvm"
if [[ -s "${NVM_DIR}/nvm.sh" ]]; then
  # shellcheck disable=SC1091
  . "${NVM_DIR}/nvm.sh"
fi

if ! command -v node &>/dev/null; then
  echo "Node.js not found. Run: ./scripts/install.sh" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$(dirname "$0")/_load-ports.sh"
_alpha_os_load_ports
FRONTEND_PORT="${ALPHA_OS_FRONTEND_PORT:-4000}"
BACKEND_PORT="${ALPHA_OS_PORT:-8081}"
BACKEND_HOST="${ALPHA_OS_HOST:-127.0.0.1}"
export INTERNAL_API_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
export NEXT_PUBLIC_API_PORT="${BACKEND_PORT}"
export ALPHA_OS_PORT="${BACKEND_PORT}"
export ALPHA_OS_HOST="${BACKEND_HOST}"

if [[ ! -d "${ROOT}/frontend/.next" ]]; then
  echo "Frontend not built. Run: cd frontend && npm run build" >&2
  exit 1
fi

cd "${ROOT}/frontend"
export PORT="${FRONTEND_PORT}"
export HOSTNAME="${ALPHA_OS_FRONTEND_HOST:-127.0.0.1}"
exec npm run start -- --port "${FRONTEND_PORT}" --hostname "${HOSTNAME}"