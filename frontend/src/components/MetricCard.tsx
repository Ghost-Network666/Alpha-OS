"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  YAxis,
} from "recharts";

interface MetricCardProps {
  label: string;
  value: string | number;
  history: number[];
  accent?: "cyan" | "green" | "pink";
  pulse?: boolean;
}

const ACCENTS = {
  cyan: { stroke: "#00f5ff", fill: "rgba(0,245,255,0.15)" },
  green: { stroke: "#00ff88", fill: "rgba(0,255,136,0.12)" },
  pink: { stroke: "#ff3366", fill: "rgba(255,51,102,0.12)" },
};

export function MetricCard({
  label,
  value,
  history,
  accent = "cyan",
  pulse = false,
}: MetricCardProps) {
  const [flash, setFlash] = useState(false);
  const colors = ACCENTS[accent];
  const chartData = (history.length ? history : [0]).map((v, i) => ({
    i,
    v,
  }));

  useEffect(() => {
    if (!pulse) return;
    setFlash(true);
    const t = setTimeout(() => setFlash(false), 600);
    return () => clearTimeout(t);
  }, [pulse, value]);

  return (
    <div
      className={`min-w-[140px] shrink-0 rounded-xl border border-slate-800/80 bg-[#0d0d14]/90 px-3 py-2 transition ${
        flash ? "border-cyan-500/50 shadow-[0_0_16px_rgba(0,245,255,0.15)]" : ""
      }`}
    >
      <div className="mb-1 text-[9px] font-semibold uppercase tracking-[0.15em] text-slate-500">
        {label}
      </div>
      <div
        className="mb-1 font-mono text-xl font-semibold"
        style={{ color: colors.stroke }}
      >
        {value}
      </div>
      <div className="h-8 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <YAxis hide domain={["dataMin", "dataMax"]} />
            <Area
              type="monotone"
              dataKey="v"
              stroke={colors.stroke}
              fill={colors.fill}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}