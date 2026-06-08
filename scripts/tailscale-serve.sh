#!/usr/bin/env bash
# Alpha OS — private HTTPS via Tailscale Serve (tailnet only, mic-safe)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_PORT="${ALPHA_OS_FRONTEND_PORT:-4000}"
BACKEND_PORT="${ALPHA_OS_PORT:-9000}"

if ! command -v tailscale &>/dev/null; then
  echo "Error: tailscale CLI not found. Install: https://tailscale.com/download"
  exit 1
fi

if ! tailscale status &>/dev/null; then
  echo "Error: Tailscale is not connected. Run: sudo tailscale up"
  exit 1
fi

echo "▸ Configuring Tailscale Serve (tailnet only — not public)…"
tailscale serve reset
tailscale serve --bg "http://127.0.0.1:${FRONTEND_PORT}"
tailscale serve --bg --set-path=/api "http://127.0.0.1:${BACKEND_PORT}"
tailscale serve --bg --set-path=/ws "http://127.0.0.1:${BACKEND_PORT}"

DNS_NAME="$(tailscale status --json 2>/dev/null | python3 -c "
import json, sys
raw = json.load(sys.stdin)
dns = (raw.get('Self') or {}).get('DNSName', '').rstrip('.')
print(dns)
" 2>/dev/null || true)"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Alpha OS — private Tailscale HTTPS (mic enabled)"
echo "════════════════════════════════════════════════════════"
echo ""
if [[ -n "${DNS_NAME}" ]]; then
  echo "  https://${DNS_NAME}/"
  echo ""
  echo "  API:  https://${DNS_NAME}/api"
  echo "  WS:   wss://${DNS_NAME}/ws/state"
else
  echo "  Run: tailscale serve status"
fi
echo ""
echo "  Tailnet only — not exposed to the public internet."
echo "  Do NOT use tailscale funnel unless you intend public access."
echo ""
tailscale serve status