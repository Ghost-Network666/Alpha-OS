#!/usr/bin/env bash
# Alpha OS — one-shot install (Python + Next.js 16 + Hermes/OpenClaw auto-detect)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'
REQUIRED_NEXT="16.2.7"

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

# ── Node.js 20.9+ (Next.js 16) ───────────────────────────────
need_node() {
  command -v node &>/dev/null || return 0
  node -e 'const [m,n]=process.versions.node.split(".").map(Number); process.exit(m>20||(m===20&&n>=9)?0:1)' 2>/dev/null
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
  info "Node.js 20.9+ not found — installing via nvm…"
  if ! load_nvm; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    load_nvm || fail "nvm install failed"
  fi
  if [[ -f "${ROOT}/.nvmrc" ]]; then
    nvm install
    nvm use
  else
    nvm install 22
    nvm use 22
  fi
elif load_nvm && [[ -f "${ROOT}/.nvmrc" ]]; then
  nvm use --silent 2>/dev/null || true
fi

NODE_VER="$(node --version 2>/dev/null || echo missing)"
info "Node: ${NODE_VER}"

[[ -f "${ROOT}/frontend/package.json" ]] || \
  fail "frontend/ not found — clone the full repo: git clone https://github.com/Ghost-Network666/Alpha-OS.git"

# ── Detect Hermes / OpenClaw (before setup) ─────────────────
# Strong auto-detect per requirements:
# - Directory presence
# - Anything connected to .hermes gateway (process or successful reachability hints)
# - Anything connected or been used on a live port for .hermes
HERMES_DETECTED=false
OPENCLAW_DETECTED=false
HERMES_PROFILE="alpha"

if [[ -d "${HOME}/.hermes" && -d "${HOME}/.hermes/profiles" ]]; then
  HERMES_DETECTED=true
fi

# Live process or port detection for Hermes (gateway / API server)
# Supports: anything connected to .hermes gateway OR anything on a live port used by .hermes
if ! $HERMES_DETECTED; then
  if pgrep -f 'hermes' &>/dev/null 2>&1 || pgrep -f 'hermes-agent' &>/dev/null 2>&1; then
    HERMES_DETECTED=true
    info "Hermes process detected (live gateway)"
  fi
fi

# Collect actual ports from Hermes env/config files (any profile) and check if live
if ! $HERMES_DETECTED; then
  HERMES_PORTS=()
  for envf in "${HOME}/.hermes/.env" "${HOME}/.hermes/profiles"/*/.env; do
    [[ -f "$envf" ]] || continue
    while IFS= read -r line || [[ -n "$line" ]]; do
      case "$line" in
        API_SERVER_PORT=*|HERMES_GATEWAY_URL=* )
          p=$(echo "$line" | sed -E 's/.*[:=]([0-9]+).*/\1/' | tr -cd '0-9')
          [[ "$p" =~ ^[0-9]+$ ]] && HERMES_PORTS+=("$p")
          ;;
      esac
    done < "$envf"
  done
  # also common fallbacks
  HERMES_PORTS+=(8642 9999 8080 8081 9000)
  for p in "${HERMES_PORTS[@]}"; do
    if ss -tlnp 2>/dev/null | grep -qE ":${p}[^0-9]"; then
      HERMES_DETECTED=true
      info "Hermes live port ${p} detected from config or common (gateway/API in use)"
      break
    fi
  done
fi

[[ -d "${HOME}/.openclaw" ]] && OPENCLAW_DETECTED=true

if [[ "${HERMES_DETECTED}" == true ]]; then
  if [[ -f "${HOME}/.hermes/active_profile" ]]; then
    HERMES_PROFILE="$(tr -d '[:space:]' < "${HOME}/.hermes/active_profile")"
  fi
  if [[ -d "${HOME}/.hermes/profiles/alpha" ]]; then
    HERMES_PROFILE="alpha"
  elif [[ ! -d "${HOME}/.hermes/profiles/${HERMES_PROFILE}" ]]; then
    for d in "${HOME}/.hermes/profiles"/*; do
      if [[ -d "${d}" && -f "${d}/config.yaml" ]]; then
        HERMES_PROFILE="$(basename "${d}")"
        break
      fi
    done
  fi
fi

RUNTIME="${ALPHA_OS_RUNTIME:-}"
if [[ -z "${RUNTIME}" ]]; then
  RUNTIME="hermes"
  if [[ "${HERMES_DETECTED}" == true && "${OPENCLAW_DETECTED}" == true ]]; then
    if [[ -t 0 ]]; then
      echo ""
      echo -e "${YELLOW}Detected both Hermes and OpenClaw (live usage on ports/processes for .hermes considered).${NC}"
      echo "[1] Hermes (${HERMES_PROFILE} profile)  [2] OpenClaw"
      read -r -p "Choice [1/2] (default 1): " RUNTIME_CHOICE
      case "${RUNTIME_CHOICE:-1}" in
        2) RUNTIME="openclaw" ;;
      esac
    else
      info "Non-interactive: defaulting to Hermes (${HERMES_PROFILE})"
    fi
  elif [[ "${OPENCLAW_DETECTED}" == true ]]; then
    RUNTIME="openclaw"
    info "Auto-selected OpenClaw (~/.openclaw)"
  elif [[ "${HERMES_DETECTED}" == true ]]; then
    RUNTIME="hermes"
    info "Auto-selected Hermes (${HERMES_PROFILE} profile) — live gateway/port detected"
  else
    info "No ~/.hermes or ~/.openclaw — defaulting to Hermes (offline UI)"
  fi
fi

if [[ "${RUNTIME}" == "hermes" ]]; then
  export HERMES_PROFILE="${HERMES_PROFILE}"
  export HERMES_HOME="${HOME}/.hermes/profiles/${HERMES_PROFILE}"
  unset OPENCLAW_HOME 2>/dev/null || true
else
  export OPENCLAW_HOME="${HOME}/.openclaw"
  unset HERMES_PROFILE HERMES_HOME 2>/dev/null || true
fi
export ALPHA_OS_RUNTIME="${RUNTIME}"

info "Runtime: ${RUNTIME}"
if [[ "${RUNTIME}" == "hermes" ]]; then
  info "HERMES_PROFILE=${HERMES_PROFILE}"
  info "HERMES_HOME=${HERMES_HOME}"
else
  info "OPENCLAW_HOME=${OPENCLAW_HOME}"
fi

# Persist runtime before alpha-os setup/configure
python3 - "${RUNTIME}" "${HERMES_PROFILE:-}" "${HERMES_HOME:-}" "${OPENCLAW_HOME:-}" <<'PY'
import sys
from alpha_os.install_config import write_runtime_env
from alpha_os.config import load_config, save_config

runtime, profile, hermes_home, openclaw_home = sys.argv[1:5]
write_runtime_env(
    runtime=runtime,
    hermes_profile=profile or None,
    hermes_home=hermes_home or None,
    openclaw_home_path=openclaw_home or None,
)
cfg = load_config()
cfg["runtime"] = runtime
save_config(cfg)
PY
ok "Runtime env → ~/.alpha-os/runtime.env"

# ── Frontend deps (Next.js 16.2.7 from package.json) ───────────
info "Installing frontend (Next.js ${REQUIRED_NEXT})…"
cd "${ROOT}/frontend"
if [[ -f package-lock.json ]]; then
  npm ci --no-fund --no-audit
else
  npm install --no-fund --no-audit
fi
INSTALLED_NEXT="$(node -p "require('./node_modules/next/package.json').version" 2>/dev/null || echo unknown)"
[[ "${INSTALLED_NEXT}" == "${REQUIRED_NEXT}" ]] || \
  fail "Expected Next.js ${REQUIRED_NEXT}, got ${INSTALLED_NEXT} — check frontend/package.json"
ok "Next.js ${INSTALLED_NEXT}"
cd "${ROOT}"

# ── Alpha OS setup + configure ────────────────────────────────
info "Running alpha-os setup…"
alpha-os setup || true

info "Configuring access URLs…"
if command -v tailscale &>/dev/null && tailscale status &>/dev/null 2>&1; then
  alpha-os configure --quiet
  # shellcheck disable=SC1091
  source "${ROOT}/scripts/_load-ports.sh"
  _alpha_os_load_ports
  ALPHA_OS_PORT="${ALPHA_OS_PORT}" ALPHA_OS_FRONTEND_PORT="${ALPHA_OS_FRONTEND_PORT}" \
    bash "${ROOT}/scripts/tailscale-serve.sh" >/dev/null
else
  alpha-os configure --quiet
fi

python3 <<'PY'
import asyncio
from alpha_os.runtime_sync import sync_runtime_config
asyncio.run(sync_runtime_config(sync_voice=True))
PY
ok "Hermes/OpenClaw settings synced"

# ── Production build ──────────────────────────────────────────
info "Building frontend…"
cd "${ROOT}/frontend"
npm run build
ok "Frontend built"
cd "${ROOT}"

if [[ "${HERMES_DETECTED}" != true && "${OPENCLAW_DETECTED}" != true ]]; then
  echo ""
  echo "  Hermes not detected — install for live gateway data:"
  echo "    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
  echo "    hermes setup && hermes gateway"
  echo ""
fi

# ── Systemd + start ───────────────────────────────────────────
if [[ -f "${ROOT}/scripts/install-systemd.sh" ]]; then
  info "Installing systemd user services…"
  bash "${ROOT}/scripts/install-systemd.sh"
  info "Starting Alpha OS…"
  systemctl --user restart alpha-os-backend.service 2>/dev/null || \
    systemctl --user start alpha-os-backend.service
  systemctl --user restart alpha-os-frontend.service 2>/dev/null || \
    systemctl --user start alpha-os-frontend.service
  sleep 4
else
  info "Starting Alpha OS (dev)…"
  nohup bash "${ROOT}/scripts/start.sh" >> "${ROOT}/alpha-os.log" 2>&1 &
  sleep 3
fi

# ── Verify + ready banner ─────────────────────────────────────
bash "${ROOT}/scripts/verify-setup.sh" || true

# ── Ready banner ──────────────────────────────────────────────
python3 - "${RUNTIME}" "${HERMES_PROFILE:-}" <<'PY'
import sys
from alpha_os.install_config import apply_configuration, print_ready_banner

runtime, profile = sys.argv[1], sys.argv[2] or None
urls = apply_configuration(include_frontend=True)
print_ready_banner(urls, runtime=runtime, hermes_profile=profile)
PY