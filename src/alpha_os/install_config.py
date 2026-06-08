"""Install-time configuration — URLs, Hermes API, frontend env."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

from alpha_os.bridges.detector import _env_gateway_url
from alpha_os.config import CONFIG_DIR, load_config, read_hermes_env, save_config, set_hermes_env


def _pkg_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here.parent, here.parent.parent):
        if (candidate / "frontend").is_dir() or (candidate / "hermes_plugin").is_dir():
            return candidate
    return here.parent.parent


def has_frontend(pkg_root: Path | None = None) -> bool:
    root = pkg_root or _pkg_root()
    return (root / "frontend" / "package.json").exists()


def _lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def _tailscale_dns_name() -> str | None:
    if not shutil.which("tailscale"):
        return None
    try:
        proc = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            return None
        raw = json.loads(proc.stdout)
        dns = (raw.get("Self") or {}).get("DNSName", "")
        dns = dns.rstrip(".") if isinstance(dns, str) else ""
        return dns or None
    except Exception:
        return None


def _tailscale_ip() -> str | None:
    if not shutil.which("tailscale"):
        return None
    try:
        proc = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            return None
        ip = (proc.stdout or "").strip().splitlines()
        return ip[0].strip() if ip else None
    except Exception:
        return None


def _port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def _pick_backend_port(preferred: int) -> int:
    if not _port_in_use(preferred):
        return preferred
    for candidate in (8081, 9000, 8888, 18080, 8082):
        if candidate != preferred and not _port_in_use(candidate):
            return candidate
    return preferred


def configure_hermes_api() -> str | None:
    """Ensure Hermes API env exists — never overwrite an existing user setup."""
    hermes_home = Path.home() / ".hermes"
    if not hermes_home.exists():
        return None

    env = read_hermes_env()
    host = env.get("API_SERVER_HOST") or "127.0.0.1"
    port = env.get("API_SERVER_PORT") or "9999"
    api_key = env.get("API_SERVER_KEY") or env.get("HERMES_API_KEY")
    if not api_key:
        api_key = f"sk-alpha-os-{secrets.token_urlsafe(16)}"

    updates: dict[str, str] = {}
    if env.get("API_SERVER_ENABLED", "").lower() not in ("true", "1", "yes"):
        updates["API_SERVER_ENABLED"] = "true"
    if not env.get("API_SERVER_HOST"):
        updates["API_SERVER_HOST"] = host
    if not env.get("API_SERVER_PORT"):
        updates["API_SERVER_PORT"] = port
    if not env.get("API_SERVER_KEY"):
        updates["API_SERVER_KEY"] = api_key
    if not env.get("HERMES_API_KEY"):
        updates["HERMES_API_KEY"] = api_key
    if not env.get("HERMES_GATEWAY_URL"):
        updates["HERMES_GATEWAY_URL"] = f"http://{host}:{port}"
    if not env.get("API_SERVER_CORS_ORIGINS"):
        updates["API_SERVER_CORS_ORIGINS"] = (
            "http://127.0.0.1:3000,http://127.0.0.1:4000,"
            "http://localhost:3000,http://localhost:4000"
        )

    if updates:
        set_hermes_env(updates)
    return api_key


def write_frontend_env(
    pkg_root: Path,
    backend_url: str,
    backend_port: int,
    tailscale_https_url: str | None = None,
) -> bool:
    env_path = pkg_root / "frontend" / ".env.local"
    if not has_frontend(pkg_root):
        return False
    internal_url = f"http://127.0.0.1:{backend_port}"
    lines = [
        f"NEXT_PUBLIC_API_PORT={backend_port}",
        f"INTERNAL_API_URL={internal_url}",
    ]
    ts_https = (tailscale_https_url or _tailscale_dns_name() or "").strip().rstrip("/")
    if ts_https:
        if not ts_https.startswith("http"):
            ts_https = f"https://{ts_https}"
        lines.append(f"NEXT_PUBLIC_TAILSCALE_HTTPS_URL={ts_https}")
    lines.append("")
    env_path.write_text("\n".join(lines), encoding="utf-8")
    return True


def build_access_urls(
    host: str,
    backend_port: int,
    frontend_port: int,
    *,
    include_frontend: bool = True,
) -> dict[str, Any]:
    backend_url = f"http://{host}:{backend_port}"
    frontend_url = f"http://{host}:{frontend_port}" if include_frontend else None
    access_url = frontend_url or backend_url

    network_url = None
    lan = _lan_ip()
    if lan and lan != host and lan != "127.0.0.1":
        network_url = (
            f"http://{lan}:{frontend_port}"
            if include_frontend
            else f"http://{lan}:{backend_port}"
        )

    tailscale_url = None
    tailscale_https_url = None
    ts_dns = _tailscale_dns_name()
    if ts_dns:
        tailscale_https_url = f"https://{ts_dns}"
    ts_ip = _tailscale_ip()
    if ts_ip:
        tailscale_url = (
            f"http://{ts_ip}:{frontend_port}"
            if include_frontend
            else f"http://{ts_ip}:{backend_port}"
        )

    if tailscale_https_url and include_frontend:
        access_url = tailscale_https_url

    return {
        "host": host,
        "backend_port": backend_port,
        "frontend_port": frontend_port,
        "backend_url": backend_url,
        "frontend_url": frontend_url,
        "access_url": access_url,
        "network_url": network_url,
        "tailscale_url": tailscale_url,
        "tailscale_https_url": tailscale_https_url,
    }


def configure_tailscale_serve(
    *,
    frontend_port: int | None = None,
    backend_port: int | None = None,
    pkg_root: Path | None = None,
) -> str | None:
    """Expose Alpha OS over Tailscale HTTPS (tailnet only). Returns HTTPS URL."""
    root = pkg_root or _pkg_root()
    script = root / "scripts" / "tailscale-serve.sh"
    if not script.exists():
        return None
    fe = frontend_port or int(
        os.getenv("ALPHA_OS_FRONTEND_PORT")
        or load_config().get("frontend", {}).get("port", 4000)
    )
    be = backend_port or int(
        os.getenv("ALPHA_OS_PORT") or load_config().get("server", {}).get("port", 9000)
    )
    env = {
        **os.environ,
        "ALPHA_OS_FRONTEND_PORT": str(fe),
        "ALPHA_OS_PORT": str(be),
    }
    subprocess.run(["bash", str(script)], cwd=str(root), env=env, check=False)
    dns = _tailscale_dns_name()
    https_url = f"https://{dns}" if dns else None
    if https_url and has_frontend(root):
        be = int(env.get("ALPHA_OS_PORT", be))
        write_frontend_env(root, f"http://127.0.0.1:{be}", be, https_url)
    return https_url


def apply_configuration(
    *,
    host: str | None = None,
    backend_port: int | None = None,
    frontend_port: int | None = None,
    include_frontend: bool | None = None,
    pkg_root: Path | None = None,
) -> dict[str, Any]:
    root = pkg_root or _pkg_root()
    use_frontend = has_frontend(root) if include_frontend is None else include_frontend

    resolved_host = host or os.getenv("ALPHA_OS_HOST") or str(load_config().get("server", {}).get("host", "127.0.0.1"))
    preferred_backend = backend_port or int(
        os.getenv("ALPHA_OS_PORT") or load_config().get("server", {}).get("port", 8080)
    )
    resolved_backend = _pick_backend_port(preferred_backend)
    resolved_frontend = frontend_port or int(
        os.getenv("ALPHA_OS_FRONTEND_PORT")
        or load_config().get("frontend", {}).get("port", 3000)
    )

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    cfg.setdefault("server", {})["host"] = resolved_host
    cfg["server"]["port"] = resolved_backend
    if use_frontend:
        cfg.setdefault("frontend", {})["port"] = resolved_frontend
    save_config(cfg)

    voice_info: dict[str, Any] | None = None
    try:
        from alpha_os.voice.hermes_sync import ensure_hermes_alpha_os_block, sync_voice_to_alpha_os

        ensure_hermes_alpha_os_block()
        voice = sync_voice_to_alpha_os()
        voice_info = {
            "tts_provider": voice.get("tts_provider"),
            "tts_voice": voice.get("tts_voice"),
            "model_provider": voice.get("model_provider"),
            "hermes_profile": voice.get("hermes_profile"),
        }
    except Exception:
        pass

    api_key = configure_hermes_api()
    env = read_hermes_env()
    gateway_url = _env_gateway_url(env) or "http://127.0.0.1:9999"
    if api_key or gateway_url:
        cfg = load_config()
        hermes = cfg.setdefault("hermes", {})
        if api_key:
            hermes["api_key"] = api_key
        hermes["gateway_url"] = gateway_url
        save_config(cfg)

    urls = build_access_urls(
        resolved_host,
        resolved_backend,
        resolved_frontend,
        include_frontend=use_frontend,
    )
    if voice_info:
        urls["voice"] = voice_info
    write_frontend_env(
        root,
        urls["backend_url"],
        resolved_backend,
        urls.get("tailscale_https_url"),
    )
    urls["hermes_configured"] = api_key is not None
    urls["config_path"] = str(CONFIG_DIR / "config.yaml")
    urls["log_path"] = str(root / "alpha-os.log")
    return urls


def print_access_banner(urls: dict[str, Any], *, include_frontend: bool) -> None:
    print("")
    print("════════════════════════════════════════════════════════")
    print("  Alpha OS installed — full access URL")
    print("════════════════════════════════════════════════════════")
    print("")
    print(f"  {urls['access_url']}")
    print("")
    print(f"  API backend:  {urls['backend_url']}")
    if include_frontend and urls.get("frontend_url"):
        print(f"  Frontend UI:  {urls['frontend_url']}")
    if urls.get("network_url"):
        print(f"  LAN access:   {urls['network_url']}")
    if urls.get("tailscale_https_url"):
        print(f"  Tailscale HTTPS (mic):  {urls['tailscale_https_url']}/")
        print("    Run: ./scripts/tailscale-serve.sh  (tailnet only)")
    elif urls.get("tailscale_url"):
        print(f"  Tailscale HTTP:  {urls['tailscale_url']}  (no mic — use HTTPS)")
    print(f"  Config:       {urls['config_path']}")
    voice = urls.get("voice") or {}
    if voice.get("tts_provider"):
        label = " (SuperGrok)" if voice.get("tts_provider") == "xai" else ""
        print(
            f"  Voice/TTS:    {voice.get('tts_provider')} / {voice.get('tts_voice')}{label}"
        )
        if voice.get("model_provider"):
            print(f"  Hermes model: {voice.get('model_provider')} (profile: {voice.get('hermes_profile')})")
    if urls.get("hermes_configured"):
        print("  Hermes API:   enabled in ~/.hermes/.env")
    else:
        print("  Hermes API:   install Hermes for live gateway data")
    if urls.get("log_path"):
        print(f"  Log file:     {urls['log_path']}")
    print("")
    if include_frontend:
        print("  Start:  ./scripts/start.sh")
        print("          alpha-os start")
    else:
        print("  Start:  alpha-os serve")
    print("")


RUNTIME_ENV_PATH = CONFIG_DIR / "runtime.env"


def write_runtime_env(
    *,
    runtime: str,
    hermes_profile: str | None = None,
    hermes_home: str | None = None,
    openclaw_home_path: str | None = None,
) -> Path:
    """Persist install-time runtime selection for scripts/start.sh."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Alpha OS runtime — generated by install.sh",
        f'export ALPHA_OS_RUNTIME="{runtime}"',
    ]
    if runtime == "hermes":
        profile = hermes_profile or "alpha"
        home = hermes_home or str(Path.home() / ".hermes" / "profiles" / profile)
        lines.append(f'export HERMES_PROFILE="{profile}"')
        lines.append(f'export HERMES_HOME="{home}"')
    elif runtime == "openclaw":
        home = openclaw_home_path or str(Path.home() / ".openclaw")
        lines.append(f'export OPENCLAW_HOME="{home}"')
    lines.append("")
    RUNTIME_ENV_PATH.write_text("\n".join(lines), encoding="utf-8")
    return RUNTIME_ENV_PATH


def print_ready_banner(
    urls: dict[str, Any],
    *,
    runtime: str | None = None,
    hermes_profile: str | None = None,
) -> None:
    """Final install message with Tailscale IP preferred."""
    fe_port = urls.get("frontend_port", 4000)
    ts_ip = _tailscale_ip()
    localhost = f"http://localhost:{fe_port}/"
    print("")
    print("  Alpha OS is ready.")
    print("")
    if ts_ip:
        print(f"  Access here: http://{ts_ip}:{fe_port}/")
        print(f"  (or {localhost})")
    elif urls.get("tailscale_https_url"):
        print(f"  Access here: {urls['tailscale_https_url']}/")
        print(f"  (or {localhost})")
    elif urls.get("access_url"):
        print(f"  Access here: {urls['access_url']}/")
        print(f"  (or {localhost})")
    else:
        print(f"  Access here: {localhost}")
    if runtime:
        label = f"{runtime}"
        if runtime == "hermes" and hermes_profile:
            label = f"Hermes ({hermes_profile} profile)"
        print("")
        print(f"  Runtime: {label}")
    print("")
    print("  Start again: ./scripts/start.sh")
    print("")


def export_shell_env(urls: dict[str, Any], *, pkg_root: Path | None = None) -> str:
    root = pkg_root or _pkg_root()
    lines = [
        f'export ALPHA_OS_HOST="{urls["host"]}"',
        f'export ALPHA_OS_PORT="{urls["backend_port"]}"',
        f'export ALPHA_OS_FRONTEND_PORT="{urls["frontend_port"]}"',
        f'export ALPHA_OS_ACCESS_URL="{urls["access_url"]}"',
        f'export NEXT_PUBLIC_API_URL="{urls["backend_url"]}"',
        f'export ALPHA_OS_LOG="{urls.get("log_path") or root / "alpha-os.log"}"',
    ]
    ts_https = urls.get("tailscale_https_url")
    if ts_https:
        lines.append(f'export ALPHA_OS_TAILSCALE_HTTPS_URL="{ts_https}"')
        lines.append(f'export NEXT_PUBLIC_TAILSCALE_HTTPS_URL="{ts_https}"')
    return "\n".join(lines)