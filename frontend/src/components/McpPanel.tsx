"use client";

import { useState } from "react";
import { refreshMcp } from "@/lib/api";
import type { McpPanel as McpPanelState } from "@/types/state";

interface McpPanelProps {
  mcp: McpPanelState;
  runtime?: string;
  onRefresh: () => void;
  compact?: boolean;
}

function sourceLabel(source?: string) {
  if (source === "hermes") return "Hermes";
  if (source === "openclaw") return "OpenClaw";
  if (source === "override") return "override";
  return source ?? "runtime";
}

function statusClass(server: McpPanelState["servers"][number]) {
  if (server.probeable === false) return "text-cyan-500";
  return server.connected ? "text-emerald-400" : "text-amber-500";
}

function statusText(server: McpPanelState["servers"][number]) {
  if (server.probeable === false) return "remote · runtime";
  return server.connected ? "stdio · online" : "stdio · offline";
}

export function McpPanel({ mcp, runtime, onRefresh, compact = false }: McpPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshMcp();
      onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  const summary =
    mcp.summary ??
    (mcp.server_count
      ? `${mcp.server_count} server(s) · ${mcp.tool_count} tools`
      : "No MCP servers configured");

  return (
    <section className="rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
            MCP Servers
          </span>
          <p className="mt-1 text-[10px] leading-relaxed text-slate-600">
            Stdio servers from your Hermes/OpenClaw config — same subprocesses your
            agents launch.
          </p>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          className="shrink-0 text-[9px] text-cyan-600 hover:text-cyan-400 disabled:opacity-50"
        >
          {refreshing ? "…" : "Probe"}
        </button>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2 text-[9px]">
        <span
          className={`rounded-full border px-2 py-px ${
            mcp.connected
              ? "border-emerald-900/60 text-emerald-500"
              : "border-slate-800 text-slate-500"
          }`}
        >
          {summary}
        </span>
        {runtime && runtime !== "offline" && (
          <span className="font-mono text-slate-600">runtime: {runtime}</span>
        )}
        {(mcp.stdio_count ?? 0) > 0 && (
          <span className="text-slate-600">{mcp.stdio_count} stdio</span>
        )}
        {(mcp.remote_count ?? 0) > 0 && (
          <span className="text-slate-600">{mcp.remote_count} remote</span>
        )}
      </div>

      {mcp.error && !mcp.servers.length && (
        <p className="mb-3 text-[10px] leading-relaxed text-amber-600/90">{mcp.error}</p>
      )}

      <div className={`space-y-2 overflow-y-auto text-[10px] ${compact ? "max-h-48" : "max-h-72"}`}>
        {mcp.servers.length === 0 ? (
          <div className="space-y-2 text-[10px] leading-relaxed text-slate-600">
            <p>Add stdio MCP servers to the same config files Hermes or OpenClaw reads:</p>
            <div className="rounded-lg border border-slate-800 bg-[#0a0a0f]/60 px-2 py-2 font-mono">
              <div className="text-cyan-800">~/.hermes/config.yaml</div>
              <pre className="mt-1 whitespace-pre-wrap text-slate-500">{`mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path"]`}</pre>
            </div>
            <div className="rounded-lg border border-slate-800 bg-[#0a0a0f]/60 px-2 py-2 font-mono">
              <div className="text-cyan-800">~/.openclaw/openclaw.json</div>
              <pre className="mt-1 whitespace-pre-wrap text-slate-500">{`"mcp": {
  "servers": {
    "docs": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}`}</pre>
            </div>
          </div>
        ) : (
          mcp.servers.map((server) => {
            const open = expanded === server.name;
            return (
              <div
                key={server.name}
                className="rounded-lg border border-slate-800/60 bg-[#0a0a0f]/50 px-2 py-2"
              >
                <button
                  type="button"
                  onClick={() => setExpanded(open ? null : server.name)}
                  className="flex w-full items-start justify-between gap-2 text-left"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-slate-200">{server.name}</span>
                      <span className="text-[9px] text-slate-600">
                        {sourceLabel(server.source)}
                      </span>
                    </div>
                    {server.command_preview && (
                      <div className="mt-1 truncate font-mono text-[9px] text-slate-600">
                        {server.command_preview}
                      </div>
                    )}
                    {server.url && (
                      <div className="mt-1 truncate font-mono text-[9px] text-slate-600">
                        {server.url}
                      </div>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <div className={statusClass(server)}>{statusText(server)}</div>
                    <div className="text-slate-600">
                      {server.probeable === false
                        ? "listed"
                        : `${server.tool_count} tools`}
                    </div>
                  </div>
                </button>

                {open && (
                  <div className="mt-2 space-y-2 border-t border-slate-800/60 pt-2">
                    {server.note && (
                      <p className="text-[9px] leading-relaxed text-slate-500">{server.note}</p>
                    )}
                    {server.error && server.probeable !== false && (
                      <p className="text-[9px] leading-relaxed text-amber-600/90">
                        {server.error}
                      </p>
                    )}
                    {server.env_keys && server.env_keys.length > 0 && (
                      <p className="text-[9px] text-slate-600">
                        env: {server.env_keys.join(", ")}
                      </p>
                    )}
                    {server.config_path && (
                      <p className="truncate font-mono text-[9px] text-slate-600">
                        {server.config_path}
                      </p>
                    )}
                    {server.tools && server.tools.length > 0 ? (
                      <ul className="max-h-32 space-y-1 overflow-y-auto">
                        {server.tools.map((tool) => (
                          <li
                            key={tool.name}
                            className="rounded border border-slate-800/40 px-2 py-1"
                          >
                            <div className="font-mono text-[9px] text-cyan-700/90">
                              {tool.name}
                            </div>
                            {tool.description && (
                              <div className="text-[9px] text-slate-600">
                                {tool.description}
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : server.probeable !== false ? (
                      <p className="text-[9px] italic text-slate-600">No tools discovered</p>
                    ) : null}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {!compact && (mcp.config_paths?.length ?? 0) > 0 && (
        <div className="mt-3 border-t border-slate-800/50 pt-2">
          <div className="mb-1 text-[9px] uppercase tracking-wider text-slate-600">
            Config sources
          </div>
          <div className="space-y-1">
            {mcp.config_paths!.map((path) => (
              <div
                key={`${path.runtime}-${path.path}`}
                className="flex items-center justify-between gap-2 font-mono text-[9px]"
              >
                <span className="truncate text-slate-600">{path.path}</span>
                <span className={path.exists ? "text-emerald-600" : "text-slate-700"}>
                  {path.exists ? path.key : "missing"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}