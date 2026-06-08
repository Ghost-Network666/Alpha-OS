"use client";

import type { AlphaState } from "@/types/state";
import { McpPanel } from "./McpPanel";

interface SidePanelsProps {
  tailscale: AlphaState["tailscale"];
  integrations: AlphaState["integrations"];
  mcp: AlphaState["mcp"];
  runtime?: string;
  onMcpRefresh: () => void;
}

function Panel({
  title,
  badge,
  children,
}: {
  title: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          {title}
        </span>
        {badge}
      </div>
      {children}
    </section>
  );
}

export function SidePanels({
  tailscale,
  integrations,
  mcp,
  runtime,
  onMcpRefresh,
}: SidePanelsProps) {
  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto">
      <Panel
        title="Tailscale"
        badge={
          <span
            className={`rounded-full border px-2 py-px text-[9px] ${
              tailscale.available
                ? "border-emerald-800 text-emerald-500"
                : "border-slate-700 text-slate-500"
            }`}
          >
            {tailscale.available ? tailscale.backend_state : "unavailable"}
          </span>
        }
      >
        <div className="font-mono text-xs text-slate-300">
          {tailscale.hostname ?? tailscale.self_ip ?? "—"}
        </div>
        <div className="mt-2 max-h-24 space-y-1 overflow-y-auto text-[10px] text-slate-500">
          {(tailscale.peers ?? []).slice(0, 6).map((p, i) => (
            <div key={i} className="truncate">
              {p.hostname ?? p.ip ?? "peer"}
            </div>
          ))}
          {!tailscale.peers?.length && (
            <span className="italic text-slate-700">No peers</span>
          )}
        </div>
      </Panel>

      <Panel
        title="Integrations"
        badge={
          <span
            className={`rounded-full border px-2 py-px text-[9px] ${
              integrations.connected
                ? "border-emerald-800 text-emerald-500"
                : "border-amber-800 text-amber-500"
            }`}
          >
            {integrations.connected ? "LIVE" : "OFFLINE"}
          </span>
        }
      >
        <div className="space-y-2 text-[10px] text-slate-500">
          <div>
            <span className="text-slate-600">Toolsets: </span>
            {integrations.toolsets.length
              ? integrations.toolsets
                  .slice(0, 4)
                  .map((t) => t.name ?? t.label)
                  .join(", ")
              : "—"}
          </div>
          <div>
            <span className="text-slate-600">Skills: </span>
            {integrations.skills.length
              ? integrations.skills
                  .slice(0, 4)
                  .map((s) => s.name)
                  .join(", ")
              : "—"}
          </div>
        </div>
      </Panel>

      <McpPanel mcp={mcp} runtime={runtime} onRefresh={onMcpRefresh} compact />
    </div>
  );
}