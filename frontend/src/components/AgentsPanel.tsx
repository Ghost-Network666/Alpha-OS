"use client";

import type { AgentCard } from "@/types/state";

interface AgentsPanelProps {
  agents: AgentCard[];
}

export function AgentsPanel({ agents }: AgentsPanelProps) {
  return (
    <section className="flex h-full min-h-0 flex-col rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          Agents
        </span>
        <span className="font-mono text-xs text-slate-600">{agents.length}</span>
      </div>
      <div className="flex min-h-0 flex-1 flex-wrap content-start gap-3 overflow-y-auto">
        {agents.length === 0 ? (
          <p className="w-full text-center text-xs text-slate-700">—</p>
        ) : (
          agents.map((a) => (
            <div
              key={a.name}
              className="flex min-w-[130px] flex-col items-center rounded-xl border border-slate-800/80 bg-[#0a0a0f]/60 p-3"
            >
              <div
                className="mb-2 h-12 w-12 rounded-full border-2"
                style={{
                  borderColor: a.color ?? "#00f5ff",
                  boxShadow: `0 0 12px ${a.color ?? "#00f5ff"}44`,
                  background: `radial-gradient(circle at 30% 30%, ${a.color ?? "#00f5ff"}88, transparent)`,
                }}
              />
              <span className="max-w-full truncate text-xs font-semibold text-slate-200">
                {a.name}
              </span>
              {a.title && (
                <span className="max-w-full truncate text-[10px] text-slate-500">
                  {a.title}
                </span>
              )}
              <span
                className={`mt-1 text-[9px] font-bold uppercase tracking-wide ${
                  a.status === "ACTIVE"
                    ? "text-[#00ff88]"
                    : "text-slate-500"
                }`}
              >
                {a.status ?? "—"}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}