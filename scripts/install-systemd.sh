#!/usr/bin/env bash
# Install Alpha OS user systemd units (backend + frontend)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER_SYSTEMD="${HOME}/.config/systemd/user"
mkdir -p "${USER_SYSTEMD}"

chmod +x "${ROOT}/scripts/run-backend.sh" "${ROOT}/scripts/run-frontend.sh" "${ROOT}/scripts/tailscale-serve.sh"

BACKEND_UNIT="${USER_SYSTEMD}/alpha-os-backend.service"
FRONTEND_UNIT="${USER_SYSTEMD}/alpha-os-frontend.service"

if [[ -f "${USER_SYSTEMD}/hermes-gateway-alpha.service" ]]; then
  HERMES_UNIT=$'After=network-online.target hermes-gateway-alpha.service\nWants=network-online.target hermes-gateway-alpha.service'
else
  HERMES_UNIT=$'After=network-online.target\nWants=network-online.target'
fi

cat > "${BACKEND_UNIT}" <<EOF
[Unit]
Description=Alpha OS API backend
${HERMES_UNIT}

[Service]
Type=simple
WorkingDirectory=${ROOT}
ExecStart=${ROOT}/scripts/run-backend.sh
Restart=on-failure
RestartSec=3
Environment=PATH=${ROOT}/.venv/bin:${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

cat > "${FRONTEND_UNIT}" <<EOF
[Unit]
Description=Alpha OS Next.js frontend
After=network-online.target alpha-os-backend.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${ROOT}/frontend
ExecStart=/bin/bash -lc 'export NVM_DIR="${HOME}/.nvm"; [[ -s "\$NVM_DIR/nvm.sh" ]] && . "\$NVM_DIR/nvm.sh"; exec ${ROOT}/scripts/run-frontend.sh'
Restart=on-failure
RestartSec=3
Environment=NODE_ENV=production
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

# Retire legacy broken unit (wrong WorkingDirectory)
if systemctl --user is-enabled alpha-mission-control.service &>/dev/null; then
  systemctl --user disable alpha-mission-control.service 2>/dev/null || true
fi
if [[ -f "${USER_SYSTEMD}/alpha-mission-control.service" ]]; then
  mv "${USER_SYSTEMD}/alpha-mission-control.service" \
    "${USER_SYSTEMD}/alpha-mission-control.service.disabled" 2>/dev/null || true
fi

TAILSCALE_UNIT="${USER_SYSTEMD}/alpha-os-tailscale.service"
cat > "${TAILSCALE_UNIT}" <<EOF
[Unit]
Description=Alpha OS Tailscale Serve (tailnet HTTPS)
After=network-online.target alpha-os-frontend.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=${ROOT}/scripts/tailscale-serve.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable alpha-os-backend.service alpha-os-frontend.service
if command -v tailscale &>/dev/null; then
  systemctl --user enable alpha-os-tailscale.service
fi
echo "✓ Installed user units:"
echo "    alpha-os-backend.service"
echo "    alpha-os-frontend.service"
if command -v tailscale &>/dev/null; then
  echo "    alpha-os-tailscale.service"
fi
echo ""
echo "  systemctl --user start alpha-os-backend alpha-os-frontend"
echo "  journalctl --user -u alpha-os-backend -f"