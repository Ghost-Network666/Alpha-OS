"use client";

import { memo } from "react";
import type { LiveEvent } from "@/types/state";

interface TelemetryPanelProps {
  events: LiveEvent[];
  logs: { ts: string; who: string; msg: string }[];
}

export const TelemetryPanel = memo(function TelemetryPanel({
  events,
  logs,
}: TelemetryPanelProps) {
  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
      <span className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
        Telemetry
      </span>
      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto font-mono text-[11px]">
        {events.map((ev) => (
          <div key={ev.seq} className="text-slate-500">
            <span className="text-cyan-700">[{ev.source}]</span> {ev.summary}
          </div>
        ))}
        {logs.map((l, i) => (
          <div key={`log-${i}`} className="text-slate-600">
            <span className="text-slate-700">{l.ts}</span>{" "}
            <span className="text-cyan-800">{l.who}:</span> {l.msg}
          </div>
        ))}
        {events.length === 0 && logs.length === 0 && (
          <p className="italic text-slate-700">—</p>
        )}
      </div>
    </section>
  );
});