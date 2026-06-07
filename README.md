# Alpha OS

Voice-first cyber command-center — the default web UI for [Hermes Agent](https://hermes-agent.nousresearch.com/) and [OpenClaw](https://openclaw.ai/).

**Public repo:** https://github.com/Ghost-Network666/Alpha-OS

## What it does

- Connects to your Hermes gateway — **blank until `~/.hermes` is installed and live**
- Discovers agents, toolsets, skills, and sessions dynamically at runtime
- No hardcoded agents, no demo data, no stale mock panels
- Modular bridges — Hermes REST, OpenClaw WebSocket, MCP, Tailscale

---

## Install from repo (recommended)

Anyone can clone and run with two commands:

```bash
git clone https://github.com/Ghost-Network666/Alpha-OS.git
cd Alpha-OS
./install.sh
```

This installs:
- Python 3.10+ virtualenv (`.venv`)
- Alpha OS backend (`pip install -e .`)
- Next.js 15 frontend (`frontend/`, npm install)
- Node.js via nvm if not already present

Then start:

```bash
./scripts/start.sh
```

Open **http://127.0.0.1:3000** (frontend) — API runs on **http://127.0.0.1:8080**.

Or use the CLI:

```bash
source .venv/bin/activate
alpha-os start
```

---

## Connect Hermes (required for live data)

Alpha OS stays empty until Hermes is installed and the gateway is running.

```bash
# 1. Install Hermes Agent
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes setup

# 2. Enable API server in ~/.hermes/.env
API_SERVER_ENABLED=true
API_SERVER_KEY=your-secret-key

# 3. Start gateway
hermes gateway

# 4. In another terminal — start Alpha OS
cd Alpha-OS
./scripts/start.sh
```

Optional — embed in Hermes dashboard:

```bash
alpha-os setup
hermes plugins enable alpha-os
hermes dashboard
```

---

## Quick install (backend only)

For backend without cloning the full repo:

```bash
curl -fsSL https://raw.githubusercontent.com/Ghost-Network666/Alpha-OS/main/install.sh | bash
alpha-os serve    # legacy UI at http://127.0.0.1:8080
```

For the **full Next.js UI**, clone the repo and run `./install.sh`.

Or via pip:

```bash
pip install alpha-os
alpha-os setup
alpha-os serve
```

---

## Commands

| Command | Description |
|---------|-------------|
| `./install.sh` | Full install from repo clone (Python + frontend) |
| `./scripts/start.sh` | Start backend + Next.js frontend |
| `alpha-os start` | Same as `start.sh` (repo clone only) |
| `alpha-os serve` | Backend only on http://127.0.0.1:8080 |
| `alpha-os setup` | Detect runtime, install plugins, write config |
| `alpha-os doctor` | Check gateway + install health |

---

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.10+ |
| Node.js | 18+ (installed automatically by `./install.sh` via nvm) |
| Hermes Agent | For live gateway data |

---

## Configuration

Stored in `~/.alpha-os/config.yaml`. Override with env vars:

| Variable | Default |
|----------|---------|
| `HERMES_GATEWAY_URL` | `http://127.0.0.1:8642` |
| `HERMES_API_KEY` | from `~/.hermes/.env` |
| `OPENCLAW_GATEWAY_URL` | `ws://127.0.0.1:18789` |
| `OPENCLAW_GATEWAY_TOKEN` | from `~/.openclaw/openclaw.json` |
| `ALPHA_OS_PORT` | `8080` |
| `ALPHA_OS_FRONTEND_PORT` | `3000` |

MCP servers: configure stdio servers in `~/.hermes/config.yaml` (`mcp_servers`) or `~/.openclaw/openclaw.json` (`mcp.servers`). Alpha OS probes the same stdio connections Hermes/OpenClaw use.

---

## Architecture

```
frontend/             # Next.js 15 App Router (primary UI)
src/alpha_os/
├── bridges/          # Hermes REST + OpenClaw WebSocket
├── core/             # Alpha butler + SQLite memory
├── integrations/     # MCP + Tailscale
└── server.py         # FastAPI + WebSocket state push

hermes_plugin/        # Hermes dashboard home override
openclaw_plugin/      # openclaw alpha CLI command
scripts/
├── install.sh        # Full repo install
└── start.sh          # Run backend + frontend
```

---

## Development

```bash
git clone https://github.com/Ghost-Network666/Alpha-OS.git
cd Alpha-OS
./install.sh
./scripts/start.sh
```

Backend only with hot reload:

```bash
source .venv/bin/activate
./scripts/dev-serve.sh
```

---

## License

MIT — see [LICENSE](LICENSE).