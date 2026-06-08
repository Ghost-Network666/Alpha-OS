"use client";

import { memo } from "react";
import type { AlphaState } from "@/types/state";
import { MetricCard } from "./MetricCard";

interface MetricsBarProps {
  metrics: AlphaState["metrics"];
  polymarket: AlphaState["polymarket"];
  history: Record<string, number[]>;
  gatewayOnline?: boolean;
  pulseKey?: number;
}

function fmt(value: number | null | undefined, suffix = ""): string {
  if (value === null || value === undefined) return "—";
  return `${value}${suffix}`;
}

export const MetricsBar = memo(function MetricsBar({
  metrics,
  polymarket,
  history,
  gatewayOnline = true,
  pulseKey = 0,
}: MetricsBarProps) {
  const cards = [
    {
      key: "toolsets",
      label: "Toolsets",
      value: metrics.toolsets ?? 0,
      accent: "cyan" as const,
    },
    {
      key: "skills",
      label: "Skills",
      value: metrics.skills,
      accent: "green" as const,
    },
    {
      key: "tools",
      label: "Tools",
      value: metrics.tools,
      accent: "green" as const,
    },
    {
      key: "plugins",
      label: "MCP",
      value: metrics.plugins ?? 0,
      accent: "cyan" as const,
    },
    {
      key: "sessions",
      label: "Sessions",
      value: metrics.sessions,
      accent: "cyan" as const,
    },
    {
      key: "events",
      label: "Events/min",
      value: gatewayOnline ? metrics.events_per_min : "—",
      accent: gatewayOnline ? ("cyan" as const) : ("amber" as const),
    },
  ];

  const polyCards = polymarket.connected
    ? [
        {
          key: "pnl",
          label: "P&L Today",
          value: fmt(polymarket.pnl_today),
          accent: "green" as const,
          history: history.pnl ?? [],
        },
        {
          key: "positions",
          label: "Open Positions",
          value: fmt(polymarket.open_positions),
          accent: "cyan" as const,
          history: history.positions ?? [],
        },
        {
          key: "winrate",
          label: "Win Rate",
          value:
            polymarket.win_rate != null ? `${polymarket.win_rate}%` : "—",
          accent: "pink" as const,
          history: history.winrate ?? [],
        },
      ]
    : [];

  return (
    <div className="shrink-0 border-b border-slate-800/60 bg-[#0a0a0f]/80 px-4 py-2">
      <div className="flex gap-2 overflow-x-auto pb-1">
        {cards.map((c) => (
          <MetricCard
            key={c.key}
            label={c.label}
            value={c.value}
            history={history[c.key] ?? []}
            accent={c.accent}
            pulse={pulseKey > 0 && gatewayOnline}
          />
        ))}
        {polyCards.map((c) => (
          <MetricCard
            key={c.key}
            label={c.label}
            value={c.value}
            history={c.history}
            accent={c.accent}
            pulse={pulseKey > 0}
          />
        ))}
      </div>
    </div>
  );
});