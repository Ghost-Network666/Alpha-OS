"use client";

import { memo, useEffect, useState } from "react";
import type { TailscaleExitNode, TailscaleStatus } from "@/types/state";

function formatDuration(totalSec: number): string {
  const sec = Math.max(0, Math.floor(totalSec));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function liveSeconds(since: number | null | undefined): number {
  if (!since) return 0;
  return Math.max(0, Date.now() / 1000 - since);
}

function exitLabel(node: TailscaleExitNode | null | undefined): string {
  if (!node) return "None (direct)";
  return node.hostname || node.dns_name || node.ip || "Exit node";
}

export const TailscaleLiveBar = memo(function TailscaleLiveBar({
  tailscale,
}: {
  tailscale: TailscaleStatus;
}) {
  const [, tick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const connected = Boolean(tailscale.connected);
  const uptimeSec = connected
    ? liveSeconds(tailscale.uptime_since) || tailscale.uptime_sec || 0
    : 0;
  const downtimeSec = !connected
    ? liveSeconds(tailscale.downtime_since) || tailscale.downtime_sec || 0
    : 0;

  const stateLabel =
    tailscale.backend_state === "Running" && connected
      ? "Running"
      : tailscale.available
        ? tailscale.backend_state
        : "Unavailable";

  const host = tailscale.hostname ?? tailscale.dns_name ?? tailscale.self_ip ?? "—";
  const exit = tailscale.exit_node;

  return (
    <div className="shrink-0 border-b border-slate-800/50 bg-[#07070c]/95 px-3 py-2 sm:px-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">
            Tailscale
          </span>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
              connected
                ? "border-emerald-500/45 bg-emerald-950/35 text-emerald-400"
                : "border-amber-600/40 bg-amber-950/30 text-amber-400"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                connected ? "animate-pulse bg-emerald-400" : "bg-amber-500"
              }`}
            />
            {stateLabel}
          </span>
        </div>

        <div className="min-w-0 font-mono text-sm font-semibold text-cyan-300">
          {host}
        </div>

        {tailscale.self_ip && (
          <div className="hidden font-mono text-[11px] text-slate-500 sm:block">
            {tailscale.self_ip}
          </div>
        )}

        <div className="flex min-w-0 flex-1 basis-full items-center gap-2 text-[10px] sm:basis-auto">
          <span className="shrink-0 uppercase tracking-wide text-slate-600">
            Exit node
          </span>
          <span
            className={`truncate font-mono ${
              exit ? "text-violet-300" : "text-slate-500"
            }`}
            title={exit?.dns_name ?? exitLabel(exit)}
          >
            {exitLabel(exit)}
          </span>
          {exit && (
            <span
              className={`shrink-0 rounded border px-1.5 py-px text-[9px] font-semibold uppercase ${
                exit.online
                  ? "border-emerald-800/60 text-emerald-500"
                  : "border-slate-700 text-slate-500"
              }`}
            >
              {exit.online ? "online" : "offline"}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 font-mono text-[10px]">
          {connected ? (
            <span className="text-emerald-500/90">
              Uptime{" "}
              <span className="font-semibold text-emerald-400">
                {formatDuration(uptimeSec)}
              </span>
            </span>
          ) : (
            <span className="text-amber-500/90">
              Downtime{" "}
              <span className="font-semibold text-amber-400">
                {formatDuration(downtimeSec)}
              </span>
            </span>
          )}
          {tailscale.peers_online != null && tailscale.peer_count != null && (
            <span className="text-slate-600">
              {tailscale.peers_online}/{tailscale.peer_count} peers
            </span>
          )}
        </div>
      </div>

      {tailscale.error && (
        <p className="mt-1 text-[10px] text-amber-500/90">{tailscale.error}</p>
      )}
    </div>
  );
});