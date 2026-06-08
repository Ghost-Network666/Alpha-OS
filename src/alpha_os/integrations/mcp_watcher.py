"""Watch Hermes/OpenClaw MCP config files and re-probe on change."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Awaitable, Callable

from alpha_os.integrations.mcp_discovery import discovery_sources

logger = logging.getLogger("alpha_os.mcp.watcher")


async def mcp_config_watch_loop(
    refresh: Callable[[], Awaitable[None]],
    interval: float = 2.0,
) -> None:
    """Re-run refresh when MCP config file mtimes change."""
    mtimes: dict[str, float] = {}
    initialized = False

    while True:
        try:
            changed = False
            seen: set[str] = set()

            for src in discovery_sources():
                seen.add(src)
                path = Path(src)
                if not path.exists():
                    if src in mtimes:
                        del mtimes[src]
                        if initialized:
                            changed = True
                    continue

                mtime = path.stat().st_mtime
                prev = mtimes.get(src)
                mtimes[src] = mtime
                if initialized and prev != mtime:
                    changed = True

            for stale in [k for k in mtimes if k not in seen]:
                del mtimes[stale]
                if initialized:
                    changed = True

            if not initialized:
                initialized = True
            elif changed:
                logger.info("MCP config changed — re-probing stdio servers")
                await refresh()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug("MCP config watch error: %s", e)

        await asyncio.sleep(interval)