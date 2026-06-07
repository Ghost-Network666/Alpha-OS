"use client";

import { useEffect, useState } from "react";
import { postConfig, postVoiceConfig } from "@/lib/api";
import type { AlphaState, VoiceConfig } from "@/types/state";

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
  runtime: string;
  live?: boolean;
  voiceConfig?: VoiceConfig;
  onSaved: () => void;
}

const DEFAULT_VOICE: Partial<VoiceConfig> = {
  wake_word: "hey alpha",
  browser_wake: true,
  server_wake: false,
  grok_oauth: true,
  record_key: "ctrl+b",
  max_recording_seconds: 120,
  auto_tts: false,
  beep_enabled: true,
  silence_threshold: 200,
  silence_duration: 3.0,
  stt_enabled: true,
  stt_provider: "local",
  stt_model: "base",
  tts_provider: "edge",
  tts_voice: "en-US-AriaNeural",
};

export function SettingsDrawer({
  open,
  onClose,
  runtime,
  live = false,
  voiceConfig,
  onSaved,
}: SettingsDrawerProps) {
  const [hermesUrl, setHermesUrl] = useState("http://127.0.0.1:8642");
  const [hermesKey, setHermesKey] = useState("");
  const [ocUrl, setOcUrl] = useState("ws://127.0.0.1:18789");
  const [ocToken, setOcToken] = useState("");
  const [rt, setRt] = useState("auto");
  const [wakeWord, setWakeWord] = useState(DEFAULT_VOICE.wake_word!);
  const [browserWake, setBrowserWake] = useState(true);
  const [serverWake, setServerWake] = useState(false);
  const [grokOauth, setGrokOauth] = useState(true);
  const [recordKey, setRecordKey] = useState(DEFAULT_VOICE.record_key!);
  const [autoTts, setAutoTts] = useState(false);
  const [beepEnabled, setBeepEnabled] = useState(true);
  const [silenceThreshold, setSilenceThreshold] = useState(200);
  const [silenceDuration, setSilenceDuration] = useState(3.0);
  const [sttEnabled, setSttEnabled] = useState(true);
  const [sttProvider, setSttProvider] = useState("local");
  const [sttModel, setSttModel] = useState("base");
  const [ttsProvider, setTtsProvider] = useState("edge");
  const [ttsVoice, setTtsVoice] = useState("en-US-AriaNeural");
  const [saving, setSaving] = useState(false);
  const [saveNote, setSaveNote] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const v = { ...DEFAULT_VOICE, ...voiceConfig };
    setWakeWord(v.wake_word ?? "hey alpha");
    setBrowserWake(v.browser_wake ?? true);
    setServerWake(v.server_wake ?? v.enabled ?? false);
    setGrokOauth(v.grok_oauth ?? true);
    setRecordKey(v.record_key ?? "ctrl+b");
    setAutoTts(v.auto_tts ?? false);
    setBeepEnabled(v.beep_enabled ?? true);
    setSilenceThreshold(v.silence_threshold ?? 200);
    setSilenceDuration(v.silence_duration ?? 3.0);
    setSttEnabled(v.stt_enabled ?? true);
    setSttProvider(v.stt_provider ?? "local");
    setSttModel(v.stt_model ?? "base");
    setTtsProvider(v.tts_provider ?? "edge");
    setTtsVoice(v.tts_voice ?? "en-US-AriaNeural");
    setSaveNote(null);

    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080"}/api/config`)
      .then((r) => r.json())
      .then((cfg) => {
        if (cfg.runtime) setRt(cfg.runtime);
        if (cfg.hermes?.gateway_url) setHermesUrl(cfg.hermes.gateway_url);
        if (cfg.openclaw?.ws_url) setOcUrl(cfg.openclaw.ws_url);
      })
      .catch(() => {});
  }, [open, voiceConfig]);

  const save = async () => {
    setSaving(true);
    setSaveNote(null);
    try {
      await postConfig({
        runtime: rt,
        hermes_gateway_url: hermesUrl || undefined,
        hermes_api_key: hermesKey || undefined,
        openclaw_ws_url: ocUrl || undefined,
        openclaw_token: ocToken || undefined,
      });
      const res = await postVoiceConfig({
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
      const path = res?.voice?.hermes_config_path;
      setSaveNote(
        path
          ? `Saved to ${path}`
          : "Saved to ~/.hermes/config.yaml"
      );
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const runtimeLabel =
    runtime && runtime !== "offline" ? runtime : live ? "connected" : "—";

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/60 transition ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 right-0 z-50 w-96 max-w-[92vw] overflow-y-auto border-l border-cyan-900/30 bg-[#0d0d14] p-5 transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="mb-6 flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-cyan-400">
            Settings
          </span>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300"
          >
            ✕
          </button>
        </div>

        <div className="space-y-5 text-sm">
          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Voice — Alpha OS
            </div>
            <p className="mb-3 text-[10px] leading-relaxed text-slate-600">
              Changes are written to{" "}
              <code className="text-cyan-700">~/.hermes/config.yaml</code>{" "}
              (<code className="text-cyan-700">alpha_os</code>,{" "}
              <code className="text-cyan-700">voice</code>,{" "}
              <code className="text-cyan-700">stt</code>,{" "}
              <code className="text-cyan-700">tts</code>). Hermes CLI/gateway
              picks them up on restart.
            </p>

            <label className="mb-1 block text-[10px] text-slate-500">
              Wake phrase
            </label>
            <input
              value={wakeWord}
              onChange={(e) => setWakeWord(e.target.value)}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
            />

            <label className="mb-2 flex items-center gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={browserWake}
                onChange={(e) => setBrowserWake(e.target.checked)}
                className="accent-cyan-500"
              />
              Browser always-on wake (no button)
            </label>

            <label className="mb-2 flex items-center gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={serverWake}
                onChange={(e) => setServerWake(e.target.checked)}
                className="accent-cyan-500"
              />
              Server mic wake{" "}
              <span className="text-[10px] text-slate-600">
                (alpha-os serve --voice)
              </span>
            </label>

            <label className="mb-3 flex items-center gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={grokOauth}
                onChange={(e) => setGrokOauth(e.target.checked)}
                className="accent-cyan-500"
              />
              Grok via X OAuth / SuperGrok (not API keys)
            </label>
          </div>

          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Hermes voice (CLI / gateway)
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  Record key
                </label>
                <input
                  value={recordKey}
                  onChange={(e) => setRecordKey(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  Silence (s)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  max="10"
                  value={silenceDuration}
                  onChange={(e) =>
                    setSilenceDuration(parseFloat(e.target.value) || 3)
                  }
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                />
              </div>
            </div>

            <div className="mt-2 grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  Silence threshold
                </label>
                <input
                  type="number"
                  min="50"
                  max="2000"
                  value={silenceThreshold}
                  onChange={(e) =>
                    setSilenceThreshold(parseInt(e.target.value, 10) || 200)
                  }
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                />
              </div>
              <div className="flex flex-col justify-end gap-1">
                <label className="flex items-center gap-2 text-[10px] text-slate-400">
                  <input
                    type="checkbox"
                    checked={autoTts}
                    onChange={(e) => setAutoTts(e.target.checked)}
                    className="accent-cyan-500"
                  />
                  Auto TTS
                </label>
                <label className="flex items-center gap-2 text-[10px] text-slate-400">
                  <input
                    type="checkbox"
                    checked={beepEnabled}
                    onChange={(e) => setBeepEnabled(e.target.checked)}
                    className="accent-cyan-500"
                  />
                  Record beeps
                </label>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  STT provider
                </label>
                <select
                  value={sttProvider}
                  onChange={(e) => setSttProvider(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
                >
                  <option value="local">local (Whisper)</option>
                  <option value="groq">groq</option>
                  <option value="openai">openai</option>
                  <option value="xai">xai / grok-stt</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  STT model
                </label>
                <input
                  value={sttModel}
                  onChange={(e) => setSttModel(e.target.value)}
                  disabled={sttProvider !== "local"}
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs disabled:opacity-40"
                />
              </div>
            </div>

            <div className="mt-2 grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  TTS provider
                </label>
                <select
                  value={ttsProvider}
                  onChange={(e) => setTtsProvider(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
                >
                  <option value="edge">edge (free)</option>
                  <option value="neutts">neutts (local)</option>
                  <option value="elevenlabs">elevenlabs</option>
                  <option value="openai">openai</option>
                  <option value="xai">xai / grok voices</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  TTS voice
                </label>
                <input
                  value={ttsVoice}
                  onChange={(e) => setTtsVoice(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                />
              </div>
            </div>

            {voiceConfig?.providers && voiceConfig.providers.length > 0 && (
              <div className="mt-3 space-y-1">
                <div className="text-[10px] uppercase text-slate-500">
                  Status
                </div>
                {voiceConfig.providers.map((p) => (
                  <div key={p.id} className="text-[10px] text-slate-500">
                    {p.label}{" "}
                    <span
                      className={
                        p.available ? "text-emerald-600" : "text-slate-700"
                      }
                    >
                      {p.available ? "available" : "unavailable"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              MCP
            </div>
            <p className="text-xs leading-relaxed text-slate-500">
              Alpha OS probes <strong className="text-slate-400">stdio</strong>{" "}
              MCP servers from your runtime configs.
            </p>
            <ul className="mt-2 space-y-1.5 text-[10px] font-mono text-slate-600">
              <li className="rounded border border-slate-800 bg-[#0a0a0f] px-2 py-1.5">
                ~/.hermes/config.yaml →{" "}
                <span className="text-cyan-700">mcp_servers</span>
              </li>
              <li className="rounded border border-slate-800 bg-[#0a0a0f] px-2 py-1.5">
                ~/.openclaw/openclaw.json →{" "}
                <span className="text-cyan-700">mcp.servers</span>
              </li>
            </ul>
          </div>

          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Runtime
            </div>
            <select
              value={rt}
              onChange={(e) => setRt(e.target.value)}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 text-xs"
            >
              <option value="auto">Auto-detect</option>
              <option value="hermes">Hermes</option>
              <option value="openclaw">OpenClaw</option>
            </select>
            <p className="font-mono text-xs text-slate-400">
              Active: {runtimeLabel}
            </p>

            <label className="mb-1 mt-3 block text-[10px] uppercase text-slate-500">
              Hermes URL
            </label>
            <input
              value={hermesUrl}
              onChange={(e) => setHermesUrl(e.target.value)}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 font-mono text-xs"
            />

            <label className="mb-1 block text-[10px] uppercase text-slate-500">
              Hermes API Key
            </label>
            <input
              type="password"
              value={hermesKey}
              onChange={(e) => setHermesKey(e.target.value)}
              placeholder="writes API_SERVER_KEY to ~/.hermes/.env"
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 font-mono text-xs"
            />

            <label className="mb-1 block text-[10px] uppercase text-slate-500">
              OpenClaw WS URL
            </label>
            <input
              value={ocUrl}
              onChange={(e) => setOcUrl(e.target.value)}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 font-mono text-xs"
            />

            <label className="mb-1 block text-[10px] uppercase text-slate-500">
              OpenClaw Token
            </label>
            <input
              type="password"
              value={ocToken}
              onChange={(e) => setOcToken(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 font-mono text-xs"
            />
          </div>

          {saveNote && (
            <p className="text-[10px] text-emerald-600">{saveNote}</p>
          )}

          <button
            type="button"
            onClick={save}
            disabled={saving}
            className="w-full rounded-xl border border-cyan-800 bg-cyan-950/50 py-2 text-sm font-semibold text-cyan-300 hover:bg-cyan-900/40 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save to ~/.hermes"}
          </button>
        </div>
      </aside>
    </>
  );
}