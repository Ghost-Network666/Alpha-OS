export interface AgentCard {
  id?: string;
  name: string;
  title?: string;
  status?: string;
  color?: string;
  tool_count?: number;
}

export interface CapabilityCard {
  id: string;
  kind: "toolset" | "skill" | "session" | "agent";
  name: string;
  title?: string;
  status?: string;
  color?: string;
  tool_count?: number;
}

export interface LiveEvent {
  seq: number;
  source: string;
  ts: number;
  summary: string;
}

export interface Metrics {
  sessions: number;
  agents: number;
  tools: number;
  toolsets: number;
  skills: number;
  plugins?: number;
  events_per_min: number;
}

export interface PolymarketMetrics {
  connected: boolean;
  server?: string;
  tool_count?: number;
  pnl_today: number | null;
  open_positions: number | null;
  win_rate: number | null;
}

export interface McpTool {
  name: string;
  description?: string;
  category?: string;
  human_label?: string;
  status?: "online" | "offline";
  issue?: string | null;
}

export interface McpCategory {
  name: string;
  online: number;
  offline: number;
  total: number;
}

export interface McpWidget {
  id: string;
  server: string;
  tool: string;
  category: string;
  title: string;
  summary: string;
  status: "ok" | "error" | "offline";
  issue?: string | null;
  fields: { label: string; value: string }[];
}

export interface McpServer {
  name: string;
  connected: boolean;
  transport?: string;
  tool_count: number;
  tools_online?: number;
  tools_offline?: number;
  tools?: McpTool[];
  categories?: McpCategory[];
  widgets?: McpWidget[];
  error?: string | null;
  command?: string;
  source?: string;
}

export interface McpPanel {
  connected: boolean;
  server_count: number;
  tool_count: number;
  servers_online?: number;
  servers_offline?: number;
  tools_online?: number;
  tools_offline?: number;
  servers: McpServer[];
  widgets?: McpWidget[];
  categories?: McpCategory[];
  sources?: string[];
  error?: string | null;
}

export interface Integrations {
  connected: boolean;
  runtime?: string;
  toolsets: { name?: string; label?: string; tools?: unknown[] }[];
  skills: { name?: string; description?: string }[];
  sessions: { id?: string; title?: string; model?: string; active?: boolean }[];
  error?: string | null;
}

export interface TailscaleStatus {
  available: boolean;
  backend_state: string;
  self_ip: string | null;
  hostname: string | null;
  peers: { hostname?: string; ip?: string; online?: boolean }[];
  error?: string | null;
}

export interface VoiceProvider {
  id: string;
  label: string;
  available: boolean;
  enabled: boolean;
  kind?: string;
  note?: string;
}

export interface VoiceConfig {
  wake_word: string;
  browser_wake: boolean;
  server_wake: boolean;
  enabled: boolean;
  browser_mic: boolean;
  grok_oauth: boolean;
  record_key: string;
  max_recording_seconds: number;
  auto_tts: boolean;
  beep_enabled: boolean;
  silence_threshold: number;
  silence_duration: number;
  stt_enabled: boolean;
  stt_provider: string;
  stt_model: string;
  tts_provider: string;
  tts_voice: string;
  hermes_config_path?: string;
  hermes_config_exists?: boolean;
  hermes_profile?: string;
  model_provider?: string;
  model_default?: string;
  providers: VoiceProvider[];
}

export interface AlphaState {
  agents: AgentCard[];
  capabilities?: CapabilityCard[];
  greeting: string;
  runtime: string;
  hermes_installed?: boolean;
  live?: boolean;
  gateway_online?: boolean;
  hermes_connected: boolean;
  openclaw_connected: boolean;
  hermes?: { connected: boolean; gateway_url?: string };
  openclaw?: { connected: boolean; gateway_url?: string };
  metrics: Metrics;
  polymarket: PolymarketMetrics;
  live_events: LiveEvent[];
  event_seq: number;
  orb_pulse: boolean;
  integrations: Integrations;
  mcp: McpPanel;
  tailscale: TailscaleStatus;
  memory?: { recent?: { who: string; text: string }[] };
  voice_config?: VoiceConfig;
  log_path?: string;
  tailscale_https_url?: string | null;
}