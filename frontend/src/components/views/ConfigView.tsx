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
  const [rt, setRt] = useState("auto");
  const [hermesUrl, setHermesUrl] = useState("http://127.0.0.1:8642");
  const [hermesKey, setHermesKey] = useState("");
  const [ocUrl, setOcUrl] = useState("ws://127.0.0.1:18789");
  const [ocToken, setOcToken] = useState("");

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
      })
      .catch(() => {});
  }, [voiceConfig]);

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
      setNote("Saved to ~/.hermes/config.yaml (and voice sections)");
      onSaved?.();
    } finally {
      setSaving(false);
    }
  };

  const runtimeLabel = runtime && runtime !== "offline" ? runtime : live ? "connected" : "—";

  return (
    <div className="space-y-4 pb-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[#00f5ff]">
          <Settings2 className="h-4 w-4" />
          <span className="text-sm font-semibold tracking-[0.08em] uppercase">Configuration</span>
        </div>
        <Button onClick={save} disabled={saving} prefix={<Save className="h-3.5 w-3.5" />}>
          {saving ? "Saving…" : "Save to Hermes"}
        </Button>
      </div>

      {note && <div className="text-[11px] text-emerald-400">{note}</div>}

      {/* Runtime + Connections */}
      <Card>
        <CardHeader>
          <CardTitle>Runtime &amp; Connections</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Active Runtime</div>
            <select
              value={rt}
              onChange={(e) => setRt(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 text-sm font-mono"
            >
              <option value="auto">Auto-detect</option>
              <option value="hermes">Hermes</option>
              <option value="openclaw">OpenClaw</option>
            </select>
            <div className="mt-1 text-[10px] text-slate-500">Current: <span className="font-mono">{runtimeLabel}</span></div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Hermes Gateway URL</div>
              <Input value={hermesUrl} onChange={(e) => setHermesUrl(e.target.value)} />
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Hermes API Key (stored in .env)</div>
              <Input type="password" value={hermesKey} onChange={(e) => setHermesKey(e.target.value)} placeholder="••••••••" />
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">OpenClaw WS URL</div>
              <Input value={ocUrl} onChange={(e) => setOcUrl(e.target.value)} />
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">OpenClaw Token</div>
              <Input type="password" value={ocToken} onChange={(e) => setOcToken(e.target.value)} placeholder="••••••••" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Voice — Alpha OS */}
      <Card>
        <CardHeader>
          <CardTitle>Voice — Alpha OS (Browser + Server)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2">
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Wake phrase</div>
              <Input value={wakeWord} onChange={(e) => setWakeWord(e.target.value)} />
            </div>
            <div className="flex flex-col justify-end gap-2 pt-1 text-xs">
              <label className="flex items-center gap-2 text-slate-400">
                <input type="checkbox" checked={browserWake} onChange={(e) => setBrowserWake(e.target.checked)} className="accent-[#00f5ff]" />
                Browser always-on wake
              </label>
              <label className="flex items-center gap-2 text-slate-400">
                <input type="checkbox" checked={serverWake} onChange={(e) => setServerWake(e.target.checked)} className="accent-[#00f5ff]" />
                Server mic wake (alpha-os serve --voice)
              </label>
              <label className="flex items-center gap-2 text-slate-400">
                <input type="checkbox" checked={grokOauth} onChange={(e) => setGrokOauth(e.target.checked)} className="accent-[#00f5ff]" />
                Grok via X OAuth / SuperGrok
              </label>
            </div>

            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Record key</div>
              <Input value={recordKey} onChange={(e) => setRecordKey(e.target.value)} />
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Silence duration (s)</div>
              <Input
                type="number"
                step="0.5"
                value={silenceDuration}
                onChange={(e) => setSilenceDuration(parseFloat(e.target.value) || 3)}
              />
            </div>

            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Silence threshold</div>
              <Input
                type="number"
                value={silenceThreshold}
                onChange={(e) => setSilenceThreshold(parseInt(e.target.value, 10) || 200)}
              />
            </div>

            <div className="flex flex-col justify-end gap-1.5 text-xs">
              <label className="flex items-center gap-2 text-slate-400">
                <input type="checkbox" checked={autoTts} onChange={(e) => setAutoTts(e.target.checked)} className="accent-[#00f5ff]" /> Auto TTS
              </label>
              <label className="flex items-center gap-2 text-slate-400">
                <input type="checkbox" checked={beepEnabled} onChange={(e) => setBeepEnabled(e.target.checked)} className="accent-[#00f5ff]" /> Record beeps
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">STT provider</div>
              <select
                value={sttProvider}
                onChange={(e) => setSttProvider(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 text-sm"
              >
                <option value="local">local (Whisper)</option>
                <option value="groq">groq</option>
                <option value="openai">openai</option>
                <option value="xai">xai / grok-stt</option>
              </select>
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">STT model</div>
              <Input value={sttModel} onChange={(e) => setSttModel(e.target.value)} disabled={sttProvider !== "local"} />
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">TTS provider</div>
              <select
                value={ttsProvider}
                onChange={(e) => setTtsProvider(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 text-sm"
              >
                <option value="edge">edge (free)</option>
                <option value="neutts">neutts (local)</option>
                <option value="elevenlabs">elevenlabs</option>
                <option value="openai">openai</option>
                <option value="xai">xai / grok voices</option>
              </select>
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">TTS voice</div>
              <Input value={ttsVoice} onChange={(e) => setTtsVoice(e.target.value)} />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="text-[10px] text-slate-500">
        Changes are written into <code className="text-[#00f5ff]/70">~/.hermes/config.yaml</code> under <code>alpha_os</code> / voice / stt / tts sections. Hermes picks them up on gateway restart.
      </div>
    </div>
  );
}
