"use client";

import { memo } from "react";
import type { ProfileAgent } from "@/types/state";

interface ProfileAgentsRowProps {
  profiles: ProfileAgent[];
}

const STATUS_STYLES: Record<string, string> = {
  LIVE: "border-emerald-500/50 bg-emerald-950/40 text-emerald-400",
  ACTIVE: "border-cyan-500/40 bg-cyan-950/30 text-cyan-400",
  STANDBY: "border-slate-700/80 bg-[#0d0d14]/90 text-slate-500",
};

function statusClass(status: string): string {
  return STATUS_STYLES[status] ?? STATUS_STYLES.STANDBY;
}

export const ProfileAgentsRow = memo(function ProfileAgentsRow({
  profiles,
}: ProfileAgentsRowProps) {
  if (!profiles.length) return null;

  return (
    <div className="shrink-0 border-b border-slate-800/40 bg-[#08080c]/90 px-3 py-2 sm:px-4">
      <div className="mb-1.5 text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-600">
        Agents
      </div>
      <div className="flex flex-wrap gap-2">
        {profiles.map((profile) => {
          const accent = profile.color ?? "#00f5ff";
          const live = profile.status === "LIVE";
          const busy = Boolean(profile.busy && profile.activity);
          const statusText = busy ? "WORKING" : profile.status;

          return (
            <div
              key={profile.id}
              className={`relative min-w-[min(100%,11rem)] flex-1 basis-[calc(50%-0.25rem)] rounded-xl border px-3 py-2 transition-colors sm:min-w-[10rem] sm:basis-[calc(33.333%-0.5rem)] md:basis-[calc(25%-0.5rem)] lg:max-w-[16rem] lg:basis-[calc(20%-0.5rem)] ${
                profile.active
                  ? "border-cyan-700/50 bg-[#0d0d14]/95"
                  : "border-slate-800/80 bg-[#0d0d14]/80"
              } ${live || busy ? "perf-lite-shadow sm:shadow-[0_0_12px_rgba(0,255,136,0.12)]" : ""}`}
            >
              {(profile.active || busy) && (
                <span
                  className={`absolute right-2 top-2 h-1.5 w-1.5 rounded-full ${
                    busy ? "animate-pulse" : ""
                  }`}
                  style={{
                    background: live || busy ? "#00ff88" : accent,
                    boxShadow: live || busy ? "0 0 6px #00ff88" : undefined,
                  }}
                />
              )}
              <div
                className="mb-0.5 pr-4 font-mono text-sm font-bold uppercase tracking-wide"
                style={{ color: accent }}
              >
                {profile.name}
              </div>
              <div className="truncate text-[10px] text-slate-500">
                {profile.title ?? profile.model ?? "Hermes profile"}
              </div>

              {profile.activity ? (
                <div
                  className={`mt-1.5 line-clamp-2 text-[10px] leading-snug ${
                    busy ? "text-cyan-300/90" : "text-slate-500"
                  }`}
                  title={profile.activity}
                >
                  {profile.activity}
                </div>
              ) : live ? (
                <div className="mt-1.5 text-[10px] italic text-slate-600">
                  Standing by for commands…
                </div>
              ) : null}

              <div className="mt-1.5">
                <span
                  className={`inline-block rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${statusClass(
                    statusText
                  )} ${busy ? "animate-pulse" : ""}`}
                >
                  {statusText}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});