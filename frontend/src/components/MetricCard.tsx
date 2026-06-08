"use client";

import { memo } from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  history: number[];
  accent?: "cyan" | "green" | "pink" | "amber";
  pulse?: boolean;
}

const ACCENTS = {
  cyan: "#00f5ff",
  green: "#00ff88",
  pink: "#ff3366",
  amber: "#ff9f1c",
};

function MiniSpark({ history, color }: { history: number[]; color: string }) {
  const pts = history.length ? history.slice(-14) : [0];
  const max = Math.max(...pts, 1);
  return (
    <div className="flex h-6 items-end gap-px">
      {pts.map((v, i) => (
        <div
          key={i}
          className="min-w-[3px] flex-1 rounded-t-sm"
          style={{
            height: `${Math.max(8, (v / max) * 100)}%`,
            background: color,
            opacity: 0.55,
          }}
        />
      ))}
    </div>
  );
}

export const MetricCard = memo(function MetricCard({
  label,
  value,
  history,
  accent = "cyan",
  pulse = false,
}: MetricCardProps) {
  const color = ACCENTS[accent];

  return (
    <div
      className={`min-w-[120px] shrink-0 rounded-xl border border-slate-800/80 bg-[#0d0d14]/90 px-3 py-2 transition-colors duration-300 ${
        pulse ? "border-cyan-500/40" : ""
      }`}
    >
      <div className="mb-0.5 text-[9px] font-semibold uppercase tracking-[0.15em] text-slate-500">
        {label}
      </div>
      <div className="font-mono text-lg font-semibold" style={{ color }}>
        {value}
      </div>
      <MiniSpark history={history} color={color} />
    </div>
  );
});