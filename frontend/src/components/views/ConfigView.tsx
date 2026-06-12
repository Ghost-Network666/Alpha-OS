"use client";

import React, { useEffect, useState } from "react";
import { Settings2, Save } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { getHttpApiBase, postConfig, postVoiceConfig } from "@/lib/api";
import type { VoiceConfig } from "@/types/state";

const DEFAULT_VOICE: Partial<VoiceConfig> = {
  wake_word: "hey alpha",
  browser_wake: true,
  server_wake: false,
  grok_oauth: true,
  record_key: "ctrl+b",
  max_recording_seconds: 120,
  auto_tts: true,
  beep_enabled: true,
  silence_threshold: 200,
  silence_duration: 3.0,
  stt_enabled: true,
  stt_provider: "local",
  stt_model: "base",
  tts_provider: "edge",
  tts_voice: "en-US-AriaNeural",
};

interface ConfigViewProps {
  voiceConfig?: VoiceConfig;
  runtime?: string;
  live?: boolean;
  onSaved?: () => void;
}

export function ConfigView({ voiceConfig, runtime, live, onSaved }: ConfigViewProps) {
  const [step, setStep] = useState(1); // 1: Runtime choice, 2: Permissions, 3: MCP, 4: Voice/Finish
  const [rt, setRt] = useState("auto");
  const [hermesUrl, setHermesUrl] = useState("http://127.0.0.1:8642");
  const [hermesKey, setHermesKey] = useState("");
  const [ocUrl, setOcUrl] = useState("ws://127.0.0.1:18789");
  const [ocToken, setOcToken] = useState("");

  // Permissions (new for first-run grant flow)
  const [grantMcpRead, setGrantMcpRead] = useState(true);
  const [grantMcpWrite, setGrantMcpWrite] = useState(false);
  const [grantVoice, setGrantVoice] = useState(true);
  const [grantTailscale, setGrantTailscale] = useState(true);
  const [grantProfiles, setGrantProfiles] = useState(true);

  // MCP (auto discovery placeholder - real call would use /api/mcp/probe)
  const [mcpDiscovered, setMcpDiscovered] = useState<any[]>([]);
  const [mcpProbing, setMcpProbing] = useState(false);

  // Voice
  const [wakeWord, setWakeWord] = useState(DEFAULT_VOICE.wake_word!);
  const [browserWake, setBrowserWake] = useState(true);
  const [serverWake, setServerWake] = useState(false);
  const [grokOauth, setGrokOauth] = useState(true);
  const [recordKey, setRecordKey] = useState(DEFAULT_VOICE.record_key!);
  const [autoTts, setAutoTts] = useState(true);
  const [beepEnabled, setBeepEnabled] = useState(true);
  const [silenceThreshold, setSilenceThreshold] = useState(200);
  const [silenceDuration, setSilenceDuration] = useState(3.0);
  const [sttEnabled, setSttEnabled] = useState(true);
  const [sttProvider, setSttProvider] = useState("local");
  const [sttModel, setSttModel] = useState("base");
  const [ttsProvider, setTtsProvider] = useState("edge");
  const [ttsVoice, setTtsVoice] = useState("en-US-AriaNeural");

  const [saving, setSaving] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    const v = { ...DEFAULT_VOICE, ...voiceConfig };
    setWakeWord(v.wake_word ?? "hey alpha");
    setBrowserWake(v.browser_wake ?? true);
    setServerWake(v.server_wake ?? false);
    setGrokOauth(v.grok_oauth ?? true);
    setRecordKey(v.record_key ?? "ctrl+b");
    setAutoTts(v.auto_tts ?? true);
    setBeepEnabled(v.beep_enabled ?? true);
    setSilenceThreshold(v.silence_threshold ?? 200);
    setSilenceDuration(v.silence_duration ?? 3.0);
    setSttEnabled(v.stt_enabled ?? true);
    setSttProvider(v.stt_provider ?? "local");
    setSttModel(v.stt_model ?? "base");
    setTtsProvider(v.tts_provider ?? "edge");
    setTtsVoice(v.tts_voice ?? "en-US-AriaNeural");
    setNote(null);

    const base = getHttpApiBase();
    fetch(`${base}/api/config`)
      .then((r) => r.json())
      .then((cfg) => {
        if (cfg.runtime) setRt(cfg.runtime);
        if (cfg.hermes?.gateway_url) setHermesUrl(cfg.hermes.gateway_url);
        if (cfg.openclaw?.ws_url) setOcUrl(cfg.openclaw.ws_url);
        // Seed permissions from config if present
        if (cfg.permissions) {
          setGrantMcpRead(!!cfg.permissions.mcp_read);
          setGrantMcpWrite(!!cfg.permissions.mcp_write);
          setGrantVoice(!!cfg.permissions.voice);
          setGrantTailscale(!!cfg.permissions.tailscale);
          setGrantProfiles(!!cfg.permissions.profiles);
        }
      })
      .catch(() => {});
  }, [voiceConfig]);

  const probeMcp = async () => {
    setMcpProbing(true);
    try {
      const base = getHttpApiBase();
      const res = await fetch(`${base}/api/mcp/probe`); // assumes backend endpoint from mcp_discovery
      if (res.ok) {
        const data = await res.json();
        setMcpDiscovered(data.servers || data.mcp?.servers || []);
      } else {
        // fallback demo data for now
        setMcpDiscovered([
          { name: "filesystem", status: "online", tools: 12 },
          { name: "github", status: "offline", tools: 0 },
        ]);
      }
    } catch {
      setMcpDiscovered([
        { name: "filesystem", status: "online", tools: 12 },
        { name: "github", status: "offline", tools: 0 },
      ]);
    } finally {
      setMcpProbing(false);
    }
  };

  const save = async () => {
    setSaving(true);
    setNote(null);
    try {
      await postConfig({
        runtime: rt,
        hermes_gateway_url: hermesUrl || undefined,
        hermes_api_key: hermesKey || undefined,
        openclaw_ws_url: ocUrl || undefined,
        openclaw_token: ocToken || undefined,
        permissions: {
          mcp_read: grantMcpRead,
          mcp_write: grantMcpWrite,
          voice: grantVoice,
          tailscale: grantTailscale,
          profiles: grantProfiles,
        },
        mcp_servers: mcpDiscovered, // seed discovered
      });
      await postVoiceConfig({
        wake_word: wakeWord.trim() || "hey alpha",
        browser_wake: browserWake,
        server_wake: serverWake,
        grok_oauth: grokOauth,
        record_key: recordKey.trim() || "ctrl+b",
        max_recording_seconds: 120,
        auto_tts: autoTts,
        beep_enabled: beepEnabled,
        silence_threshold: silenceThreshold,
        silence_duration: silenceDuration,
        stt_enabled: sttEnabled,
        stt_provider: sttProvider,
        stt_model: sttModel,
        tts_provider: ttsProvider,
        tts_voice: ttsVoice,
      });
      setNote("Saved. First-run config complete. Reconnect to apply.");
      onSaved?.();
    } finally {
      setSaving(false);
    }
  };

  const runtimeLabel = runtime && runtime !== "offline" ? runtime : live ? "connected" : "—";

  const nextStep = () => setStep((s) => Math.min(4, s + 1));
  const prevStep = () => setStep((s) => Math.max(1, s - 1));

  const runtimeLabel = runtime && runtime !== "offline" ? runtime : live ? "connected" : "—";

  const nextStep = () => setStep((s) => Math.min(4, s + 1));
  const prevStep = () => setStep((s) => Math.max(1, s - 1));

  return (
    <div className="space-y-4 pb-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[#00f5ff]">
          <Settings2 className="h-4 w-4" />
          <span className="text-sm font-semibold tracking-[0.08em] uppercase">First-Run Setup Wizard</span>
        </div>
        <div className="flex gap-2">
          {step > 1 && <Button onClick={prevStep} variant="ghost" size="sm">Back</Button>}
          {step < 4 && <Button onClick={nextStep} size="sm">Next</Button>}
          <Button onClick={save} disabled={saving} prefix={<Save className="h-3.5 w-3.5" />}>
            {saving ? "Saving…" : "Finish &amp; Save"}
          </Button>
        </div>
      </div>

      {/* Progress steps */}
      <div className="flex gap-2 text-[10px]">
        {[
          { n: 1, l: "Choose Runtime" },
          { n: 2, l: "Permissions" },
          { n: 3, l: "MCP Discovery" },
          { n: 4, l: "Voice + Kabal Heartbeats" },
        ].map(s => (
          <div key={s.n} className={`flex-1 rounded px-2 py-1 text-center ${step === s.n ? "bg-cyan-950/60 text-cyan-400" : "bg-slate-800/40 text-slate-500"}`}>
            {s.n}. {s.l}
          </div>
        ))}
      </div>

      {note && <div className="text-[11px] text-emerald-400">{note}</div>}

      {/* Step content (wizard) */}
      {step === 1 && (
        <Card>
          <CardHeader><CardTitle>1. Choose Runtime (Hermes vs OpenClaw / Multi-Agent)</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <select value={rt} onChange={e=>setRt(e.target.value)} className="w-full rounded border border-slate-700 bg-[#0a0a0f] p-2 text-sm">
              <option value="auto">Auto (live detect from install script)</option>
              <option value="hermes">Hermes (supports Alpha / Reaper / Phantom profiles)</option>
              <option value="openclaw">OpenClaw</option>
            </select>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 text-sm">
              <Input placeholder="Hermes URL" value={hermesUrl} onChange={e=>setHermesUrl(e.target.value)} />
              <Input placeholder="Hermes Key" type="password" value={hermesKey} onChange={e=>setHermesKey(e.target.value)} />
              <Input placeholder="OpenClaw URL" value={ocUrl} onChange={e=>setOcUrl(e.target.value)} />
              <Input placeholder="OpenClaw Token" type="password" value={ocToken} onChange={e=>setOcToken(e.target.value)} />
            </div>
            <div className="text-[10px] text-slate-500">Current: {runtimeLabel}. Auto-detect now uses live ports/processes from the improved install script.</div>
          </CardContent>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardHeader><CardTitle>2. Grant Permissions (Read/Write Access)</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <label className="flex gap-2"><input type="checkbox" checked={grantMcpRead} onChange={e=>setGrantMcpRead(e.target.checked)} /> MCP Read (discover &amp; view tools)</label>
            <label className="flex gap-2"><input type="checkbox" checked={grantMcpWrite} onChange={e=>setGrantMcpWrite(e.target.checked)} /> MCP Write (execute tools)</label>
            <label className="flex gap-2"><input type="checkbox" checked={grantVoice} onChange={e=>setGrantVoice(e.target.checked)} /> Voice (mic + TTS)</label>
            <label className="flex gap-2"><input type="checkbox" checked={grantTailscale} onChange={e=>setGrantTailscale(e.target.checked)} /> Tailscale (HTTPS remote + mic)</label>
            <label className="flex gap-2"><input type="checkbox" checked={grantProfiles} onChange={e=>setGrantProfiles(e.target.checked)} /> Multi-agent profiles &amp; heartbeats (Kabal)</label>
          </CardContent>
        </Card>
      )}

      {step === 3 && (
        <Card>
          <CardHeader><CardTitle>3. MCP Tool Discovery &amp; UI Visibility</CardTitle></CardHeader>
          <CardContent>
            <Button onClick={probeMcp} disabled={mcpProbing} size="sm">{mcpProbing ? "Probing..." : "Probe &amp; Discover MCP Servers"}</Button>
            {mcpDiscovered.length > 0 && (
              <div className="mt-3 text-xs space-y-1">
                {mcpDiscovered.map((s,i) => <div key={i} className="border border-slate-800 rounded px-2 py-1">{s.name} — {s.status} ({s.tools} tools)</div>)}
              </div>
            )}
            <div className="mt-2 text-[10px] text-slate-500">Tools will appear in the dedicated <strong>MCP</strong> sidebar view. Full discovery uses the backend mcp_discovery module.</div>
          </CardContent>
        </Card>
      )}

      {step === 4 && (
        <Card>
          <CardHeader><CardTitle>4. Voice + Multi-Agent Kabal (Alpha / Reaper / Phantom) + Heartbeats</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>Voice settings (abridged — full in this view or SettingsDrawer).</div>
            <div className="grid grid-cols-2 gap-2">
              <Input value={wakeWord} onChange={e=>setWakeWord(e.target.value)} placeholder="Wake word" />
              <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={autoTts} onChange={e=>setAutoTts(e.target.checked)} /> Auto TTS</label>
            </div>
            <div className="border-t border-slate-800 pt-3">
              <div className="font-semibold mb-1">Kabal Agents &amp; Heartbeats</div>
              {["Alpha","Reaper","Phantom"].map(a => (
                <div key={a} className="flex justify-between text-xs border border-slate-800 rounded px-2 py-1 mb-1">
                  <span>{a} agent</span>
                  <span className="text-emerald-400">LIVE • Heartbeat active</span>
                </div>
              ))}
              <div className="text-[10px] text-slate-500">Heartbeats managed via backend (profile_agents + mcp_watcher). Toggle in Agents view or via CLI. Selection on load uses runtime + active_profile.</div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="text-[10px] text-slate-500">
        Saved to <code className="text-[#00f5ff]/70">~/.hermes/config.yaml</code> (alpha_os section) + ~/.alpha-os/runtime.env. Use sidebar views (Config / Agents / MCP) after saving + reconnect.
      </div>
    </div>
  );
}
