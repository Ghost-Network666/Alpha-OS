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

# ── Detect existing runtimes ──────────────────────────────────
HERMES_HOME="${HOME}/.hermes"
OPENCLAW_HOME="${HOME}/.openclaw"
HAS_HERMES=0
HAS_OPENCLAW=0
[[ -d "${HERMES_HOME}" ]] && HAS_HERMES=1 && ok "Found ~/.hermes (Hermes Agent)"
[[ -d "${OPENCLAW_HOME}" ]] && HAS_OPENCLAW=1 && ok "Found ~/.openclaw (OpenClaw)"
if [[ "${HAS_HERMES}" -eq 0 && "${HAS_OPENCLAW}" -eq 0 ]]; then
  info "No ~/.hermes or ~/.openclaw yet — pick a runtime in the Alpha OS connect screen"
fi

# ── Alpha OS setup ────────────────────────────────────────────
info "Running alpha-os setup…"
alpha-os setup || true

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Alpha OS installed successfully${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
if [[ "${HAS_HERMES}" -eq 1 ]]; then
  echo "  Hermes detected at ~/.hermes"
  echo "    • Enable API: API_SERVER_ENABLED=true in ~/.hermes/.env"
  echo "    • Start gateway: hermes gateway"
else
  echo "  Install Hermes (option A):"
  echo "    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
  echo "    hermes setup"
fi
echo ""
if [[ "${HAS_OPENCLAW}" -eq 1 ]]; then
  echo "  OpenClaw detected at ~/.openclaw"
  echo "    • Start gateway: openclaw gateway run"
else
  echo "  Install OpenClaw (option B):"
  echo "    curl -fsSL https://openclaw.ai/install.sh | bash"
  echo "    openclaw onboard --install-daemon"
fi
echo ""
echo "  Start Alpha OS:"
echo "    ./scripts/start.sh"
echo "    Open http://127.0.0.1:3000 — choose Hermes or OpenClaw on the connect screen"
echo ""
echo "  Other commands:"
echo "     source .venv/bin/activate"
echo "     alpha-os doctor     # check gateways"
echo "     alpha-os serve      # backend only (port 8080)"
echo ""