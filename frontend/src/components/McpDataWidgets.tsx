"use client";

import { memo, useState } from "react";
import type { McpWidget } from "@/types/state";
import { callMcpTool } from "@/lib/api";

interface McpDataWidgetsProps {
  widgets: McpWidget[];
  onRefresh?: () => void;
}

function StatusDot({ status }: { status: McpWidget["status"] }) {
  const cls =
    status === "ok"
      ? "text-[#00ff88]"
      : status === "error"
        ? "text-amber-500"
        : "text-slate-600";
  const label = status === "ok" ? "Live data" : status === "error" ? "Issue" : "Offline";
  return (
    <span className={`text-[9px] font-semibold uppercase ${cls}`}>
      {label}
    </span>
  );
}

export const McpDataWidgets = memo(function McpDataWidgets({
  widgets,
  onRefresh,
}: McpDataWidgetsProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const refreshOne = async (w: McpWidget) => {
    setLoading(w.id);
    try {
      await callMcpTool(w.server, w.tool, {});
      onRefresh?.();
    } finally {
      setLoading(null);
    }
  };

  if (!widgets.length) {
    return (
      <section className="shrink-0 rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          MCP live data
        </span>
        <p className="mt-2 text-[10px] text-slate-600">
          No live samples yet. Refresh MCP or wait for a connected server to pull data.
        </p>
      </section>
    );
  }

  return (
    <section className="shrink-0 space-y-2">
      <div className="flex items-center justify-between px-1">
        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          MCP live data
        </span>
        <span className="text-[9px] text-slate-600">Plain-language view</span>
      </div>
      {widgets.map((w) => (
        <article
          key={w.id}
          className="rounded-2xl border border-cyan-900/20 bg-[#0d0d14]/80 p-3"
        >
          <div className="mb-1 flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="text-xs font-medium text-slate-200">{w.title}</div>
              <div className="text-[9px] text-slate-600">
                {w.server} · {w.category}
              </div>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <StatusDot status={w.status} />
              <button
                type="button"
                disabled={loading === w.id}
                onClick={() => refreshOne(w)}
                className="text-[9px] text-cyan-700 hover:text-cyan-500 disabled:opacity-50"
              >
                {loading === w.id ? "…" : "Refresh"}
              </button>
            </div>
          </div>
          <p className="mb-2 text-[11px] leading-relaxed text-slate-400">{w.summary}</p>
          {w.issue && (
            <p className="mb-2 rounded border border-amber-900/40 bg-amber-950/20 px-2 py-1 text-[10px] text-amber-500/90">
              {w.issue}
            </p>
          )}
          {w.fields.length > 0 && (
            <dl className="grid grid-cols-1 gap-1 sm:grid-cols-2">
              {w.fields.map((f) => (
                <div
                  key={`${w.id}-${f.label}`}
                  className="rounded border border-slate-800/60 bg-[#0a0a0f]/40 px-2 py-1"
                >
                  <dt className="text-[9px] uppercase tracking-wide text-slate-600">
                    {f.label}
                  </dt>
                  <dd className="truncate font-mono text-[10px] text-cyan-800/90">
                    {f.value}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </article>
      ))}
    </section>
  );
});