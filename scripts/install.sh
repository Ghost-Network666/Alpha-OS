#!/usr/bin/env bash
# Alpha OS — full install from a repo clone (Python + Next.js frontend)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}▸${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# ── Python 3.10+ ──────────────────────────────────────────────
PY=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
  if command -v "${cmd}" &>/dev/null; then
    ver="$("${cmd}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    major="${ver%%.*}"
    minor="${ver##*.}"
    if [[ "${major}" -eq 3 && "${minor}" -ge 10 ]]; then
      PY="${cmd}"
      break
    fi
  fi
done
[[ -n "${PY}" ]] || fail "Python 3.10+ required. Install from https://python.org"

info "Python: $(${PY} --version)"

# ── Virtualenv ────────────────────────────────────────────────
VENV="${ROOT}/.venv"
if [[ ! -d "${VENV}" ]]; then
  info "Creating virtualenv at .venv"
  "${PY}" -m venv "${VENV}"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
pip install --upgrade pip wheel -q
info "Installing Alpha OS (editable)…"
pip install -e "${ROOT}[voice]" -q
ok "Backend installed"

# ── Node.js 18+ (for Next.js frontend) ───────────────────────
need_node() {
  command -v node &>/dev/null || return 0
  local major
  major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
  [[ "${major}" -ge 18 ]]
}

load_nvm() {
  export NVM_DIR="${HOME}/.nvm"
  if [[ -s "${NVM_DIR}/nvm.sh" ]]; then
    # shellcheck disable=SC1091
    . "${NVM_DIR}/nvm.sh"
    return 0
  fi
  return 1
}

if ! need_node; then
  info "Node.js 18+ not found — installing via nvm…"
  if ! load_nvm; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    load_nvm || fail "nvm install failed"
  fi
  nvm install 22
  nvm use 22
fi

NODE_VER="$(node --version 2>/dev/null || echo missing)"
info "Node: ${NODE_VER}"

# ── Frontend deps ─────────────────────────────────────────────
if [[ -f "${ROOT}/frontend/package.json" ]]; then
  info "Installing frontend dependencies…"
  cd "${ROOT}/frontend"
  npm install --no-fund --no-audit
  if [[ ! -f .env.local ]]; then
    echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8080" > .env.local
    ok "Created frontend/.env.local"
  fi
  ok "Frontend installed"
  cd "${ROOT}"
else
  fail "frontend/ not found — clone the full repo: git clone https://github.com/Ghost-Network666/Alpha-OS.git"
fi

# ── Alpha OS setup ────────────────────────────────────────────
info "Running alpha-os setup…"
alpha-os setup || true

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Alpha OS installed successfully${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "  1. Install Hermes Agent (if you haven't):"
echo "     curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
echo "     hermes setup"
echo ""
echo "  2. Enable API in ~/.hermes/.env:"
echo "     API_SERVER_ENABLED=true"
echo "     API_SERVER_KEY=your-secret-key"
echo ""
echo "  3. Start everything:"
echo "     ./scripts/start.sh"
echo ""
echo "  4. Open http://127.0.0.1:3000"
echo ""
echo "  Other commands:"
echo "     source .venv/bin/activate"
echo "     alpha-os doctor     # check gateway"
echo "     alpha-os serve      # backend only (port 8080)"
echo ""