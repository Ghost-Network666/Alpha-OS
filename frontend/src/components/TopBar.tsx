"use client";

import { memo, useEffect, useState } from "react";

interface TopBarProps {
  connected: boolean;
  runtime: string;
  hermesConnected: boolean;
  gatewayOnline?: boolean;
  openclawConnected?: boolean;
  reconnecting?: boolean;
  onReconnect: () => void;
  onSettings: () => void;
  onCustomizeView?: () => void;
}

export const TopBar = memo(function TopBar({
  connected,
  runtime,
  hermesConnected,
  gatewayOnline,
  openclawConnected,
  reconnecting = false,
  onReconnect,
  onSettings,
  onCustomizeView,
}: TopBarProps) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const tick = () => setNow(new Date());
    const id = setInterval(tick, 30_000);
    return () => clearInterval(id);
  }, []);

  const online = gatewayOnline ?? hermesConnected ?? Boolean(openclawConnected);
  const fullyConnected = connected && online;

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

  const reconnectLabel = reconnecting
    ? "Connecting…"
    : fullyConnected
      ? "Connected"
      : connected
        ? "Refresh"
        : "Reconnect";

  const reconnectClass = reconnecting
    ? "border-slate-700 bg-slate-900/60 text-slate-400"
    : fullyConnected
      ? "border-[#00ff88]/45 bg-[#00ff88]/10 text-[#00ff88]"
      : connected
        ? "border-cyan-800/50 bg-cyan-950/40 text-cyan-400"
        : "border-amber-700/50 bg-amber-950/30 text-amber-300";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-cyan-900/30 bg-[#0a0a0f]/95 px-3 pt-[env(safe-area-inset-top)] sm:gap-4 sm:px-4">
      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
        <div className="flex shrink-0 items-center gap-0.5 rounded-lg border border-cyan-500/35 bg-gradient-to-br from-cyan-950/70 via-[#0c1218] to-[#0a0a0f] px-2.5 py-1.5 sm:gap-1 sm:px-3 sm:py-2">
          <span className="text-base font-black tracking-[0.22em] text-[#00f5ff] sm:text-xl sm:tracking-[0.28em]">
            ALPHA
          </span>
          <span className="text-base font-semibold tracking-[0.32em] text-slate-200 sm:text-xl sm:tracking-[0.4em]">
            OS
          </span>
        </div>

        <span
          className={`hidden rounded-full border px-3 py-1 text-xs font-semibold min-[400px]:inline ${statusClass}`}
        >
          {statusLabel}
        </span>
        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold min-[400px]:hidden ${statusClass}`}
          aria-label={statusLabel}
        >
          {connected ? (online ? "●" : "○") : "○"}
        </span>

        {runtime !== "offline" && (
          <span className="hidden text-[10px] uppercase tracking-wider text-slate-600 md:inline">
            {runtime}
          </span>
        )}

        <button
          type="button"
          onClick={onReconnect}
          disabled={reconnecting}
          aria-label={reconnectLabel}
          className={`shrink-0 rounded-lg border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide transition hover:opacity-90 disabled:cursor-wait disabled:opacity-70 sm:px-3 sm:text-[11px] ${reconnectClass}`}
        >
          {reconnecting ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 animate-pulse rounded-full bg-current opacity-70" />
              <span className="hidden sm:inline">{reconnectLabel}</span>
            </span>
          ) : (
            <>
              <span className="hidden sm:inline">{reconnectLabel}</span>
              <span className="sm:hidden" aria-hidden>
                {fullyConnected ? "✓" : "↻"}
              </span>
            </>
          )}
        </button>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
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
});