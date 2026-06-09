"use client";

import { memo } from "react";
import type { VoiceLive } from "@/types/state";
import type { WakeWordStatus } from "@/hooks/useWakeWordListener";

interface VoiceLiveBarProps {
  voiceLive?: VoiceLive | null;
  wakeStatus?: WakeWordStatus;
  speaking?: boolean;
  lastActivity?: { kind: "tts" | "stt"; chars: number } | null;
}

function formatTokens(n: number): string {
  if (n >= 1000) return `~${(n / 1000).toFixed(1)}k tok`;
  return `~${n} tok`;
}

export const VoiceLiveBar = memo(function VoiceLiveBar({
  voiceLive,
  wakeStatus,
  speaking = false,
  lastActivity,
}: VoiceLiveBarProps) {
  if (!voiceLive) return null;

  const session = voiceLive.session;
  const voiceHot =
    speaking || wakeStatus === "capturing" || wakeStatus === "listening";
  const sttActive = wakeStatus === "capturing" || wakeStatus === "listening";

  return (
    <div className="mt-3 space-y-2">
      <div
        className={`rounded-xl border px-3 py-2 transition ${
          voiceHot
            ? "perf-lite-shadow border-cyan-700/50 bg-cyan-950/25 sm:shadow-[0_0_14px_rgba(34,211,238,0.08)]"
            : "border-slate-800/80 bg-[#0a0a0f]/90"
        }`}
      >
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.14em] ${
              voiceHot
                ? "border-emerald-500/50 bg-emerald-950/40 text-emerald-400"
                : "border-slate-700 bg-slate-900/60 text-slate-500"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                voiceHot ? "animate-pulse bg-emerald-400" : "bg-slate-600"
              }`}
            />
            Voice live
          </span>
          {voiceLive.tts_local && (
            <span className="rounded-full border border-violet-800/50 bg-violet-950/30 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-violet-300">
              local TTS
            </span>
          )}
          {voiceLive.stt_local && (
            <span className="rounded-full border border-violet-800/50 bg-violet-950/30 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-violet-300">
              local STT
            </span>
          )}
          {speaking && (
            <span className="text-[9px] font-semibold uppercase tracking-wide text-pink-400">
              Speaking…
            </span>
          )}
          {sttActive && !speaking && (
            <span className="text-[9px] font-semibold uppercase tracking-wide text-cyan-400">
              Mic active
            </span>
          )}
        </div>

        <div className="grid gap-1.5 text-[10px] leading-snug sm:grid-cols-2">
          <div className="min-w-0">
            <span className="text-slate-600">TTS </span>
            <span className="font-semibold text-cyan-300">
              {voiceLive.tts_provider_label}
            </span>
            {voiceLive.tts_voice ? (
              <span className="font-mono text-slate-500"> · {voiceLive.tts_voice}</span>
            ) : null}
            {voiceLive.tts_model && voiceLive.tts_provider === "elevenlabs" ? (
              <span className="block truncate font-mono text-slate-600">
                {voiceLive.tts_model}
              </span>
            ) : null}
          </div>
          <div className="min-w-0">
            <span className="text-slate-600">STT </span>
            <span
              className={`font-semibold ${
                sttActive ? "text-cyan-300" : "text-slate-400"
              }`}
            >
              {voiceLive.stt_enabled
                ? voiceLive.stt_provider_label
                : "off"}
            </span>
            {voiceLive.stt_enabled && voiceLive.stt_model ? (
              <span className="font-mono text-slate-500">
                {" "}
                · {voiceLive.stt_model}
              </span>
            ) : null}
          </div>
        </div>

        {session && (
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 border-t border-slate-800/60 pt-2 text-[9px] text-slate-500">
            <span>
              Session:{" "}
              <span className="font-mono text-slate-400">
                {session.tts_requests} TTS
              </span>
              {session.tts_characters > 0 && (
                <span className="font-mono text-slate-500">
                  {" "}
                  · {session.tts_characters} chars ·{" "}
                  {formatTokens(session.tts_estimated_tokens)}
                </span>
              )}
            </span>
            {session.stt_requests > 0 && (
              <span>
                <span className="font-mono text-slate-400">
                  {session.stt_requests} STT
                </span>
                <span className="font-mono text-slate-500">
                  {" "}
                  · {session.stt_characters} chars
                </span>
              </span>
            )}
            {session.estimated_tokens > 0 && (
              <span className="text-cyan-700/80">
                total {formatTokens(session.estimated_tokens)}
              </span>
            )}
          </div>
        )}

        {lastActivity && (
          <div className="mt-1 text-[9px] text-amber-600/90">
            Last {lastActivity.kind.toUpperCase()}: {lastActivity.chars} chars ·{" "}
            {formatTokens(Math.max(1, Math.floor(lastActivity.chars / 4)))}
          </div>
        )}
      </div>

      {!voiceLive.auto_tts && (
        <p className="text-[9px] text-slate-600">
          Auto TTS is off — replies won&apos;t be spoken until enabled in Settings.
        </p>
      )}
    </div>
  );
});