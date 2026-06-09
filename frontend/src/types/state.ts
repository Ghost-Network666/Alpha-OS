export interface AgentCard {
  id?: string;
  name: string;
  title?: string;
  status?: string;
  color?: string;
  tool_count?: number;
}

export interface ProfileAgent {
  id: string;
  kind: "profile";
  name: string;
  title?: string;
  model?: string | null;
  provider?: string | null;
  status: "LIVE" | "ACTIVE" | "STANDBY" | string;
  active: boolean;
  color?: string;
  activity?: string | null;
  busy?: boolean;
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

export interface TailscaleExitNode {
  id?: string;
  hostname?: string;
  dns_name?: string;
  ip?: string | null;
  online?: boolean;
  active?: boolean;
  is_exit_node?: boolean;
}

export interface TailscalePeer {
  id?: string;
  hostname?: string;
  dns_name?: string;
  ip?: string | null;
  online?: boolean;
  active?: boolean;
  os?: string;
  is_exit_node?: boolean;
  exit_node_option?: boolean;
}

export interface TailscaleStatus {
  available: boolean;
  backend_state: string;
  online?: boolean;
  connected?: boolean;
  self_ip: string | null;
  hostname: string | null;
  dns_name?: string | null;
  version?: string | null;
  advertises_exit_node?: boolean;
  is_exit_node?: boolean;
  exit_node?: TailscaleExitNode | null;
  exit_node_id?: string | null;
  uptime_since?: number | null;
  downtime_since?: number | null;
  uptime_sec?: number;
  downtime_sec?: number;
  peers: TailscalePeer[];
  peer_count?: number;
  peers_online?: number;
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

export interface VoiceUsageSession {
  tts_requests: number;
  tts_characters: number;
  stt_requests: number;
  stt_characters: number;
  estimated_tokens: number;
  tts_estimated_tokens: number;
  stt_estimated_tokens: number;
  last_tts_provider?: string;
  last_stt_provider?: string;
  last_tts_chars?: number;
  last_stt_chars?: number;
}

export interface VoiceLive {
  active: boolean;
  auto_tts: boolean;
  stt_enabled: boolean;
  tts_provider: string;
  tts_provider_label: string;
  tts_voice: string;
  tts_model?: string;
  tts_local: boolean;
  stt_provider: string;
  stt_provider_label: string;
  stt_model?: string;
  stt_local: boolean;
  wake_word: string;
  hermes_profile?: string;
  session?: VoiceUsageSession;
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
  tts_model?: string;
  hermes_config_path?: string;
  hermes_config_exists?: boolean;
  hermes_profile?: string;
  model_provider?: string;
  model_default?: string;
  providers: VoiceProvider[];
}

export interface AlphaState {
  agents: AgentCard[];
  profile_agents?: ProfileAgent[];
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
  voice_live?: VoiceLive | null;
  log_path?: string;
  tailscale_https_url?: string | null;
}