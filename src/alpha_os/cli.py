"""Alpha OS CLI — setup, serve, doctor."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from alpha_os import __version__
from alpha_os.bridges.detector import detect_best, detect_hermes, detect_openclaw
from alpha_os.config import CONFIG_DIR, inject_runtime_env, load_config, save_config, set_key

inject_runtime_env()

def _resolve_pkg_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here.parent, here.parent.parent):
        if (candidate / "hermes_plugin").is_dir():
            return candidate
    return here.parent.parent


PKG_ROOT = _resolve_pkg_root()
HERMES_PLUGIN_SRC = PKG_ROOT / "hermes_plugin"
THEME_SRC = PKG_ROOT / "hermes_plugin" / "dashboard" / "alpha-os-cyber.yaml"


def _print(msg: str) -> None:
    print(msg, flush=True)


async def cmd_doctor() -> int:
    _print(f"Alpha OS v{__version__} doctor\n")
    hermes = await detect_hermes()
    openclaw = await detect_openclaw()
    best = await detect_best()

    frontend_ok = (PKG_ROOT / "frontend" / "node_modules").exists()
    install_sh = PKG_ROOT / "scripts" / "install.sh"

    _print(f"  Repo root:      {PKG_ROOT}")
    _print(f"  Install script: {'found' if install_sh.exists() else 'not found (pip-only install)'}")
    _print(f"  Frontend deps:  {'installed' if frontend_ok else 'missing — run ./install.sh'}")
    _print(f"  Hermes home:    {'~/.hermes found' if Path.home().joinpath('.hermes').exists() else 'not found'}")
    _print(f"  Hermes API:     {'LIVE' if hermes.connected else 'offline'} — {hermes.gateway_url}")
    _print(f"  OpenClaw home:  {'~/.openclaw found' if Path.home().joinpath('.openclaw').exists() else 'not found'}")
    _print(f"  OpenClaw GW:    {'LIVE' if openclaw.connected else 'offline'} — {openclaw.ws_url or openclaw.gateway_url}")
    _print(f"  Active runtime: {best.name} ({'connected' if best.connected else 'offline'})")
    _print(f"  Config:         {CONFIG_DIR / 'config.yaml'}")
    if not frontend_ok and install_sh.exists():
        _print("\n  Run: ./install.sh && ./scripts/start.sh")
    return 0 if best.connected else 1


def _install_hermes_plugin() -> bool:
    dest = Path.home() / ".hermes" / "plugins" / "alpha-os"
    if not HERMES_PLUGIN_SRC.exists():
        _print("  Warning: hermes_plugin source not found in package")
        return False
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(HERMES_PLUGIN_SRC, dest)
    _print(f"  Installed Hermes dashboard plugin → {dest}")

    theme_dest = Path.home() / ".hermes" / "dashboard-themes"
    theme_dest.mkdir(parents=True, exist_ok=True)
    if THEME_SRC.exists():
        shutil.copy2(THEME_SRC, theme_dest / "alpha-os-cyber.yaml")
        _print("  Installed cyber theme → ~/.hermes/dashboard-themes/alpha-os-cyber.yaml")

    hermes_cfg = Path.home() / ".hermes" / "config.yaml"
    if shutil.which("hermes"):
        try:
            subprocess.run(
                ["hermes", "plugins", "enable", "alpha-os"],
                check=False,
                capture_output=True,
            )
            _print("  Enabled alpha-os in hermes plugins")
        except Exception:
            _print("  Run manually: hermes plugins enable alpha-os")
    return True


def _install_openclaw_plugin() -> bool:
    oc_plugin = PKG_ROOT / "openclaw_plugin"
    if not oc_plugin.exists():
        _print("  OpenClaw plugin source not bundled yet — use: alpha-os serve")
        return False
    if shutil.which("openclaw"):
        try:
            subprocess.run(
                ["openclaw", "plugins", "install", str(oc_plugin)],
                check=False,
            )
            _print("  Installed OpenClaw plugin")
            return True
        except Exception:
            pass
    _print("  OpenClaw plugin at:", oc_plugin)
    _print("  Run: openclaw plugins install <path-to-openclaw_plugin>")
    return False


async def cmd_setup(args: argparse.Namespace) -> int:
    _print(f"Alpha OS v{__version__} setup\n")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    hermes = await detect_hermes()
    openclaw = await detect_openclaw()
    best = await detect_best()

    cfg: dict = load_config()
    runtime = args.runtime or best.name
    if runtime == "auto":
        runtime = best.name if best.name != "offline" else "hermes"

    cfg["runtime"] = runtime
    cfg.setdefault("server", {})["port"] = args.port
    cfg["server"]["host"] = args.host

    if runtime == "hermes" or hermes.gateway_url:
        cfg.setdefault("hermes", {})
        cfg["hermes"]["gateway_url"] = hermes.gateway_url or "http://127.0.0.1:8642"
        if hermes.api_key:
            cfg["hermes"]["api_key"] = hermes.api_key
        cfg["hermes"]["dashboard_theme"] = "alpha-os-cyber"
        _install_hermes_plugin()

    if runtime == "openclaw" or openclaw.ws_url:
        cfg.setdefault("openclaw", {})
        cfg["openclaw"]["ws_url"] = openclaw.ws_url or "ws://127.0.0.1:18789"
        if openclaw.api_key:
            cfg["openclaw"]["token"] = openclaw.api_key
        _install_openclaw_plugin()

    save_config(cfg)
    _print(f"\n  Runtime:  {runtime}")
    _print(f"  Config:   {CONFIG_DIR / 'config.yaml'}")
    _print("\n  Next steps:")
    if runtime == "hermes":
        _print("    hermes gateway          # start API server if needed")
        _print("    hermes dashboard        # Alpha OS replaces home page")
        _print("    — or —")
    _print(f"    alpha-os serve          # http://{args.host}:{args.port}")
    return 0


def _run_start_script(name: str) -> int:
    start_sh = PKG_ROOT / "scripts" / name
    if not start_sh.exists():
        _print(f"  scripts/{name} not found — are you running from a repo clone?")
        _print("  Clone: git clone https://github.com/Ghost-Network666/Alpha-OS.git")
        _print("  Then:  ./install.sh && ./scripts/start.sh")
        return 1
    if not (PKG_ROOT / "frontend" / "node_modules").exists():
        _print("  Frontend not installed. Run: ./install.sh")
        return 1
    try:
        subprocess.run(["bash", str(start_sh)], cwd=str(PKG_ROOT), check=False)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_start(_args: argparse.Namespace) -> int:
    _print("Starting Alpha OS (dev — hot reload)…")
    return _run_start_script("start.sh")


def cmd_start_prod(_args: argparse.Namespace) -> int:
    _print("Starting Alpha OS (production build)…")
    return _run_start_script("start-prod.sh")


def cmd_serve(args: argparse.Namespace) -> int:
    set_key("server.port", args.port)
    set_key("server.host", args.host)
    if getattr(args, "voice", False):
        set_key("voice.enabled", True)
        _print("  Voice loop enabled (server mic — also use browser mic in dashboard)")
    url = f"http://{args.host}:{args.port}"
    _print(f"Alpha OS → {url}")
    if args.open:
        webbrowser.open(url)
    from alpha_os.server import main as serve_main
    serve_main(host=args.host, port=args.port)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="alpha-os",
        description="Alpha OS — cyber command-center for Hermes & OpenClaw",
    )
    parser.add_argument("--version", action="version", version=f"alpha-os {__version__}")
    sub = parser.add_subparsers(dest="cmd")

    p_setup = sub.add_parser("setup", help="Detect runtime and install plugins")
    p_setup.add_argument("--runtime", choices=["hermes", "openclaw", "auto"], default="auto")
    p_setup.add_argument("--port", type=int, default=8080)
    p_setup.add_argument("--host", default="127.0.0.1")

    p_serve = sub.add_parser("serve", help="Start Alpha OS web server")
    p_serve.add_argument("--port", type=int, default=8080)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--open", action="store_true", help="Open browser")
    p_serve.add_argument(
        "--voice",
        action="store_true",
        help="Enable server-side mic loop (requires pip install alpha-os[voice])",
    )

    sub.add_parser("doctor", help="Check gateway connectivity")

    sub.add_parser("start", help="Start backend + Next.js frontend (dev mode)")

    sub.add_parser("start-prod", help="Start backend + built Next.js frontend (production)")

    args = parser.parse_args()
    if args.cmd == "setup":
        raise SystemExit(asyncio.run(cmd_setup(args)))
    if args.cmd == "doctor":
        raise SystemExit(asyncio.run(cmd_doctor()))
    if args.cmd == "serve":
        raise SystemExit(cmd_serve(args))
    if args.cmd == "start":
        raise SystemExit(cmd_start(args))
    if args.cmd == "start-prod":
        raise SystemExit(cmd_start_prod(args))

    # Default: serve
    raise SystemExit(cmd_serve(argparse.Namespace(port=8080, host="127.0.0.1", open=True, voice=False)))


if __name__ == "__main__":
    main()