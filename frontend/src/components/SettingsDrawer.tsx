"use client";

import { useCallback, useEffect, useState } from "react";
import { AgentsSettingsTab } from "@/components/AgentsSettingsTab";
import { TerminalPanel } from "@/components/TerminalPanel";
import { Toggle } from "@/components/Toggle";
import {
  autodetectConfig,
  fetchElevenLabsVoices,
  fetchProfileVoice,
  fetchSettings,
  fetchSystemInfo,
  postConfig,
  postVoiceConfig,
  reloadConfig,
  systemReboot,
  type ElevenLabsVoice,
} from "@/lib/api";
import {
  EDGE_VOICES,
  ELEVENLABS_MODELS,
  MODEL_PROVIDERS,
  STT_MODELS,
  XAI_VOICES,
} from "@/lib/voice-options";
import type { VoiceConfig } from "@/types/state";

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
  runtime: string;
  live?: boolean;
  voiceConfig?: VoiceConfig;
  onSaved: () => void;
}

type SettingsTab =
  | "profiles"
  | "agents"
  | "voice"
  | "gateway"
  | "runtime"
  | "terminal";

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "profiles", label: "Profiles" },
  { id: "agents", label: "Agents" },
  { id: "voice", label: "Voice" },
  { id: "gateway", label: "Gateway" },
  { id: "runtime", label: "Runtime" },
  { id: "terminal", label: "Terminal" },
];

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
  tts_model: "eleven_multilingual_v2",
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
  const [ttsModel, setTtsModel] = useState("eleven_multilingual_v2");
  const [elevenlabsVoices, setElevenlabsVoices] = useState<ElevenLabsVoice[]>(
    []
  );
  const [elevenlabsVoicesLoading, setElevenlabsVoicesLoading] = useState(false);
  const [elevenlabsVoicesError, setElevenlabsVoicesError] = useState<
    string | null
  >(null);
  const [elevenlabsKey, setElevenlabsKey] = useState("");
  const [elevenlabsKeySet, setElevenlabsKeySet] = useState(false);
  const [elevenlabsKeyMasked, setElevenlabsKeyMasked] = useState<string | null>(
    null
  );
  const [modelProvider, setModelProvider] = useState("");
  const [modelDefault, setModelDefault] = useState("");
  const [saving, setSaving] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [saveNote, setSaveNote] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [tab, setTab] = useState<SettingsTab>("profiles");
  const [elevenSearch, setElevenSearch] = useState("");
  const [ubuntuReboot, setUbuntuReboot] = useState(false);
  const [rebooting, setRebooting] = useState(false);
  const [profileLoading, setProfileLoading] = useState(false);

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
    setTtsModel(merged.tts_model ?? "eleven_multilingual_v2");
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
      setElevenlabsKeySet(Boolean(cfg.elevenlabs?.api_key_set));
      setElevenlabsKeyMasked(cfg.elevenlabs?.api_key_masked ?? null);
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

  useEffect(() => {
    if (!open) return;
    void fetchSystemInfo()
      .then((info) => setUbuntuReboot(Boolean(info.reboot_available)))
      .catch(() => setUbuntuReboot(false));
  }, [open]);

  const loadProfileVoice = useCallback(
    async (profile: string) => {
      setProfileLoading(true);
      setSaveError(null);
      try {
        const res = await fetchProfileVoice(profile);
        if (res.voice) applyVoice(res.voice);
        if (res.voice?.hermes_config_path) setConfigPath(res.voice.hermes_config_path);
      } catch (e) {
        setSaveError(
          e instanceof Error ? e.message : `Failed to load profile “${profile}”`
        );
      } finally {
        setProfileLoading(false);
      }
    },
    [applyVoice]
  );

  useEffect(() => {
    if (!open || ttsProvider !== "elevenlabs") return;
    let cancelled = false;
    setElevenlabsVoicesLoading(true);
    setElevenlabsVoicesError(null);
    void fetchElevenLabsVoices(elevenSearch || undefined)
      .then((res) => {
        if (cancelled) return;
        if (!res.available) {
          setElevenlabsVoices([]);
          setElevenlabsVoicesError(
            res.error ?? "Set ELEVENLABS_API_KEY in Gateway tab"
          );
          return;
        }
        setElevenlabsVoices(res.voices ?? []);
      })
      .catch((e) => {
        if (cancelled) return;
        setElevenlabsVoices([]);
        setElevenlabsVoicesError(
          e instanceof Error ? e.message : "Failed to load voices"
        );
      })
      .finally(() => {
        if (!cancelled) setElevenlabsVoicesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, ttsProvider, elevenlabsKeySet, elevenSearch]);

  const elevenOptions = (() => {
    const opts = [...elevenlabsVoices];
    if (
      ttsVoice &&
      !opts.some((v) => v.voice_id === ttsVoice)
    ) {
      opts.unshift({
        voice_id: ttsVoice,
        name: ttsVoice,
        label: `${ttsVoice} (saved)`,
      });
    }
    return opts;
  })();

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
        elevenlabs_api_key: elevenlabsKey.trim() || undefined,
        openclaw_ws_url: ocUrl.trim() || undefined,
        openclaw_token: ocToken.trim() || undefined,
      });
      const voiceRes = await postVoiceConfig({
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
        tts_model: ttsProvider === "elevenlabs" ? ttsModel : undefined,
      });
      const path = voiceRes?.voice?.hermes_config_path ?? configPath;
      setConfigPath(path ?? null);
      const reload = voiceRes?.hermes_reload;
      const reloadNote =
        reload?.ok === true
          ? " · Hermes gateway reloaded"
          : reload?.hint
            ? ` · ${reload.hint}`
            : "";
      setSaveNote(
        path
          ? `Saved to ${path}${reloadNote}`
          : `Saved to profile “${hermesProfile}”${reloadNote}`
      );
      if (hermesKey.trim()) {
        setHermesKeySet(true);
        setHermesKey("");
      }
      if (elevenlabsKey.trim()) {
        setElevenlabsKeySet(true);
        setElevenlabsKey("");
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
        className={`fixed inset-y-0 right-0 z-50 w-[520px] max-w-[96vw] overflow-y-auto border-l border-cyan-900/30 bg-[#0d0d14] p-5 transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="mb-4 border-b border-slate-800/80 pb-4">
          <div className="mb-3 flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold tracking-[0.15em] text-[#00f5ff]">
                  ALPHA
                </span>
                <span className="text-base font-light tracking-[0.25em] text-slate-500">
                  OS
                </span>
              </div>
              <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Settings
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close settings"
              className="rounded-lg border border-slate-800 px-2 py-1 text-slate-500 hover:border-slate-600 hover:text-slate-300"
            >
              ✕
            </button>
          </div>
          <nav className="flex flex-wrap gap-1">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className={`rounded-lg px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide transition ${
                  tab === item.id
                    ? "border border-cyan-700/60 bg-cyan-950/40 text-cyan-300"
                    : "border border-transparent text-slate-500 hover:text-cyan-400"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="space-y-5 text-sm">
          {tab === "profiles" && (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
                Hermes profiles
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
              onChange={(e) => {
                const name = e.target.value;
                setHermesProfile(name);
                void loadProfileVoice(name);
              }}
              disabled={profileLoading}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1.5 text-xs disabled:opacity-60"
            >
              {(hermesProfiles.length ? hermesProfiles : [hermesProfile]).map(
                (p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                )
              )}
            </select>
            {profileLoading && (
              <p className="text-[10px] text-slate-600">Loading profile settings…</p>
            )}
            <p className="mt-2 text-[10px] text-slate-600">
              Switching profiles loads that profile&apos;s saved config. Click{" "}
              <strong className="font-normal text-cyan-600">Save</strong> to persist
              changes and set it as active.
            </p>
          </div>
          )}

          {tab === "agents" && (
            <AgentsSettingsTab
              activeProfile={hermesProfile}
              onProfileChange={(name) => {
                setHermesProfile(name);
                void loadProfileVoice(name);
              }}
              onError={setSaveError}
              onNote={setSaveNote}
            />
          )}

          {tab === "voice" && (
          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Voice & wake
            </div>

            <label className="mb-1 block text-[10px] text-slate-500">
              Wake phrase
            </label>
            <input
              value={wakeWord}
              onChange={(e) => setWakeWord(e.target.value)}
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
            />

            <div className="mb-3 space-y-1.5">
              <Toggle
                checked={browserWake}
                onChange={setBrowserWake}
                label="Browser wake"
                hint="Always-on phrase detection on HTTPS / localhost"
              />
              <Toggle
                checked={serverWake}
                onChange={setServerWake}
                label="Server mic wake"
                hint="Server listens for wake phrase (requires voice extras)"
              />
              <Toggle
                checked={grokOauth}
                onChange={setGrokOauth}
                label="Grok via X OAuth"
                hint="SuperGrok / X OAuth — not xAI API keys"
              />
            </div>

          <div className="mt-4">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Model (saved to Hermes profile)
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  Provider
                </label>
                <select
                  value={modelProvider}
                  onChange={(e) => setModelProvider(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
                >
                  <option value="">—</option>
                  {MODEL_PROVIDERS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                  {modelProvider &&
                    !MODEL_PROVIDERS.some((p) => p.id === modelProvider) && (
                      <option value={modelProvider}>{modelProvider}</option>
                    )}
                </select>
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

          <div className="mt-4">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Speech I/O
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

            <div className="mt-2 space-y-1.5">
              <Toggle checked={autoTts} onChange={setAutoTts} label="Auto TTS" />
              <Toggle
                checked={beepEnabled}
                onChange={setBeepEnabled}
                label="Record beeps"
              />
              <Toggle
                checked={sttEnabled}
                onChange={setSttEnabled}
                label="STT enabled"
              />
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
                {STT_MODELS[sttProvider]?.length ? (
                  <select
                    value={sttModel}
                    onChange={(e) => setSttModel(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                  >
                    {STT_MODELS[sttProvider].map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                    {!STT_MODELS[sttProvider].includes(sttModel) && sttModel && (
                      <option value={sttModel}>{sttModel}</option>
                    )}
                  </select>
                ) : (
                  <input
                    value={sttModel}
                    onChange={(e) => setSttModel(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                  />
                )}
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
                  <option value="piper">piper (local)</option>
                  <option value="kittentts">kittentts (local)</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] text-slate-500">
                  TTS voice
                </label>
                {ttsProvider === "xai" ? (
                  <select
                    value={ttsVoice}
                    onChange={(e) => setTtsVoice(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
                  >
                    {XAI_VOICES.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.label}
                      </option>
                    ))}
                    {!XAI_VOICES.some((v) => v.id === ttsVoice) && ttsVoice && (
                      <option value={ttsVoice}>{ttsVoice}</option>
                    )}
                  </select>
                ) : ttsProvider === "edge" ? (
                  <select
                    value={ttsVoice}
                    onChange={(e) => setTtsVoice(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
                  >
                    {EDGE_VOICES.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.label}
                      </option>
                    ))}
                    {!EDGE_VOICES.some((v) => v.id === ttsVoice) && ttsVoice && (
                      <option value={ttsVoice}>{ttsVoice}</option>
                    )}
                  </select>
                ) : ttsProvider === "elevenlabs" ? (
                  <>
                    <input
                      value={elevenSearch}
                      onChange={(e) => setElevenSearch(e.target.value)}
                      placeholder="Search voice library…"
                      className="mb-1 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
                    />
                    <select
                      value={ttsVoice}
                      onChange={(e) => setTtsVoice(e.target.value)}
                      className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
                    >
                      {elevenOptions.map((v) => (
                        <option key={v.voice_id} value={v.voice_id}>
                          {v.label}
                        </option>
                      ))}
                    </select>
                    <a
                      href="https://elevenlabs.io/voice-library"
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-[10px] text-cyan-600 hover:underline"
                    >
                      Browse ElevenLabs voice library →
                    </a>
                  </>
                ) : (
                  <input
                    value={ttsVoice}
                    onChange={(e) => setTtsVoice(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 font-mono text-xs"
                  />
                )}
                {ttsProvider === "elevenlabs" && elevenlabsVoicesLoading && (
                  <p className="mt-1 text-[10px] text-slate-600">
                    Loading voice library…
                  </p>
                )}
                {ttsProvider === "elevenlabs" && elevenlabsVoicesError && (
                  <p className="mt-1 text-[10px] text-amber-600">
                    {elevenlabsVoicesError}
                  </p>
                )}
              </div>
            </div>

            {ttsProvider === "elevenlabs" && (
              <div className="mt-2">
                <label className="mb-1 block text-[10px] text-slate-500">
                  ElevenLabs model
                </label>
                <select
                  value={ttsModel}
                  onChange={(e) => setTtsModel(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-2 py-1 text-xs"
                >
                  {ELEVENLABS_MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                  {!ELEVENLABS_MODELS.some((m) => m.id === ttsModel) && ttsModel && (
                    <option value={ttsModel}>{ttsModel}</option>
                  )}
                </select>
              </div>
            )}

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
          </div>
          )}

          {tab === "gateway" && (
          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Gateway connections
            </div>
            <label className="mb-1 block text-[10px] uppercase text-slate-500">
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
              ElevenLabs API key
            </label>
            <input
              type="password"
              value={elevenlabsKey}
              onChange={(e) => setElevenlabsKey(e.target.value)}
              placeholder={
                elevenlabsKeySet
                  ? `configured (${elevenlabsKeyMasked ?? "••••"}) — enter to replace`
                  : "writes ELEVENLABS_API_KEY to ~/.hermes/.env"
              }
              className="mb-2 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-2 font-mono text-xs"
            />
            <p className="mb-2 text-[10px] leading-relaxed text-slate-600">
              Powers ElevenLabs TTS and the voice library picker. Get a key at{" "}
              <a
                href="https://elevenlabs.io/"
                target="_blank"
                rel="noreferrer"
                className="text-cyan-600 hover:underline"
              >
                elevenlabs.io
              </a>
              .
            </p>

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
          )}

          {tab === "runtime" && (
          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
              Alpha OS runtime
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
            <p className="mt-3 text-[10px] leading-relaxed text-slate-600">
              Alpha OS reads live data from your Hermes or OpenClaw gateway.
              Use Gateway tab for API URLs and keys.
            </p>
            {ubuntuReboot && (
              <div className="mt-4 rounded-lg border border-rose-900/40 bg-rose-950/20 p-3">
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-rose-400">
                  Ubuntu server reboot
                </div>
                <p className="mb-2 text-[10px] text-slate-500">
                  Runs <code className="text-rose-300">sudo reboot</code> on this
                  VPS. Requires passwordless sudo.
                </p>
                <button
                  type="button"
                  disabled={rebooting}
                  onClick={async () => {
                    if (
                      !window.confirm(
                        "Reboot this Ubuntu server now? All services will restart."
                      )
                    ) {
                      return;
                    }
                    setRebooting(true);
                    setSaveError(null);
                    try {
                      await systemReboot();
                      setSaveNote("Reboot initiated — reconnect shortly");
                    } catch (e) {
                      setSaveError(
                        e instanceof Error ? e.message : "Reboot failed"
                      );
                    } finally {
                      setRebooting(false);
                    }
                  }}
                  className="w-full rounded-lg border border-rose-800 bg-rose-950/40 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-900/30 disabled:opacity-50"
                >
                  {rebooting ? "Rebooting…" : "Reboot server (Ubuntu)"}
                </button>
              </div>
            )}
          </div>
          )}

          {tab === "terminal" && (
            <TerminalPanel
              profiles={hermesProfiles.length ? hermesProfiles : [hermesProfile]}
              defaultProfile={hermesProfile}
            />
          )}

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
            {saving ? "Saving…" : "Save Alpha OS settings"}
          </button>
        </div>
      </aside>
    </>
  );
}