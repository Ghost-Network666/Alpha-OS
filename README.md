# Alpha OS

Voice-first cyber command-center — the default web UI for [Hermes Agent](https://hermes-agent.nousresearch.com/) and [OpenClaw](https://openclaw.ai/).

**Public repo:** https://github.com/Ghost-Network666/Alpha-OS

## What it does

- Auto-detects your Hermes or OpenClaw installation
- Shows live agents, toolsets, skills, and sessions — nothing hardcoded
- Graceful offline mode — panels stay empty until real data arrives
- Modular bridges — swap, extend, or overhaul any layer independently

## Quick install

```bash
pip install alpha-os
alpha-os setup
alpha-os serve
```

Or one-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/Ghost-Network666/Alpha-OS/main/install.sh | bash
```

## Hermes users

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes setup
pip install alpha-os
alpha-os setup
hermes gateway
hermes dashboard    # Alpha OS replaces the home page
```

Enable API server in `~/.hermes/.env`:

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=your-secret-key
```

## OpenClaw users

```bash
npm i -g openclaw@latest
openclaw onboard --install-daemon
pip install alpha-os
alpha-os setup
openclaw plugins install ./path/to/alpha-os/openclaw_plugin
alpha-os serve        # or: openclaw alpha
```

## Commands

| Command | Description |
|---------|-------------|
| `alpha-os` | Start server and open browser |
| `alpha-os serve` | Start on http://127.0.0.1:8080 |
| `alpha-os setup` | Detect runtime, install plugins, write config |
| `alpha-os doctor` | Check gateway connectivity |

## Configuration

Stored in `~/.alpha-os/config.yaml`. Override with env vars:

| Variable | Default |
|----------|---------|
| `HERMES_GATEWAY_URL` | `http://127.0.0.1:8642` |
| `HERMES_API_KEY` | from `~/.hermes/.env` |
| `OPENCLAW_GATEWAY_URL` | `ws://127.0.0.1:18789` |
| `OPENCLAW_GATEWAY_TOKEN` | from `~/.openclaw/openclaw.json` |

## Architecture

```
src/alpha_os/
├── bridges/          # Hermes REST + OpenClaw WebSocket adapters
├── core/             # Alpha butler + SQLite memory
├── integrations/     # Tailscale panel
├── dashboard/        # Single-file cyber UI
└── server.py         # FastAPI + WebSocket state push

hermes_plugin/        # Overrides hermes dashboard home page
openclaw_plugin/      # openclaw alpha CLI command
```

Every layer is independently replaceable — fork a bridge, reskin the UI, or add panels without touching the rest.

## Development

```bash
git clone https://github.com/Ghost-Network666/Alpha-OS.git
cd Alpha-OS
pip install -e ".[voice]"
alpha-os serve --open
```

## License

MIT — see [LICENSE](LICENSE).