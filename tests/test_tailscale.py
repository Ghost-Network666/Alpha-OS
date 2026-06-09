"""Tailscale status parsing tests."""

from __future__ import annotations

import time

from alpha_os.integrations.tailscale import parse_tailscale_status


def test_parse_running_with_exit_node() -> None:
    raw = {
        "BackendState": "Running",
        "Version": "1.98.3",
        "Self": {
            "HostName": "ghostnetwork-gmk",
            "DNSName": "ghostnetwork-gmk.tail83a477.ts.net.",
            "TailscaleIPs": ["100.115.102.75"],
            "Online": True,
            "ExitNode": False,
            "ExitNodeOption": False,
        },
        "Peer": {
            "nodekey:abc": {
                "ID": "nj7u54MddK11CNTRL",
                "HostName": "ie-dub-wg-101",
                "DNSName": "ie-dub-wg-101.mullvad.ts.net.",
                "TailscaleIPs": ["100.91.45.109"],
                "Online": True,
                "Active": True,
                "ExitNode": True,
                "ExitNodeOption": True,
            }
        },
    }
    prefs = {"ExitNodeID": "nj7u54MddK11CNTRL"}
    since = time.time() - 125
    data = parse_tailscale_status(raw, prefs, uptime_since=since, downtime_since=None)

    assert data["connected"] is True
    assert data["hostname"] == "ghostnetwork-gmk"
    assert data["backend_state"] == "Running"
    assert data["exit_node"]["hostname"] == "ie-dub-wg-101"
    assert data["uptime_sec"] >= 120


def test_parse_offline_tracks_downtime() -> None:
    raw = {
        "BackendState": "Stopped",
        "Self": {"Online": False, "HostName": "ghostnetwork-gmk"},
        "Peer": {},
    }
    since = time.time() - 60
    data = parse_tailscale_status(raw, None, uptime_since=None, downtime_since=since)

    assert data["connected"] is False
    assert data["downtime_sec"] >= 55
    assert data["uptime_sec"] == 0.0