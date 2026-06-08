"""Turn MCP tool metadata and results into human-readable dashboard widgets."""

from __future__ import annotations

import json
import re
from typing import Any


def categorize_tool(name: str) -> str:
    n = name.lower()
    if "discover" in n:
        return "Discovery"
    if any(k in n for k in ("portfolio", "position", "pnl", "balance")):
        return "Portfolio"
    if any(k in n for k in ("order", "trade", "buy", "sell", "execute")):
        return "Trading"
    if "market" in n:
        return "Markets"
    if any(k in n for k in ("auth", "health", "status", "ping")):
        return "System"
    parts = name.split("_")
    if len(parts) > 1 and parts[0] in ("alpha", "mcp"):
        chunk = parts[1].replace("-", " ")
        return chunk.title() if chunk else "General"
    return "General"


def human_tool_label(name: str, description: str = "") -> str:
    if description:
        first = description.strip().split(".")[0].split("\n")[0].strip()
        if first:
            return first[:100]
    label = re.sub(r"^alpha_", "", name)
    label = label.replace("_", " ")
    return label[:100].title() or name


def _extract_text_content(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        if "content" in raw and isinstance(raw["content"], list):
            parts = []
            for block in raw["content"]:
                if isinstance(block, dict) and block.get("text"):
                    parts.append(str(block["text"]))
            return "\n".join(parts)
        if "text" in raw:
            return str(raw["text"])
        return json.dumps(raw, indent=2, default=str)
    if isinstance(raw, list):
        return json.dumps(raw, indent=2, default=str)
    return str(raw)


def _parse_jsonish(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _flatten_fields(data: Any, prefix: str = "", limit: int = 12) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []

    def walk(obj: Any, path: str) -> None:
        if len(fields) >= limit:
            return
        if isinstance(obj, dict):
            for k, v in list(obj.items())[:8]:
                key = f"{path}.{k}" if path else str(k)
                if isinstance(v, (dict, list)):
                    if isinstance(v, list) and v and not isinstance(v[0], (dict, list)):
                        fields.append({
                            "label": key.replace("_", " ").title(),
                            "value": ", ".join(str(x) for x in v[:5]),
                        })
                    else:
                        walk(v, key)
                else:
                    fields.append({
                        "label": key.replace("_", " ").title(),
                        "value": str(v)[:200],
                    })
        elif isinstance(obj, list) and obj:
            fields.append({
                "label": (path or "Items").replace("_", " ").title(),
                "value": f"{len(obj)} item(s)",
            })
            if isinstance(obj[0], dict):
                walk(obj[0], f"{path}[0]" if path else "Item")

    walk(data, prefix)
    return fields[:limit]


def humanize_tool_result(
    *,
    server: str,
    tool_name: str,
    description: str,
    raw: Any,
    ok: bool = True,
    error: str | None = None,
) -> dict[str, Any]:
    category = categorize_tool(tool_name)
    title = human_tool_label(tool_name, description)

    if not ok or error:
        return {
            "id": f"{server}:{tool_name}",
            "server": server,
            "tool": tool_name,
            "category": category,
            "title": title,
            "summary": error or "This tool could not return data right now.",
            "status": "error",
            "issue": error,
            "fields": [],
        }

    text = _extract_text_content(raw)
    parsed = _parse_jsonish(text) if isinstance(text, str) else raw
    fields = _flatten_fields(parsed)

    if isinstance(parsed, list):
        summary = f"Returned {len(parsed)} result(s) you can use in Hermes."
    elif isinstance(parsed, dict):
        summary = f"Live data from {server} — {len(fields)} field(s) shown below."
    else:
        summary = (text[:160] + "…") if len(text) > 160 else (text or "No data returned.")

    return {
        "id": f"{server}:{tool_name}",
        "server": server,
        "tool": tool_name,
        "category": category,
        "title": title,
        "summary": summary,
        "status": "ok",
        "fields": fields,
    }


def enrich_tool(server_connected: bool, tool: dict[str, Any]) -> dict[str, Any]:
    name = str(tool.get("name", ""))
    desc = str(tool.get("description", ""))
    status = "online" if server_connected else "offline"
    return {
        **tool,
        "category": categorize_tool(name),
        "human_label": human_tool_label(name, desc),
        "status": status,
        "issue": None if server_connected else "MCP server offline",
    }


def build_category_summary(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, int]] = {}
    for t in tools:
        cat = t.get("category", "General")
        st = t.get("status", "offline")
        bucket = buckets.setdefault(cat, {"online": 0, "offline": 0, "total": 0})
        bucket["total"] += 1
        if st == "online":
            bucket["online"] += 1
        else:
            bucket["offline"] += 1
    return [
        {"name": name, **counts}
        for name, counts in sorted(buckets.items(), key=lambda x: -x[1]["total"])
    ]