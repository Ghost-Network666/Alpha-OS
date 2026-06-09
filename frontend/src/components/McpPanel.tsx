"use client";

import { memo, useMemo, useState } from "react";
import type { McpPanel as McpPanelData } from "@/types/state";
import { refreshMcp } from "@/lib/api";

interface McpPanelProps {
  mcp: McpPanelData;
  categoryFilter?: (category: string) => boolean;
  onRefresh?: () => void;
}

export const McpPanel = memo(function McpPanel({
  mcp,
  categoryFilter,
  onRefresh,
}: McpPanelProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"all" | "online" | "offline">("all");

  const toggle = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const filteredServers = useMemo(() => {
    const q = query.trim().toLowerCase();
    return mcp.servers
      .map((s) => {
        const tools = (s.tools ?? []).filter((t) => {
          if (categoryFilter && t.category && !categoryFilter(t.category)) return false;
          if (statusFilter === "online" && t.status !== "online") return false;
          if (statusFilter === "offline" && t.status !== "offline") return false;
          if (!q) return true;
          return (
            t.name.toLowerCase().includes(q) ||
            (t.human_label ?? "").toLowerCase().includes(q) ||
            (t.description ?? "").toLowerCase().includes(q)
          );
        });
        return { ...s, tools };
      })
      .filter(
        (s) =>
          s.tools.length > 0 ||
          (!q && statusFilter === "all") ||
          s.name.toLowerCase().includes(q)
      );
  }, [mcp.servers, query, statusFilter, categoryFilter]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshMcp();
      onRefresh?.();
    } finally {
      setRefreshing(false);
    }
  };

  const serversOn = mcp.servers_online ?? mcp.servers.filter((s) => s.connected).length;
  const serversOff = mcp.servers_offline ?? mcp.server_count - serversOn;
  const toolsOn = mcp.tools_online ?? 0;
  const toolsOff = mcp.tools_offline ?? 0;

  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          MCP Tools
        </span>
        <span
          className={`rounded-full border px-2 py-px text-[9px] ${
            mcp.connected
              ? "border-emerald-800 text-emerald-500"
              : "border-amber-800 text-amber-500"
          }`}
        >
          {mcp.connected ? "LIVE" : "OFFLINE"}
        </span>
      </div>

      <div className="mb-2 grid grid-cols-2 gap-1 text-[9px] text-slate-500">
        <div>
          Servers{" "}
          <span className="text-[#00ff88]">{serversOn} on</span>
          {serversOff > 0 && (
            <>
              {" "}
              · <span className="text-amber-500">{serversOff} off</span>
            </>
          )}
        </div>
        <div className="text-right">
          Tools{" "}
          <span className="text-[#00ff88]">{toolsOn} on</span>
          {toolsOff > 0 && (
            <>
              {" "}
              · <span className="text-amber-500">{toolsOff} off</span>
            </>
          )}
        </div>
      </div>

      {(mcp.categories ?? []).length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {(mcp.categories ?? []).map((c) => (
            <span
              key={c.name}
              className="rounded border border-slate-800 px-1.5 py-px text-[8px] text-slate-600"
            >
              {c.name}{" "}
              <span className="text-[#00ff88]">{c.online}</span>/
              <span className="text-slate-500">{c.total}</span>
            </span>
          ))}
        </div>
      )}

      <div className="mb-2 flex flex-wrap gap-1">
        {(["all", "online", "offline"] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setStatusFilter(f)}
            className={`rounded px-1.5 py-0.5 text-[9px] uppercase ${
              statusFilter === f
                ? "bg-cyan-950/80 text-cyan-400"
                : "text-slate-600 hover:text-slate-400"
            }`}
          >
            {f}
          </button>
        ))}
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search…"
          className="min-w-0 flex-1 rounded border border-slate-800 bg-[#0a0a0f] px-2 py-0.5 text-[10px]"
        />
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          className="text-[9px] text-cyan-600 disabled:opacity-50"
        >
          {refreshing ? "…" : "↻"}
        </button>
      </div>

      {mcp.error && (
        <p className="mb-2 rounded border border-amber-900/40 bg-amber-950/20 px-2 py-1 text-[10px] text-amber-500/90">
          {mcp.error}
        </p>
      )}

      <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto overscroll-contain">
        {filteredServers.length === 0 ? (
          <p className="text-[10px] text-slate-600">No tools match your filters.</p>
        ) : (
          filteredServers.map((s) => {
            const open = expanded.has(s.name);
            const tools = s.tools ?? [];
            return (
              <div
                key={s.name}
                className="rounded-lg border border-slate-800/60 bg-[#0a0a0f]/50"
              >
                <button
                  type="button"
                  onClick={() => toggle(s.name)}
                  className="flex w-full items-center justify-between px-2 py-1.5 text-left"
                >
                  <span className="truncate text-[11px] text-slate-300">
                    {open ? "▾" : "▸"} {s.name}
                    <span className="ml-1 text-[9px] text-slate-600">({s.source})</span>
                  </span>
                  <span className="shrink-0 text-[9px]">
                    <span className={s.connected ? "text-[#00ff88]" : "text-amber-500"}>
                      {s.connected ? "● online" : "○ offline"}
                    </span>
                  </span>
                </button>
                {s.error && !s.connected && (
                  <p className="border-t border-slate-800/50 px-2 py-1 text-[9px] text-amber-500/80">
                    {s.error}
                  </p>
                )}
                {open && (
                  <div className="max-h-48 overflow-y-auto border-t border-slate-800/50 px-2 py-1">
                    {tools.map((t) => (
                      <div
                        key={`${s.name}-${t.name}`}
                        className="border-b border-slate-900/50 py-1 last:border-0"
                      >
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-[10px] text-slate-300">
                            {t.human_label ?? t.name}
                          </span>
                          <span
                            className={`shrink-0 text-[8px] font-bold uppercase ${
                              t.status === "online"
                                ? "text-[#00ff88]"
                                : "text-amber-600"
                            }`}
                          >
                            {t.status ?? "offline"}
                          </span>
                        </div>
                        <div className="font-mono text-[9px] text-slate-700">{t.name}</div>
                        {t.category && (
                          <span className="text-[8px] uppercase text-cyan-900">{t.category}</span>
                        )}
                        {t.issue && (
                          <p className="text-[9px] text-amber-600/80">{t.issue}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </section>
  );
});