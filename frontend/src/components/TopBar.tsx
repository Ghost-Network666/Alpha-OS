"use client";

import { useEffect, useState } from "react";

interface TopBarProps {
  connected: boolean;
  runtime: string;
  hermesConnected: boolean;
  gatewayOnline?: boolean;
  openclawConnected?: boolean;
  onReconnect: () => void;
  onSettings: () => void;
  onCustomizeView?: () => void;
}

export function TopBar({
  connected,
  runtime,
  hermesConnected,
  gatewayOnline,
  openclawConnected,
  onReconnect,
  onSettings,
  onCustomizeView,
}: TopBarProps) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const online = gatewayOnline ?? hermesConnected ?? Boolean(openclawConnected);
  const statusLabel = connected
    ? online
      ? "● Gateway LIVE"
      : "○ Gateway OFFLINE"
    : "○ No Runtime";

  const statusClass = connected
    ? online
      ? "border-[#00ff88]/40 bg-[#00ff88]/10 text-[#00ff88]"
      : "border-amber-600/40 bg-amber-950/30 text-amber-400"
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
        {onCustomizeView && (
          <button
            type="button"
            onClick={onCustomizeView}
            className="rounded-lg border border-slate-700/80 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400 transition hover:border-cyan-700 hover:text-cyan-400"
          >
            View
          </button>
        )}
        <button
          type="button"
          onClick={onSettings}
          aria-label="Alpha OS Settings"
          title="Alpha OS Settings"
          className="flex items-center gap-2 rounded-lg border border-slate-700/80 px-2.5 py-1.5 text-slate-400 transition hover:border-cyan-700 hover:bg-cyan-950/30 hover:text-cyan-400"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          <span className="hidden text-[10px] font-semibold uppercase tracking-wide sm:inline">
            Settings
          </span>
        </button>
      </div>
    </header>
  );
}