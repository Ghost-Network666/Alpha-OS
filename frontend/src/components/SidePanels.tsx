"use client";

import type { AlphaState } from "@/types/state";
import { refreshMcp } from "@/lib/api";

interface SidePanelsProps {
  tailscale: AlphaState["tailscale"];
  integrations: AlphaState["integrations"];
  mcp: AlphaState["mcp"];
  onMcpRefresh: () => void;
}

function Panel({
  title,
  badge,
  children,
  action,
}: {
  title: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          {title}
        </span>
        <div className="flex items-center gap-2">
          {badge}
          {action}
        </div>
      </div>
      {children}
    </section>
  );
}

export function SidePanels({
  tailscale,
  integrations,
  mcp,
  onMcpRefresh,
}: SidePanelsProps) {
  const handleMcpRefresh = async () => {
    await refreshMcp();
    onMcpRefresh();
  };

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

      <Panel
        title="MCP Servers"
        action={
          <button
            type="button"
            onClick={handleMcpRefresh}
            className="text-[9px] text-cyan-600 hover:text-cyan-400"
          >
            Refresh
          </button>
        }
        badge={
          <span className="font-mono text-[9px] text-slate-600">
            {mcp.server_count}
          </span>
        }
      >
        <div className="max-h-40 space-y-2 overflow-y-auto text-[10px]">
          {mcp.servers.length === 0 ? (
            <p className="text-[10px] leading-relaxed text-slate-600">
              No stdio servers — add{" "}
              <code className="text-cyan-800">mcp_servers</code> to{" "}
              <code className="text-cyan-800">~/.hermes/config.yaml</code>
            </p>
          ) : (
            mcp.servers.map((s) => (
              <div
                key={s.name}
                className="rounded-lg border border-slate-800/60 bg-[#0a0a0f]/50 px-2 py-1.5"
              >
                <div className="flex justify-between">
                  <span className="text-slate-300">{s.name}</span>
                  <span
                    className={
                      s.connected ? "text-[#00ff88]" : "text-slate-600"
                    }
                  >
                    {s.connected ? "● stdio" : "○ stdio"}
                  </span>
                </div>
                <div className="text-slate-600">
                  {s.tool_count} tools
                  {s.source ? ` · ${s.source}` : ""}
                </div>
              </div>
            ))
          )}
        </div>
      </Panel>
    </div>
  );
}