import type { AlphaState } from "@/types/state";
import { usesTailscaleHttps } from "@/lib/secure-context";

const DEFAULT_BACKEND_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "9000";

/** Server-side / build-time backend URL for Next.js rewrites. */
export const INTERNAL_API_BASE =
  process.env.INTERNAL_API_URL ??
  `http://127.0.0.1:${DEFAULT_BACKEND_PORT}`;

function isBindOnlyUrl(url: string): boolean {
  return !url || /127\.0\.0\.1|localhost|0\.0\.0\.0/i.test(url);
}

/** HTTP API prefix — browser uses same-origin (Next.js or Tailscale HTTPS proxy). */
export function getHttpApiBase(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return INTERNAL_API_BASE.replace(/\/$/, "");
}

/** Direct backend URL for insecure HTTP / dev fallback. */
export function getApiBase(): string {
  if (typeof window !== "undefined") {
    if (usesTailscaleHttps() || window.isSecureContext) {
      return `${window.location.protocol}//${window.location.host}`;
    }
    const env = process.env.NEXT_PUBLIC_API_URL ?? "";
    if (isBindOnlyUrl(env)) {
      return `${window.location.protocol}//${window.location.hostname}:${DEFAULT_BACKEND_PORT}`;
    }
    return env.replace(/\/$/, "");
  }
  return INTERNAL_API_BASE.replace(/\/$/, "");
}

export function wsStateUrl(): string {
  if (typeof window !== "undefined") {
    if (usesTailscaleHttps() || window.isSecureContext) {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${window.location.host}/ws/state`;
    }
  }
  const base = getApiBase().replace(/^http/, "ws");
  return `${base}/ws/state`;
}

export async function fetchState(): Promise<AlphaState> {
  const res = await fetch(`${getHttpApiBase()}/api/state`, { cache: "no-store" });
  if (!res.ok) throw new Error(`State fetch failed: ${res.status}`);
  return res.json();
}

export async function sendCommand(command: string) {
  const res = await fetch(`${getHttpApiBase()}/api/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command }),
  });
  return res.json();
}

export async function fetchSettings() {
  const res = await fetch(`${getHttpApiBase()}/api/config`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Settings fetch failed: ${res.status}`);
  return res.json();
}

export async function postConfig(body: Record<string, string | undefined>) {
  const res = await fetch(`${getHttpApiBase()}/api/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Config save failed: ${res.status}`);
  return res.json();
}

export async function autodetectConfig() {
  const res = await fetch(`${getHttpApiBase()}/api/config/autodetect`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Auto-detect failed: ${res.status}`);
  return res.json();
}

export async function reloadConfig() {
  const res = await fetch(`${getHttpApiBase()}/api/config/reload`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Reload config failed: ${res.status}`);
  return res.json();
}

export async function reconnectRuntime() {
  const res = await fetch(`${getHttpApiBase()}/api/reconnect`, { method: "POST" });
  if (!res.ok) throw new Error(`Reconnect failed: ${res.status}`);
  return res.json();
}

export async function refreshMcp() {
  const res = await fetch(`${getHttpApiBase()}/api/mcp/refresh`, { method: "POST" });
  if (!res.ok) throw new Error(`MCP refresh failed: ${res.status}`);
  return res.json();
}

export async function callMcpTool(
  server: string,
  tool: string,
  toolArgs?: Record<string, unknown>
) {
  const res = await fetch(`${getHttpApiBase()}/api/mcp/call`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ server, tool, arguments: toolArgs ?? {} }),
  });
  if (!res.ok) throw new Error(`MCP call failed: ${res.status}`);
  return res.json();
}

export interface VoiceConfigPayload {
  wake_word?: string;
  browser_wake?: boolean;
  server_wake?: boolean;
  enabled?: boolean;
  grok_oauth?: boolean;
  hermes_profile?: string;
  model_provider?: string;
  model_default?: string;
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
  const res = await fetch(`${getHttpApiBase()}/api/voice/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Voice save failed: ${res.status}`);
  return res.json();
}

export async function fetchTtsAudio(
  text: string,
  provider?: string,
  voice?: string
): Promise<Blob | null> {
  const trimmed = text.trim();
  if (!trimmed) return null;

  const res = await fetch(`${getHttpApiBase()}/api/voice/tts`, {
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