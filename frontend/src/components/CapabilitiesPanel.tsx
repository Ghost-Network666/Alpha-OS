"use client";

import { memo, useMemo, useState } from "react";
import type { CapabilityCard } from "@/types/state";

type Tab = "all" | "toolset" | "skill" | "session";

interface CapabilitiesPanelProps {
  capabilities: CapabilityCard[];
  gatewayOnline?: boolean;
}

const TAB_LABELS: Record<Tab, string> = {
  all: "All",
  toolset: "Toolsets",
  skill: "Skills",
  session: "Sessions",
};

export const CapabilitiesPanel = memo(function CapabilitiesPanel({
  capabilities,
  gatewayOnline = true,
}: CapabilitiesPanelProps) {
  const [tab, setTab] = useState<Tab>("all");

  const counts = useMemo(() => {
    const c = { all: capabilities.length, toolset: 0, skill: 0, session: 0 };
    for (const item of capabilities) {
      const k = item.kind as Tab;
      if (k in c && k !== "all") c[k]++;
    }
    return c;
  }, [capabilities]);

  const filtered = useMemo(() => {
    if (tab === "all") return capabilities;
    return capabilities.filter((c) => c.kind === tab);
  }, [capabilities, tab]);

  return (
    <section className="flex h-full min-h-0 flex-col rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          Capabilities
        </span>
        <span
          className={`rounded-full border px-2 py-px text-[9px] font-semibold ${
            gatewayOnline
              ? "border-emerald-800 text-emerald-500"
              : "border-amber-800 text-amber-500"
          }`}
        >
          {gatewayOnline ? "LIVE" : "OFFLINE"}
        </span>
      </div>

      <div className="mb-3 flex flex-wrap gap-1">
        {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-md px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide transition ${
              tab === t
                ? "bg-cyan-950/80 text-cyan-400"
                : "text-slate-600 hover:text-slate-400"
            }`}
          >
            {TAB_LABELS[t]} {counts[t] > 0 ? counts[t] : ""}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto overscroll-contain">
        {!gatewayOnline && (
          <p className="rounded-lg border border-amber-900/40 bg-amber-950/20 px-2 py-1.5 text-[10px] text-amber-500/90">
            Gateway offline — cached list may be stale. Reconnect when Hermes is back.
          </p>
        )}
        {filtered.length === 0 ? (
          <p className="text-center text-xs text-slate-700">—</p>
        ) : (
          filtered.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-2 rounded-lg border border-slate-800/70 bg-[#0a0a0f]/50 px-2 py-1.5"
            >
              <div
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: item.color ?? "#00f5ff" }}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-xs font-medium text-slate-200">
                    {item.name}
                  </span>
                  <span className="shrink-0 text-[8px] font-bold uppercase tracking-wider text-slate-600">
                    {item.kind}
                  </span>
                </div>
                {item.title && (
                  <p className="truncate text-[10px] text-slate-500">{item.title}</p>
                )}
              </div>
              <span
                className={`shrink-0 text-[8px] font-bold uppercase ${
                  item.status === "ACTIVE"
                    ? "text-[#00ff88]"
                    : item.status === "OFFLINE"
                      ? "text-amber-600"
                      : "text-slate-600"
                }`}
              >
                {item.status ?? "—"}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
});