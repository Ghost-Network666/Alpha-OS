"use client";

import { useCallback, useRef, useState } from "react";
import { sendCommand } from "@/lib/api";

interface TerminalLine {
  who: "you" | "alpha" | "system" | "error";
  text: string;
  ts: string;
}

interface TerminalPanelProps {
  profiles: string[];
  defaultProfile?: string;
}

export function TerminalPanel({ profiles, defaultProfile }: TerminalPanelProps) {
  const [lines, setLines] = useState<TerminalLine[]>([
    {
      who: "system",
      text: "Alpha OS terminal — send commands to the active Hermes/OpenClaw runtime.",
      ts: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [targetProfile, setTargetProfile] = useState(defaultProfile ?? "");
  const scrollRef = useRef<HTMLDivElement>(null);

  const push = useCallback((who: TerminalLine["who"], text: string) => {
    setLines((prev) => [
      ...prev,
      { who, text, ts: new Date().toLocaleTimeString() },
    ]);
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    });
  }, []);

  const run = async () => {
    const cmd = input.trim();
    if (!cmd || busy) return;
    setInput("");
    setBusy(true);
    const prefix = targetProfile ? `[${targetProfile}] ` : "";
    push("you", `${prefix}${cmd}`);
    try {
      const full =
        targetProfile && !cmd.startsWith("/")
          ? `/profile ${targetProfile} ${cmd}`
          : cmd;
      const res = await sendCommand(full);
      const reply = String(res.reply ?? res.error ?? JSON.stringify(res));
      push(res.ok === false ? "error" : "alpha", reply);
    } catch (e) {
      push("error", e instanceof Error ? e.message : "Command failed");
    } finally {
      setBusy(false);
    }
  };

  const color: Record<TerminalLine["who"], string> = {
    you: "text-cyan-400",
    alpha: "text-emerald-400",
    system: "text-slate-500",
    error: "text-rose-400",
  };

  return (
    <div className="flex h-full min-h-[280px] flex-col">
      <div className="mb-2 flex items-center gap-2">
        <label className="text-[10px] uppercase text-slate-500">Target</label>
        <select
          value={targetProfile}
          onChange={(e) => setTargetProfile(e.target.value)}
          className="flex-1 rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
        >
          <option value="">Active runtime</option>
          {profiles.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded-lg border border-slate-800 bg-[#050508] p-2 font-mono text-[10px] leading-relaxed"
      >
        {lines.map((line, i) => (
          <div key={i} className="mb-1">
            <span className="text-slate-700">{line.ts}</span>{" "}
            <span className={color[line.who]}>{line.text}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void run();
          }}
          placeholder="Command or message…"
          disabled={busy}
          className="flex-1 rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 font-mono text-xs"
        />
        <button
          type="button"
          onClick={() => void run()}
          disabled={busy || !input.trim()}
          className="rounded-lg border border-cyan-800 bg-cyan-950/40 px-3 py-2 text-xs font-semibold text-cyan-300 disabled:opacity-50"
        >
          {busy ? "…" : "Send"}
        </button>
      </div>
      <p className="mt-2 text-[10px] text-slate-600">
        Tip: use Hermes CLI syntax, gateway commands, or natural language. Prefix
        with a profile to route to a specific agent.
      </p>
    </div>
  );
}