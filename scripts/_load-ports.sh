#!/usr/bin/env bash
# Source ports/hosts from ~/.alpha-os/config.yaml (no alpha-os CLI — avoids log noise/hangs).
_alpha_os_load_ports() {
  local cfg="${HOME}/.alpha-os/config.yaml"
  if [[ ! -f "${cfg}" ]]; then
    export ALPHA_OS_HOST="${ALPHA_OS_HOST:-127.0.0.1}"
    export ALPHA_OS_PORT="${ALPHA_OS_PORT:-9000}"
    export ALPHA_OS_FRONTEND_PORT="${ALPHA_OS_FRONTEND_PORT:-4000}"
    return 0
  fi
  eval "$(python3 - "${cfg}" <<'PY'
import sys
from pathlib import Path
import yaml
path = Path(sys.argv[1])
data = yaml.safe_load(path.read_text()) or {}
server = data.get("server") or {}
frontend = data.get("frontend") or {}
host = server.get("host") or "127.0.0.1"
port = server.get("port") or 9000
fe = frontend.get("port") or 4000
print(f'export ALPHA_OS_HOST="{host}"')
print(f'export ALPHA_OS_PORT="{port}"')
print(f'export ALPHA_OS_FRONTEND_PORT="{fe}"')
PY
)"
}