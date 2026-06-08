"use client";

import { useState } from "react";
import { sendCommand } from "@/lib/api";
import { ActivityOrb } from "./ActivityOrb";
import type { WakeWordStatus } from "@/hooks/useWakeWordListener";

interface CommandPanelProps {
  greeting: string;
  orbPulse: boolean;
  hasActivity: boolean;
  wakeStatus?: WakeWordStatus;
  wakeDetail?: string;
  wakeWord?: string;
  onLog: (msg: string, who?: string) => void;
  onReply?: (reply: string) => void;
}

function wakeStatusLabel(
  status: WakeWordStatus | undefined,
  wakeWord: string,
  detail?: string
): string {
  switch (status) {
    case "loading":
      return "Initializing wake word engine…";
    case "listening":
      return `Listening for “${wakeWord}”`;
    case "capturing":
      return "Wake word detected — speak your command";
    case "error":
      return detail ?? "Wake word unavailable — use text input";
    case "unsupported":
      return "Voice unsupported in this browser";
    default:
      return `Say “${wakeWord}” to command Alpha`;
  }
}

export function CommandPanel({
  greeting,
  orbPulse,
  hasActivity,
  wakeStatus = "idle",
  wakeDetail,
  wakeWord = "hey alpha",
  onLog,
  onReply,
}: CommandPanelProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    const cmd = input.trim();
    if (!cmd || sending) return;
    setSending(true);
    onLog(cmd, "you");
    setInput("");
    try {
      const res = await sendCommand(cmd);
      const reply = res.reply ?? "No response";
      onLog(reply, "alpha");
      onReply?.(reply);
    } catch (e) {
      onLog(e instanceof Error ? e.message : "Command failed", "system");
    } finally {
      setSending(false);
    }
  };

  const voiceActive = wakeStatus === "listening" || wakeStatus === "capturing";
  const voiceHot = wakeStatus === "capturing";

  return (
    <section className="flex h-full min-h-0 flex-col rounded-2xl border border-cyan-900/25 bg-[#0d0d14]/80 p-4">
      <div className="mb-4 flex items-start gap-4">
        <ActivityOrb pulse={orbPulse || voiceHot} active={hasActivity || voiceActive} />
        <div className="flex-1 pt-1">
          <p className="text-sm leading-relaxed text-slate-400">{greeting}</p>
          <div
            className={`mt-2 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] transition ${
              voiceHot
                ? "border-[#ff3366]/60 bg-[#ff3366]/15 text-pink-300 shadow-[0_0_18px_rgba(255,51,102,0.25)]"
                : voiceActive
                  ? "border-cyan-800/60 bg-cyan-950/40 text-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                  : "border-slate-800 bg-[#0a0a0f] text-slate-500"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                voiceHot
                  ? "animate-pulse bg-[#ff3366]"
                  : voiceActive
                    ? "animate-pulse bg-cyan-400"
                    : "bg-slate-600"
              }`}
            />
            {wakeStatusLabel(wakeStatus, wakeWord, wakeDetail)}
          </div>
        </div>
      </div>
      <div className="mt-auto flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder='Or type a command…'
          disabled={sending}
          className="flex-1 rounded-xl border border-slate-800 bg-[#0a0a0f] px-4 py-2.5 text-sm text-slate-200 outline-none transition focus:border-cyan-700 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={submit}
          disabled={sending}
          className="rounded-xl border border-cyan-800 bg-cyan-950/60 px-4 py-2 text-sm font-semibold text-cyan-300 transition hover:bg-cyan-900/50 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </section>
  );
}