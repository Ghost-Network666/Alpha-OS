"use client";

import { useEffect, useState } from "react";

interface TopBarProps {
  connected: boolean;
  runtime: string;
  hermesConnected: boolean;
  openclawConnected?: boolean;
  onReconnect: () => void;
  onSettings: () => void;
}

export function TopBar({
  connected,
  runtime,
  hermesConnected,
  openclawConnected,
  onReconnect,
  onSettings,
}: TopBarProps) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const statusLabel = connected
    ? "● Hermes Connected"
    : "○ No Runtime";

  const statusClass = connected
    ? "border-[#00ff88]/40 bg-[#00ff88]/10 text-[#00ff88]"
    : "border-[#ff3366]/40 bg-[#ff3366]/10 text-[#ff3366]";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-cyan-900/30 bg-[#0a0a0f]/90 px-4 backdrop-blur-md">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold tracking-[0.2em] text-[#00f5ff]">
            ALPHA
          </span>
          <span className="text-lg font-light tracking-[0.35em] text-slate-500">
            OS
          </span>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusClass}`}
        >
          {statusLabel}
        </span>
        {runtime !== "offline" && (
          <span className="hidden text-[10px] uppercase tracking-wider text-slate-600 sm:inline">
            {runtime}
          </span>
        )}
        <button
          type="button"
          onClick={onReconnect}
          className="rounded-lg border border-cyan-800/50 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-400 transition hover:border-cyan-600 hover:bg-cyan-950/50"
        >
          Reconnect
        </button>
      </div>

      <div className="flex items-center gap-4">
        {now && (
          <div className="hidden text-right font-mono text-xs text-slate-400 sm:block">
            <div>{now.toLocaleTimeString()}</div>
            <div className="text-[10px] text-slate-600">
              {now.toLocaleDateString(undefined, {
                weekday: "short",
                month: "short",
                day: "numeric",
              })}
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={onSettings}
          aria-label="Settings"
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700/80 text-slate-400 transition hover:border-cyan-700 hover:text-cyan-400"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
          </svg>
        </button>
      </div>
    </header>
  );
}