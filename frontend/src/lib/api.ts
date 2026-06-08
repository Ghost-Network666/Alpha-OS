import type { AlphaState } from "@/types/state";
import { parseBootstrapWsUrl } from "@/lib/ws";

/** Same-origin — Next.js proxies /api/* to the backend using runtime dotenv */
export const API_BASE = "";

async function apiFetch(path: string, init: RequestInit = {}) {
  return fetch(`${API_BASE}${path}`, init);
}

let cachedWsUrl: string | null = null;

export function resetWsUrlCache(): void {
  cachedWsUrl = null;
}

export async function resolveWsUrl(): Promise<string> {
  if (cachedWsUrl) return cachedWsUrl;
  const res = await apiFetch("/api/bootstrap", { cache: "no-store" });
  if (!res.ok) throw new Error(`Bootstrap failed: ${res.status}`);
  const data = await res.json();
  cachedWsUrl = parseBootstrapWsUrl(data);
  return cachedWsUrl;
}

export function wsStateUrl(): string {
  if (cachedWsUrl) return cachedWsUrl;
  return "/api/bootstrap-pending";
}

export async function fetchState(): Promise<AlphaState> {
  const res = await apiFetch("/api/state", { cache: "no-store" });
  if (!res.ok) throw new Error(`State fetch failed: ${res.status}`);
  return res.json();
}

export async function sendCommand(command: string) {
  const res = await apiFetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command }),
  });
  return res.json();
}

export async function postConfig(body: Record<string, string | undefined>) {
  const res = await apiFetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function refreshMcp() {
  const res = await apiFetch("/api/mcp/refresh", { method: "POST" });
  return res.json();
}

export interface VoiceConfigPayload {
  wake_word?: string;
  browser_wake?: boolean;
  server_wake?: boolean;
  enabled?: boolean;
  grok_oauth?: boolean;
  record_key?: string;
  max_recording_seconds?: number;
  auto_tts?: boolean;
  beep_enabled?: boolean;
  silence_threshold?: number;
  silence_duration?: number;
  stt_enabled?: boolean;
  stt_provider?: string;
  stt_model?: string;
  tts_provider?: string;
  tts_voice?: string;
  provider_id?: string;
  provider_enabled?: boolean;
}

export async function postVoiceConfig(body: VoiceConfigPayload) {
  const res = await apiFetch("/api/voice/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function fetchTtsAudio(
  text: string,
  provider?: string,
  voice?: string
): Promise<Blob | null> {
  const trimmed = text.trim();
  if (!trimmed) return null;

  const res = await apiFetch("/api/voice/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: trimmed, provider, voice }),
  });

  const ctype = res.headers.get("content-type") ?? "";
  if (res.ok && ctype.startsWith("audio/")) {
    return res.blob();
  }
  return null;
}