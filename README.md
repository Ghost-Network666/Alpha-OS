# Alpha OS

Voice-first cyber command-center — the default web UI for [Hermes Agent](https://hermes-agent.nousresearch.com/) and [OpenClaw](https://openclaw.ai/).

**Public repo:** https://github.com/Ghost-Network666/Alpha-OS

## What it does

- Connects to your Hermes gateway — **blank until `~/.hermes` is installed and live**
- Discovers agents, toolsets, skills, and sessions dynamically at runtime
- No hardcoded agents, no demo data, no stale mock panels
- Modular bridges — Hermes REST, OpenClaw WebSocket, stdio MCP (from runtime configs), Tailscale

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

Then start (production — recommended):

```bash
./scripts/install-systemd.sh
systemctl --user start alpha-os-backend alpha-os-frontend alpha-os-tailscale
```

Open **http://127.0.0.1:4000** (frontend) — API runs on **http://127.0.0.1:8081** (or the next free port if 8080 is taken).

Dev mode:

```bash
./scripts/start.sh
```

**Remote access (any device on your Tailscale tailnet):**

```bash
./scripts/tailscale-serve.sh
# → https://<your-machine>.ts.net/
```

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
| `./scripts/start.sh` | Dev mode — backend reload + Next.js dev server |
| `./scripts/start-prod.sh` | Production — `next build` + `next start`, uvicorn workers |
| `alpha-os start` | Same as `start.sh` (repo clone only) |
| `alpha-os start-prod` | Same as `start-prod.sh` |
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

Alpha OS has **no project `.env` files**. It injects from the same dotenv files your runtime uses:

| Runtime | Env file | JSON config |
|---------|----------|-------------|
| **Hermes** | `~/.hermes/.env` | `~/.hermes/config.yaml` |
| **OpenClaw** | `~/.openclaw/.env` | `~/.openclaw/openclaw.json` |

UI preferences also live in `~/.alpha-os/config.yaml`. When both runtimes are installed, the **active runtime** (Hermes or OpenClaw) owns `ALPHA_OS_*` keys.

**Hermes users** — `~/.hermes/.env`:

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=your-secret-key
ALPHA_OS_PORT=8080
ALPHA_OS_FRONTEND_PORT=3000
ALPHA_OS_API_TOKEN=
```

**OpenClaw users** — `~/.openclaw/.env`:

```bash
OPENCLAW_GATEWAY_TOKEN=your-gateway-token
ALPHA_OS_PORT=8080
ALPHA_OS_FRONTEND_PORT=3000
ALPHA_OS_API_TOKEN=
```

| Variable | Hermes source | OpenClaw source | Default |
|----------|---------------|-----------------|---------|
| `API_SERVER_KEY` | `~/.hermes/.env` | — | — |
| `OPENCLAW_GATEWAY_TOKEN` | — | `~/.openclaw/.env` or `openclaw.json` | — |
| `ALPHA_OS_PORT` | active runtime `.env` | active runtime `.env` | `8080` |
| `ALPHA_OS_API_TOKEN` | active runtime `.env` | active runtime `.env` | disabled |

The Next.js UI proxies `/api/*` to the backend using shell-inherited env — no `frontend/.env.local` needed.

## MCP (stdio from your runtime)

Alpha OS does **not** maintain its own MCP registry. It reads the same server definitions Hermes Agent and OpenClaw already use, then probes **stdio** subprocess servers so you can see tools before or while the gateway is live.

| Runtime | Config file | Key |
|---------|-------------|-----|
| Hermes | `~/.hermes/config.yaml` | `mcp_servers` |
| OpenClaw | `~/.openclaw/openclaw.json` | `mcp.servers` |

**Stdio example (Hermes):**

```yaml
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    env:
      SOME_TOKEN: "from-your-env"
```

**Stdio example (OpenClaw):**

```json
{
  "mcp": {
    "servers": {
      "docs": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"]
      }
    }
  }
}
```

- **Stdio servers** — Alpha OS launches the same `command` + `args` (+ `env`) and lists discovered tools in the MCP panel.
- **Remote HTTP/SSE servers** (`url` in config) — listed for visibility; Hermes/OpenClaw own OAuth/TLS and tool execution.
- After editing MCP config: Hermes `/reload-mcp` or restart OpenClaw gateway; click **Probe** in the Alpha OS MCP panel.

Install the MCP client library for stdio probing:

```bash
pip install -e ".[mcp]"
# or full install: ./install.sh  (includes voice + mcp extras)
```

---

## Architecture

```
frontend/             # Next.js 15 App Router (primary UI)
src/alpha_os/
├── bridges/          # Hermes REST + OpenClaw WebSocket
├── core/             # Alpha butler + SQLite memory
├── integrations/     # stdio MCP discovery/probe + Tailscale
└── server.py         # FastAPI + WebSocket state push

hermes_plugin/        # Hermes dashboard home override
openclaw_plugin/      # openclaw alpha CLI command
scripts/
├── install.sh        # Full repo install
└── start.sh          # Run backend + frontend
```

---

## Production

```bash
# Add ALPHA_OS_* keys to ~/.hermes/.env or ~/.openclaw/.env (see Configuration)
./scripts/start-prod.sh
```

- Binds to `127.0.0.1` by default — override via `~/.hermes/.env`.
- Set `ALPHA_OS_API_TOKEN` in `~/.hermes/.env` to enable API auth; the Next.js proxy injects it server-side.
- Health: `GET /health` and `GET /ready` (always public).

## Development

```bash
git clone https://github.com/Ghost-Network666/Alpha-OS.git
cd Alpha-OS
./install.sh
./scripts/start.sh
```

### Tests

```bash
# Backend (60+ unit tests)
pip install -e ".[test,mcp]"
pytest

# Frontend unit tests
cd frontend && npm test
```

Backend only with hot reload:

```bash
source .venv/bin/activate
./scripts/dev-serve.sh
```

---

## License

MIT — see [LICENSE](LICENSE).