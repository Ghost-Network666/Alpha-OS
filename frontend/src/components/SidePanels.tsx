"use client";

import { memo } from "react";
import type { AlphaState } from "@/types/state";
import { McpPanel } from "@/components/McpPanel";
import { McpDataWidgets } from "@/components/McpDataWidgets";

interface SidePanelsProps {
  tailscale: AlphaState["tailscale"];
  integrations: AlphaState["integrations"];
  mcp: AlphaState["mcp"];
  gatewayOnline?: boolean;
  showTailscale?: boolean;
  showIntegrations?: boolean;
  showMcpTools?: boolean;
  showMcpData?: boolean;
  mcpCategoryFilter?: (category: string) => boolean;
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
    <section className="shrink-0 rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
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

export const SidePanels = memo(function SidePanels({
  tailscale,
  integrations,
  mcp,
  gatewayOnline = true,
  showTailscale = true,
  showIntegrations = true,
  showMcpTools = true,
  showMcpData = true,
  mcpCategoryFilter,
  onMcpRefresh,
}: SidePanelsProps) {
  const widgets = (mcp.widgets ?? []).filter(
    (w) => !mcpCategoryFilter || mcpCategoryFilter(w.category)
  );

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto overscroll-contain">
      {showTailscale && (
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
        </Panel>
      )}

      {showIntegrations && (
        <Panel
          title="Integrations"
          badge={
            <span
              className={`rounded-full border px-2 py-px text-[9px] ${
                integrations.connected && gatewayOnline
                  ? "border-emerald-800 text-emerald-500"
                  : "border-amber-800 text-amber-500"
              }`}
            >
              {integrations.connected && gatewayOnline ? "LIVE" : "OFFLINE"}
            </span>
          }
        >
          {integrations.error && !gatewayOnline && (
            <p className="mb-1 text-[10px] text-amber-500/90">{integrations.error}</p>
          )}
          <div className="text-[10px] text-slate-500">
            Hermes toolsets {integrations.toolsets.length} · skills{" "}
            {integrations.skills.length}
          </div>
        </Panel>
      )}

      {showMcpData && <McpDataWidgets widgets={widgets} onRefresh={onMcpRefresh} />}

      {showMcpTools && (
        <McpPanel
          mcp={mcp}
          categoryFilter={mcpCategoryFilter}
          onRefresh={onMcpRefresh}
        />
      )}
    </div>
  );
});