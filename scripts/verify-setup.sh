#!/usr/bin/env bash
# Quick health check after install (run from repo root)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; FAIL=1; }

FAIL=0

# shellcheck disable=SC1091
source "${ROOT}/scripts/_load-ports.sh"
_alpha_os_load_ports
BE="${ALPHA_OS_PORT:-9000}"
FE="${ALPHA_OS_FRONTEND_PORT:-4000}"

[[ -d "${ROOT}/.venv" ]] && ok "Python venv" || fail "Python venv missing — run ./install.sh"
[[ -d "${ROOT}/frontend/node_modules" ]] && ok "Frontend deps" || fail "Frontend deps missing"
NEXT="$(node -p "require('${ROOT}/frontend/node_modules/next/package.json').version" 2>/dev/null || echo ?)"
[[ "${NEXT}" == "16.2.7" ]] && ok "Next.js ${NEXT}" || fail "Next.js 16.2.7 expected, got ${NEXT}"
[[ -d "${ROOT}/frontend/.next" ]] && ok "Frontend build" || fail "Frontend not built — run ./install.sh"
[[ -f "${HOME}/.alpha-os/runtime.env" ]] && ok "Runtime env" || fail "~/.alpha-os/runtime.env missing"

systemctl --user is-active alpha-os-backend.service &>/dev/null && ok "Backend service" || fail "alpha-os-backend not running"
systemctl --user is-active alpha-os-frontend.service &>/dev/null && ok "Frontend service" || fail "alpha-os-frontend not running"

curl -sf "http://127.0.0.1:${BE}/health" >/dev/null && ok "Backend /health (:${BE})" || fail "Backend not responding on :${BE}"
curl -sf "http://127.0.0.1:${FE}/" >/dev/null && ok "Frontend UI (:${FE})" || fail "Frontend not responding on :${FE}"

if curl -sf -X POST "http://127.0.0.1:${BE}/api/reconnect" >/dev/null 2>&1; then
  HERMES_OK="$(curl -sf "http://127.0.0.1:${BE}/api/hermes/status" | python3 -c "import sys,json; print(json.load(sys.stdin).get('connected',False))" 2>/dev/null || echo False)"
  [[ "${HERMES_OK}" == "True" ]] && ok "Hermes bridge live" || fail "Hermes bridge offline — is hermes-gateway-alpha running?"
fi

if [[ "${FAIL}" -eq 0 ]]; then
  echo ""
  ok "Alpha OS setup OK"
  echo "  UI:  http://127.0.0.1:${FE}/"
  echo "  API: http://127.0.0.1:${BE}/"
  exit 0
fi
echo ""
fail "Setup incomplete — run: cd ${ROOT} && ./install.sh"
exit 1