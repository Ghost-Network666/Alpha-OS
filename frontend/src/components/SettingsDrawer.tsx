"use client";

import { useCallback, useEffect, useState } from "react";
import {
  autodetectConfig,
  fetchSettings,
  postConfig,
  postVoiceConfig,
  reloadConfig,
} from "@/lib/api";
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
  const [hermesKeySet, setHermesKeySet] = useState(false);
  const [hermesKeyMasked, setHermesKeyMasked] = useState<string | null>(null);
  const [hermesProfile, setHermesProfile] = useState("default");
  const [hermesProfiles, setHermesProfiles] = useState<string[]>([]);
  const [configPath, setConfigPath] = useState<string | null>(null);
  const [ocUrl, setOcUrl] = useState("ws://127.0.0.1:18789");
  const [ocToken, setOcToken] = useState("");
  const [rt, setRt] = useState("auto");
  const [wakeWord, setWakeWord] = useState(DEFAULT_VOICE.wake_word!);
  const [browserWake, setBrowserWake] = useState(true);
  const [serverWake, setServerWake] = useState(false);
  const [grokOauth, setGrokOauth] = useState(true);
  const [recordKey, setRecordKey] = useState(DEFAULT_VOICE.record_key!);
  const [maxRecording, setMaxRecording] = useState(120);
  const [autoTts, setAutoTts] = useState(true);
  const [beepEnabled, setBeepEnabled] = useState(true);
  const [silenceThreshold, setSilenceThreshold] = useState(200);
  const [silenceDuration, setSilenceDuration] = useState(3.0);
  const [sttEnabled, setSttEnabled] = useState(true);
  const [sttProvider, setSttProvider] = useState("local");
  const [sttModel, setSttModel] = useState("base");
  const [ttsProvider, setTtsProvider] = useState("edge");
  const [ttsVoice, setTtsVoice] = useState("en-US-AriaNeural");
  const [modelProvider, setModelProvider] = useState("");
  const [modelDefault, setModelDefault] = useState("");
  const [saving, setSaving] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [saveNote, setSaveNote] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const applyVoice = useCallback((v: Partial<VoiceConfig>) => {
    const merged = { ...DEFAULT_VOICE, ...v };
    setWakeWord(merged.wake_word ?? "hey alpha");
    setBrowserWake(merged.browser_wake ?? true);
    setServerWake(merged.server_wake ?? merged.enabled ?? false);
    setGrokOauth(merged.grok_oauth ?? true);
    setRecordKey(merged.record_key ?? "ctrl+b");
    setMaxRecording(merged.max_recording_seconds ?? 120);
    setAutoTts(merged.auto_tts ?? true);
    setBeepEnabled(merged.beep_enabled ?? true);
    setSilenceThreshold(merged.silence_threshold ?? 200);
    setSilenceDuration(merged.silence_duration ?? 3.0);
    setSttEnabled(merged.stt_enabled ?? true);
    setSttProvider(merged.stt_provider ?? "local");
    setSttModel(merged.stt_model ?? "base");
    setTtsProvider(merged.tts_provider ?? "edge");
    setTtsVoice(merged.tts_voice ?? "en-US-AriaNeural");
    setModelProvider(merged.model_provider ?? "");
    setModelDefault(merged.model_default ?? "");
    if (merged.hermes_profile) setHermesProfile(merged.hermes_profile);
    if (merged.hermes_config_path) setConfigPath(merged.hermes_config_path);
  }, []);

  const loadSettings = useCallback(async () => {
    setSaveError(null);
    try {
      const cfg = await fetchSettings();
      if (cfg.runtime) setRt(cfg.runtime);
      if (cfg.hermes?.gateway_url) setHermesUrl(cfg.hermes.gateway_url);
      if (cfg.hermes?.profiles?.length) setHermesProfiles(cfg.hermes.profiles);
      if (cfg.hermes?.profile) setHermesProfile(cfg.hermes.profile);
      if (cfg.hermes?.config_path) setConfigPath(cfg.hermes.config_path);
      setHermesKeySet(Boolean(cfg.hermes?.api_key_set));
      setHermesKeyMasked(cfg.hermes?.api_key_masked ?? null);
      if (cfg.openclaw?.ws_url) setOcUrl(cfg.openclaw.ws_url);
      applyVoice(cfg.voice_live ?? voiceConfig ?? {});
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to load settings");
      applyVoice(voiceConfig ?? {});
    }
  }, [applyVoice, voiceConfig]);

  useEffect(() => {
    if (!open) return;
    setSaveNote(null);
    setSaveError(null);
    void loadSettings();
  }, [open, loadSettings]);

  const autodetect = async () => {
    setDetecting(true);
    setSaveError(null);
    try {
      const res = await autodetectConfig();
      if (res.config) {
        const cfg = res.config;
        if (cfg.runtime) setRt(cfg.runtime);
        if (cfg.hermes?.gateway_url) setHermesUrl(cfg.hermes.gateway_url);
        if (cfg.hermes?.profiles?.length) setHermesProfiles(cfg.hermes.profiles);
        if (cfg.hermes?.profile) setHermesProfile(cfg.hermes.profile);
        if (cfg.hermes?.config_path) setConfigPath(cfg.hermes.config_path);
        applyVoice(cfg.voice_live ?? {});
        setHermesKeySet(Boolean(cfg.hermes?.api_key_set));
        setHermesKeyMasked(cfg.hermes?.api_key_masked ?? null);
        if (cfg.openclaw?.ws_url) setOcUrl(cfg.openclaw.ws_url);
      }
      setSaveNote("Re-detected from ~/.hermes and ~/.openclaw");
      onSaved();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Auto-detect failed");
    } finally {
      setDetecting(false);
    }
  };

  const reload = async () => {
    setReloading(true);
    setSaveError(null);
    try {
      const res = await reloadConfig();
      if (res.config) {
        const cfg = res.config;
        if (cfg.runtime) setRt(cfg.runtime);
        if (cfg.hermes?.config_path) setConfigPath(cfg.hermes.config_path);
        if (cfg.hermes?.profile) setHermesProfile(cfg.hermes.profile);
        applyVoice(cfg.voice_live ?? {});
      }
      const path =
        res.config?.hermes?.config_path ??
        res.voice?.hermes_config_path ??
        configPath;
      setSaveNote(path ? `Reloaded from ${path}` : "Config reloaded from disk");
      onSaved();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Reload failed");
    } finally {
      setReloading(false);
    }
  };

  const save = async () => {
    setSaving(true);
    setSaveNote(null);
    setSaveError(null);
    try {
      await postConfig({
        runtime: rt,
        hermes_gateway_url: hermesUrl.trim() || undefined,
        hermes_api_key: hermesKey.trim() || undefined,
        openclaw_ws_url: ocUrl.trim() || undefined,
        openclaw_token: ocToken.trim() || undefined,
      });
      const res = await postVoiceConfig({
        hermes_profile: hermesProfile,
        wake_word: wakeWord.trim() || "hey alpha",
        browser_wake: browserWake,
        server_wake: serverWake,
        grok_oauth: grokOauth,
        model_provider: modelProvider.trim() || undefined,
        model_default: modelDefault.trim() || undefined,
        record_key: recordKey.trim() || "ctrl+b",
        max_recording_seconds: maxRecording,
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
      const path = res?.voice?.hermes_config_path ?? configPath;
      setConfigPath(path ?? null);
      setSaveNote(path ? `Saved to ${path}` : "Saved to active Hermes profile");
      if (hermesKey.trim()) {
        setHermesKeySet(true);
        setHermesKey("");
      }
      onSaved();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
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
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
                Hermes profile
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={reload}
                  disabled={reloading || detecting}
                  className="text-[10px] font-semibold uppercase tracking-wide text-cyan-600 hover:text-cyan-400 disabled:opacity-50"
                >
                  {reloading ? "Reloading…" : "Reload config"}
                </button>
                <button
                  type="button"
                  onClick={autodetect}
                  disabled={detecting || reloading}
                  className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 hover:text-cyan-400 disabled:opacity-50"
                >
                  {detecting ? "Detecting…" : "Re-detect"}
                </button>
              </div>
            </div>
            <p className="mb-2 text-[10px] leading-relaxed text-slate-600">
              Auto-detected from{" "}
              <code className="text-cyan-700">~/.hermes</code>. Edits save to{" "}
              <code className="break-all text-cyan-700">
                {configPath ?? "~/.hermes/profiles/.../config.yaml"}
              </code>
              .
            </p>
            <select
              value={hermesProfile}
              onChange={(e) => setHermesProfile(e.target.value)}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1.5 text-xs"
            >
              {(hermesProfiles.length ? hermesProfiles : [hermesProfile]).map(
                (p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                )
              )}
            </select>
          </div>

          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Voice — Alpha OS
            </div>

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
              Browser always-on wake (HTTPS / localhost)
            </label>

            <label className="mb-2 flex items-center gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={serverWake}
                onChange={(e) => setServerWake(e.target.checked)}
                className="accent-cyan-500"
              />
              Server mic wake
            </label>

            <label className="mb-3 flex items-center gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={grokOauth}
                onChange={(e) => setGrokOauth(e.target.checked)}
                className="accent-cyan-500"
              />
              Grok via X OAuth / SuperGrok
            </label>
          </div>

          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Hermes model
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  Provider
                </label>
                <input
                  value={modelProvider}
                  onChange={(e) => setModelProvider(e.target.value)}
                  placeholder="xai-oauth"
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  Default model
                </label>
                <input
                  value={modelDefault}
                  onChange={(e) => setModelDefault(e.target.value)}
                  placeholder="grok-4.3"
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                />
              </div>
            </div>
          </div>

          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Hermes voice (gateway)
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
                  Max record (s)
                </label>
                <input
                  type="number"
                  min={30}
                  max={600}
                  value={maxRecording}
                  onChange={(e) =>
                    setMaxRecording(parseInt(e.target.value, 10) || 120)
                  }
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                />
              </div>
            </div>

            <div className="mt-2 grid grid-cols-2 gap-2">
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
            </div>

            <div className="mt-2 flex flex-wrap gap-3">
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
              <label className="flex items-center gap-2 text-[10px] text-slate-400">
                <input
                  type="checkbox"
                  checked={sttEnabled}
                  onChange={(e) => setSttEnabled(e.target.checked)}
                  className="accent-cyan-500"
                />
                STT enabled
              </label>
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
                  <option value="mistral">mistral</option>
                  <option value="elevenlabs">elevenlabs</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  STT model
                </label>
                <input
                  value={sttModel}
                  onChange={(e) => setSttModel(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
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
                  <option value="mistral">mistral</option>
                  <option value="piper">piper</option>
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
                <div className="text-[10px] uppercase text-slate-500">Status</div>
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
              Hermes API URL
            </label>
            <input
              value={hermesUrl}
              onChange={(e) => setHermesUrl(e.target.value)}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 font-mono text-xs"
            />

            <label className="mb-1 block text-[10px] uppercase text-slate-500">
              Hermes API key
            </label>
            <input
              type="password"
              value={hermesKey}
              onChange={(e) => setHermesKey(e.target.value)}
              placeholder={
                hermesKeySet
                  ? `configured (${hermesKeyMasked ?? "••••"}) — enter to replace`
                  : "writes API_SERVER_KEY to ~/.hermes/.env"
              }
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
              OpenClaw token
            </label>
            <input
              type="password"
              value={ocToken}
              onChange={(e) => setOcToken(e.target.value)}
              placeholder="optional — saves to ~/.alpha-os/config.yaml"
              className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 font-mono text-xs"
            />
          </div>

          {saveNote && (
            <p className="text-[10px] text-emerald-600">{saveNote}</p>
          )}
          {saveError && (
            <p className="text-[10px] text-rose-500">{saveError}</p>
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