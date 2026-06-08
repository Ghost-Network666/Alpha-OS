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
from alpha_os.logging_config import setup_logging
from alpha_os.config import CONFIG_DIR, load_config, save_config, set_key
from alpha_os.install_config import (
    apply_configuration,
    configure_tailscale_serve,
    export_shell_env,
    has_frontend,
    print_access_banner,
)

def _resolve_pkg_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here.parent, here.parent.parent):
        if (candidate / "hermes_plugin").is_dir():
            return candidate
    return here.parent.parent


PKG_ROOT = _resolve_pkg_root()
setup_logging(pkg_root=PKG_ROOT)
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


def cmd_configure(args: argparse.Namespace) -> int:
    include_frontend = has_frontend(PKG_ROOT) and not getattr(args, "no_frontend", False)
    urls = apply_configuration(
        host=args.host,
        backend_port=args.port,
        frontend_port=args.frontend_port,
        include_frontend=include_frontend,
        pkg_root=PKG_ROOT,
    )
    if getattr(args, "export", False):
        _print(export_shell_env(urls, pkg_root=PKG_ROOT))
        return 0
    if getattr(args, "tailscale_serve", False):
        https_url = configure_tailscale_serve(
            frontend_port=urls.get("frontend_port"),
            backend_port=urls.get("backend_port"),
            pkg_root=PKG_ROOT,
        )
        if https_url:
            urls["tailscale_https_url"] = https_url
            urls["access_url"] = https_url
            from alpha_os.install_config import write_frontend_env

            write_frontend_env(
                PKG_ROOT,
                urls["backend_url"],
                urls["backend_port"],
                https_url,
            )
    if not getattr(args, "quiet", False):
        print_access_banner(urls, include_frontend=include_frontend)
    return 0


async def cmd_setup(args: argparse.Namespace) -> int:
    _print(f"Alpha OS v{__version__} setup\n")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    from alpha_os.runtime_sync import sync_runtime_config

    synced = await sync_runtime_config(sync_voice=False)
    hermes = await detect_hermes()
    openclaw = await detect_openclaw()
    best = await detect_best()
    _print(f"  Hermes home:    {'~/.hermes' if Path.home().joinpath('.hermes').exists() else 'not found'}")
    if synced.get("hermes_profile"):
        _print(f"  Hermes profile: {synced['hermes_profile']}")
    if synced.get("hermes_gateway_url"):
        _print(f"  Hermes API:     {synced['hermes_gateway_url']} ({'live' if synced.get('hermes_connected') else 'offline'})")
    if synced.get("openclaw_ws_url"):
        _print(f"  OpenClaw GW:    {synced['openclaw_ws_url']} ({'live' if synced.get('openclaw_connected') else 'offline'})")

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

    if hermes.gateway_url or runtime == "hermes":
        try:
            from alpha_os.voice.hermes_sync import (
                ensure_hermes_alpha_os_block,
                load_voice_config,
                sync_voice_to_alpha_os,
            )

            ensure_hermes_alpha_os_block()
            voice = sync_voice_to_alpha_os()
            _print(f"  Hermes profile: {voice.get('hermes_profile', 'default')}")
            _print(f"  Hermes config:  {voice.get('hermes_config_path', '')}")
            if voice.get("model_provider"):
                _print(f"  Model:          {voice.get('model_default')} ({voice['model_provider']})")
            _print(
                f"  Voice/TTS:      {voice.get('tts_provider')} / {voice.get('tts_voice')}"
                + (" (SuperGrok)" if voice.get("tts_provider") == "xai" else "")
            )
            _print(f"  STT:            {voice.get('stt_provider')} / {voice.get('stt_model')}")
        except Exception as exc:
            _print(f"  Voice sync:     skipped ({exc})")

    _print(f"\n  Runtime:  {runtime}")
    _print(f"  Config:   {CONFIG_DIR / 'config.yaml'}")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    start_sh = PKG_ROOT / "scripts" / "start.sh"
    if not start_sh.exists():
        _print("  scripts/start.sh not found — are you running from a repo clone?")
        _print("  Clone: git clone https://github.com/Ghost-Network666/Alpha-OS.git")
        _print("  Then:  ./install.sh && ./scripts/start.sh")
        return 1
    if not (PKG_ROOT / "frontend" / "node_modules").exists():
        _print("  Frontend not installed. Run: ./install.sh")
        return 1
    _print("Starting Alpha OS (backend + frontend)…")
    try:
        subprocess.run(["bash", str(start_sh)], cwd=str(PKG_ROOT), check=False)
    except KeyboardInterrupt:
        pass
    return 0


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

    p_configure = sub.add_parser("configure", help="Write config and print access URL")
    p_configure.add_argument("--port", type=int, default=None)
    p_configure.add_argument("--frontend-port", type=int, default=None)
    p_configure.add_argument("--host", default=None)
    p_configure.add_argument("--no-frontend", action="store_true", help="Backend-only install")
    p_configure.add_argument("--export", action="store_true", help="Print shell exports for scripts")
    p_configure.add_argument("--quiet", action="store_true", help="Skip access URL banner")
    p_configure.add_argument(
        "--tailscale-serve",
        action="store_true",
        help="Expose via Tailscale HTTPS (tailnet only, enables browser mic)",
    )

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

    sub.add_parser("start", help="Start backend + Next.js frontend (repo clone)")

    args = parser.parse_args()
    if args.cmd == "setup":
        raise SystemExit(asyncio.run(cmd_setup(args)))
    if args.cmd == "configure":
        raise SystemExit(cmd_configure(args))
    if args.cmd == "doctor":
        raise SystemExit(asyncio.run(cmd_doctor()))
    if args.cmd == "serve":
        raise SystemExit(cmd_serve(args))
    if args.cmd == "start":
        raise SystemExit(cmd_start(args))

    # Default: serve
    raise SystemExit(cmd_serve(argparse.Namespace(port=8080, host="127.0.0.1", open=True, voice=False)))


if __name__ == "__main__":
    main()