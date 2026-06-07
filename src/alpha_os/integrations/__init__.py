"""Alpha OS integrations — Tailscale, MCP, and external services."""

from .mcp_bridge import MCPBridge, MCPRegistry
from .tailscale import TailscaleStatus

__all__ = ["MCPBridge", "MCPRegistry", "TailscaleStatus"]