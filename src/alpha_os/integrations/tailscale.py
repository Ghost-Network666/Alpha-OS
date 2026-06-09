"""Tailscale CLI wrapper with exit node + uptime/downtime tracking."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from typing import Any

logger = logging.getLogger("alpha_os.tailscale")


def _peer_brief(peer: dict[str, Any], peer_key: str) -> dict[str, Any]:
    ips = peer.get("TailscaleIPs") or []
    return {
        "id": peer.get("ID") or peer_key,
        "hostname": peer.get("HostName") or peer.get("DNSName") or peer_key,
        "dns_name": (peer.get("DNSName") or "").rstrip("."),
        "ip": ips[0] if ips else None,
        "online": bool(peer.get("Online")),
        "active": bool(peer.get("Active")),
        "os": peer.get("OS", ""),
        "is_exit_node": bool(peer.get("ExitNode")),
        "exit_node_option": bool(peer.get("ExitNodeOption")),
    }


def _resolve_exit_node(
    exit_node_id: str | None,
    peers_raw: dict[str, Any],
) -> dict[str, Any] | None:
    if not exit_node_id:
        return None
    needle = str(exit_node_id).strip()
    if not needle:
        return None
    for key, peer in peers_raw.items():
        if not isinstance(peer, dict):
            continue
        if peer.get("ID") == needle or key == needle:
            return _peer_brief(peer, key)
    return None


def _active_exit_peer(peers_raw: dict[str, Any]) -> dict[str, Any] | None:
    """Peer currently carrying exit traffic (Active + ExitNode)."""
    for key, peer in peers_raw.items():
        if not isinstance(peer, dict):
            continue
        if peer.get("Active") and peer.get("ExitNode"):
            return _peer_brief(peer, key)
    return None


def parse_tailscale_status(
    raw: dict[str, Any],
    prefs: dict[str, Any] | None = None,
    *,
    uptime_since: float | None = None,
    downtime_since: float | None = None,
) -> dict[str, Any]:
    """Build dashboard tailscale dict from `tailscale status --json` (+ optional prefs)."""
    now = time.time()
    self_node = raw.get("Self") if isinstance(raw.get("Self"), dict) else {}
    peers_raw = raw.get("Peer") if isinstance(raw.get("Peer"), dict) else {}

    self_ip = None
    ips = self_node.get("TailscaleIPs") or []
    if ips:
        self_ip = ips[0]

    hostname = self_node.get("HostName") or None
    dns_name = (self_node.get("DNSName") or "").rstrip(".") or None
    backend_state = str(raw.get("BackendState") or "unknown")
    online = bool(self_node.get("Online"))
    connected = backend_state.lower() == "running" and online

    exit_node_id = None
    if prefs:
        exit_node_id = str(prefs.get("ExitNodeID") or "").strip() or None

    exit_node = _resolve_exit_node(exit_node_id, peers_raw)
    if not exit_node:
        exit_node = _active_exit_peer(peers_raw)

    peers = []
    peers_online = 0
    for key, peer in peers_raw.items():
        if not isinstance(peer, dict):
            continue
        brief = _peer_brief(peer, key)
        peers.append(brief)
        if brief["online"]:
            peers_online += 1
    peers.sort(key=lambda p: (not p["online"], p.get("hostname") or ""))

    uptime_sec = max(0.0, now - uptime_since) if uptime_since and connected else 0.0
    downtime_sec = max(0.0, now - downtime_since) if downtime_since and not connected else 0.0

    return {
        "available": True,
        "backend_state": backend_state,
        "online": online,
        "connected": connected,
        "self_ip": self_ip,
        "hostname": hostname,
        "dns_name": dns_name,
        "version": str(raw.get("Version") or ""),
        "advertises_exit_node": bool(self_node.get("ExitNodeOption")),
        "is_exit_node": bool(self_node.get("ExitNode")),
        "exit_node": exit_node,
        "exit_node_id": exit_node_id,
        "uptime_since": uptime_since if connected else None,
        "downtime_since": downtime_since if not connected else None,
        "uptime_sec": round(uptime_sec, 1),
        "downtime_sec": round(downtime_sec, 1),
        "peers": peers[:20],
        "peer_count": len(peers),
        "peers_online": peers_online,
        "error": None,
    }


class TailscaleStatus:
    def __init__(self):
        self._data: dict[str, Any] = self._empty()
        self._uptime_since: float | None = None
        self._downtime_since: float | None = None
        self._was_connected = False

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "available": False,
            "backend_state": "unavailable",
            "online": False,
            "connected": False,
            "self_ip": None,
            "hostname": None,
            "dns_name": None,
            "version": None,
            "advertises_exit_node": False,
            "is_exit_node": False,
            "exit_node": None,
            "exit_node_id": None,
            "uptime_since": None,
            "downtime_since": None,
            "uptime_sec": 0.0,
            "downtime_sec": 0.0,
            "peers": [],
            "peer_count": 0,
            "peers_online": 0,
            "error": None,
        }

    def _tick_timers(self, connected: bool) -> None:
        now = time.time()
        if connected:
            if not self._was_connected:
                self._uptime_since = now
                self._downtime_since = None
        else:
            if self._was_connected:
                self._downtime_since = now
            if self._uptime_since is None and self._downtime_since is None:
                self._downtime_since = now
        self._was_connected = connected

    async def _run_json_cmd(self, *args: str) -> dict[str, Any] | None:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode() or f"{' '.join(args)} failed")
        text = stdout.decode().strip()
        if not text:
            return None
        return json.loads(text)

    async def refresh(self) -> dict[str, Any]:
        if not shutil.which("tailscale"):
            self._data = self._empty()
            self._data["error"] = "tailscale CLI not found"
            return dict(self._data)
        try:
            status_coro = self._run_json_cmd("tailscale", "status", "--json")
            prefs_coro = self._run_json_cmd("tailscale", "debug", "prefs")
            results = await asyncio.gather(status_coro, prefs_coro, return_exceptions=True)
            status_raw = results[0]
            prefs_raw = results[1]
            if isinstance(status_raw, Exception):
                raise status_raw
            if not isinstance(status_raw, dict):
                raise RuntimeError("tailscale status returned no data")
            prefs = prefs_raw if isinstance(prefs_raw, dict) else None

            preview = parse_tailscale_status(
                status_raw,
                prefs,
                uptime_since=self._uptime_since,
                downtime_since=self._downtime_since,
            )
            self._tick_timers(bool(preview.get("connected")))
            self._data = parse_tailscale_status(
                status_raw,
                prefs,
                uptime_since=self._uptime_since,
                downtime_since=self._downtime_since,
            )
        except Exception as e:
            logger.warning("Tailscale refresh failed: %s", e)
            self._tick_timers(False)
            self._data = self._empty()
            self._data["available"] = True
            self._data["backend_state"] = "error"
            self._data["error"] = str(e)
            self._data["downtime_since"] = self._downtime_since
            if self._downtime_since:
                self._data["downtime_sec"] = round(
                    max(0.0, time.time() - self._downtime_since), 1
                )
        return dict(self._data)

    def to_dict(self) -> dict[str, Any]:
        data = dict(self._data)
        now = time.time()
        if data.get("connected") and data.get("uptime_since"):
            data["uptime_sec"] = round(max(0.0, now - float(data["uptime_since"])), 1)
            data["downtime_sec"] = 0.0
            data["downtime_since"] = None
        elif data.get("downtime_since"):
            data["downtime_sec"] = round(
                max(0.0, now - float(data["downtime_since"])), 1
            )
            data["uptime_sec"] = 0.0
            data["uptime_since"] = None
        return data