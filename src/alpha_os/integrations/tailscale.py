"""Tailscale CLI wrapper with graceful fallback."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from typing import Any

logger = logging.getLogger("alpha_os.tailscale")


class TailscaleStatus:
    def __init__(self):
        self._data: dict[str, Any] = {
            "available": False,
            "backend_state": "unknown",
            "self_ip": None,
            "hostname": None,
            "exit_node": None,
            "peers": [],
            "error": None,
        }

    async def refresh(self) -> dict[str, Any]:
        if not shutil.which("tailscale"):
            self._data = {
                "available": False,
                "backend_state": "unavailable",
                "self_ip": None,
                "hostname": None,
                "exit_node": None,
                "peers": [],
                "error": "tailscale CLI not found",
            }
            return dict(self._data)
        try:
            proc = await asyncio.create_subprocess_exec(
                "tailscale", "status", "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode != 0:
                raise RuntimeError(stderr.decode() or "tailscale status failed")
            raw = json.loads(stdout.decode())
            self_ip = None
            hostname = raw.get("Self", {}).get("HostName") or raw.get("Self", {}).get("DNSName")
            if isinstance(raw.get("Self"), dict):
                ips = raw["Self"].get("TailscaleIPs", [])
                if ips:
                    self_ip = ips[0]
            peers = []
            for key, peer in (raw.get("Peer") or {}).items():
                if not isinstance(peer, dict):
                    continue
                peers.append({
                    "id": key,
                    "hostname": peer.get("HostName", peer.get("DNSName", key)),
                    "ip": (peer.get("TailscaleIPs") or [None])[0],
                    "online": peer.get("Online", False),
                    "os": peer.get("OS", ""),
                })
            self._data = {
                "available": True,
                "backend_state": raw.get("BackendState", "unknown"),
                "self_ip": self_ip,
                "hostname": hostname,
                "exit_node": raw.get("ExitNodeStatus"),
                "peers": peers[:20],
                "error": None,
            }
        except Exception as e:
            logger.warning("Tailscale refresh failed: %s", e)
            self._data["error"] = str(e)
            self._data["available"] = bool(shutil.which("tailscale"))
        return dict(self._data)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)