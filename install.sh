#!/usr/bin/env bash
# Alpha OS installer
#
# From repo clone (recommended — includes Next.js UI):
#   git clone https://github.com/Ghost-Network666/Alpha-OS.git
#   cd Alpha-OS
#   ./install.sh
#
# Remote one-liner (backend only — for full UI, clone the repo):
#   curl -fsSL https://raw.githubusercontent.com/Ghost-Network666/Alpha-OS/main/install.sh | bash
set -euo pipefail

# Resolve script directory (works when executed, not only when piped)
if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
  SCRIPT_DIR="$(pwd)"
fi

# Full repo clone → run scripts/install.sh
if [[ -f "${SCRIPT_DIR}/scripts/install.sh" && -f "${SCRIPT_DIR}/frontend/package.json" ]]; then
  exec bash "${SCRIPT_DIR}/scripts/install.sh"
fi

# Remote / partial install → pip only
echo "▸ Installing Alpha OS (backend package)…"
PY=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
  if command -v "${cmd}" &>/dev/null; then
    ver="$("${cmd}" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo 0)"
    if [[ "$("${cmd}" -c 'import sys; print(sys.version_info.major)' 2>/dev/null)" -eq 3 && "${ver}" -ge 10 ]]; then
      PY="${cmd}"
      break
    fi
  fi
done
if [[ -z "${PY}" ]]; then
  echo "Error: Python 3.10+ required."
  exit 1
fi

pip_install() {
  if command -v pip3 &>/dev/null; then
    pip3 "$@"
  elif command -v pip &>/dev/null; then
    pip "$@"
  else
    "${PY}" -m pip "$@"
  fi
}

pip_install install --user --upgrade pip -q
pip_install install --user "git+https://github.com/Ghost-Network666/Alpha-OS.git" \
  || pip_install install --user alpha-os

echo "▸ Running setup…"
alpha-os setup || true

echo "▸ Configuring access URLs…"
alpha-os configure --no-frontend

echo ""
echo "  For the full Next.js UI, clone the repo:"
echo "    git clone https://github.com/Ghost-Network666/Alpha-OS.git"
echo "    cd Alpha-OS && ./install.sh"
echo ""