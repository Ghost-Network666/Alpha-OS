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
    <div className="flex h-4 items-end gap-px sm:h-5">
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
      className={`min-w-0 flex-1 basis-[calc(33.333%-0.375rem)] rounded-lg border border-slate-800/80 bg-[#0d0d14]/90 px-2 py-1.5 transition-colors duration-300 sm:basis-[calc(25%-0.375rem)] sm:rounded-xl sm:px-2.5 sm:py-2 md:basis-[calc(16.666%-0.5rem)] lg:basis-[calc(11%-0.5rem)] ${
        pulse ? "border-cyan-500/40" : ""
      }`}
    >
      <div className="mb-0.5 truncate text-[8px] font-semibold uppercase tracking-[0.12em] text-slate-500 sm:text-[9px] sm:tracking-[0.15em]">
        {label}
      </div>
      <div className="font-mono text-base font-semibold sm:text-lg" style={{ color }}>
        {value}
      </div>
      <MiniSpark history={history} color={color} />
    </div>
  );
});