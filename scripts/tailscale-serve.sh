#!/usr/bin/env bash
# Alpha OS — private HTTPS via Tailscale Serve (tailnet-wide, mic-safe)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# shellcheck disable=SC1091
source "$(dirname "$0")/_load-ports.sh"
_alpha_os_load_ports
FRONTEND_PORT="${ALPHA_OS_FRONTEND_PORT:-4000}"
BACKEND_PORT="${ALPHA_OS_PORT:-8081}"

if ! command -v tailscale &>/dev/null; then
  echo "Error: tailscale CLI not found. Install: https://tailscale.com/download"
  exit 1
fi

if ! tailscale status &>/dev/null; then
  echo "Error: Tailscale is not connected. Run: sudo tailscale up"
  exit 1
fi

echo "▸ Configuring Tailscale Serve (tailnet only — reachable from any tailnet device)…"
tailscale serve reset
# Default: all HTTP paths → Next.js (proxies /api/* to backend at build/runtime)
tailscale serve --bg "http://127.0.0.1:${FRONTEND_PORT}"
# WebSocket only — Next.js does not proxy /ws/state in production
tailscale serve --bg --set-path=/ws "http://127.0.0.1:${BACKEND_PORT}"

DNS_NAME="$(tailscale status --json 2>/dev/null | python3 -c "
import json, sys
raw = json.load(sys.stdin)
dns = (raw.get('Self') or {}).get('DNSName', '').rstrip('.')
print(dns)
" 2>/dev/null || true)"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Alpha OS — Tailscale HTTPS (any device on your tailnet)"
echo "════════════════════════════════════════════════════════"
echo ""
if [[ -n "${DNS_NAME}" ]]; then
  echo "  https://${DNS_NAME}/"
  echo ""
  echo "  Works from any Wi‑Fi / location — phone, laptop, etc."
  echo "  (Must be signed into Tailscale on that device.)"
  echo ""
  echo "  WS:   wss://${DNS_NAME}/ws/state"
else
  echo "  Run: tailscale serve status"
fi
echo ""
echo "  Tailnet only — not on the public internet."
echo "  For public (no Tailscale client), use: tailscale funnel"
echo ""
tailscale serve status