#!/usr/bin/env bash
# Alpha OS — one-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Ghost-Network666/Alpha-OS/main/install.sh | bash
set -euo pipefail

echo "▸ Installing Alpha OS…"
if command -v pip3 &>/dev/null; then
  pip3 install --user "git+https://github.com/Ghost-Network666/Alpha-OS.git" || pip3 install --user alpha-os
elif command -v pip &>/dev/null; then
  pip install --user "git+https://github.com/Ghost-Network666/Alpha-OS.git" || pip install --user alpha-os
else
  echo "Error: pip not found. Install Python 3.10+ first."
  exit 1
fi

echo "▸ Running setup…"
alpha-os setup || true

echo ""
echo "  Alpha OS installed."
echo "  Run:  alpha-os serve"
echo "  Hermes users:  hermes dashboard  (after hermes plugins enable alpha-os)"
echo "  OpenClaw users:  openclaw alpha  (after plugin install)"
echo ""