"use client";

import type { AlphaState } from "@/types/state";
import { MetricCard } from "./MetricCard";

interface MetricsBarProps {
  metrics: AlphaState["metrics"];
  mcp: AlphaState["mcp"];
  history: Record<string, number[]>;
  pulseKey?: number;
}

export function MetricsBar({
  metrics,
  mcp,
  history,
  pulseKey = 0,
}: MetricsBarProps) {
  const cards = [
    {
      key: "sessions",
      label: "Sessions",
      value: metrics.sessions,
      accent: "cyan" as const,
    },
    {
      key: "agents",
      label: "Agents",
      value: metrics.agents,
      accent: "cyan" as const,
    },
    {
      key: "tools",
      label: "Tools",
      value: metrics.tools,
      accent: "green" as const,
    },
    {
      key: "skills",
      label: "Skills",
      value: metrics.skills,
      accent: "green" as const,
    },
    {
      key: "events",
      label: "Events/min",
      value: metrics.events_per_min,
      accent: "cyan" as const,
    },
  ];

  if ((mcp.server_count ?? 0) > 0) {
    cards.push({
      key: "mcp_tools",
      label: "MCP Tools",
      value: mcp.tool_count,
      accent: "green" as const,
    });
  }

  return (
    <div className="shrink-0 border-b border-slate-800/60 bg-[#0a0a0f]/80 px-4 py-2">
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
        {cards.map((c) => (
          <MetricCard
            key={c.key}
            label={c.label}
            value={c.value}
            history={history[c.key] ?? []}
            accent={c.accent}
            pulse={pulseKey > 0}
          />
        ))}
      </div>
    </div>
  );
}