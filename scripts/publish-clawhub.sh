#!/usr/bin/env bash
# Publish OpenClaw plugin to ClawHub (requires clawhub CLI + auth)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}/openclaw_plugin"

if ! command -v clawhub &>/dev/null; then
  echo "Install ClawHub CLI first: npm i -g @openclaw/clawhub"
  exit 1
fi

echo "▸ Dry-run package validation…"
clawhub package publish ghostnetwork/alpha-os --dry-run

echo "▸ Publish (remove --dry-run when ready)…"
echo "  clawhub package publish ghostnetwork/alpha-os"