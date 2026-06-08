export interface AgentCard {
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
  toolsets?: number;
  skills: number;
  events_per_min: number;
  mcp_servers?: number;
  mcp_tools?: number;
}

export interface McpConfigPath {
  runtime: string;
  path: string;
  exists: boolean;
  key: string;
}

export interface McpServer {
  name: string;
  connected: boolean;
  transport?: string;
  probeable?: boolean;
  tool_count: number;
  tools?: { name: string; description?: string }[];
  error?: string | null;
  command?: string;
  args?: string[];
  command_preview?: string;
  env_keys?: string[];
  source?: string;
  config_path?: string;
  url?: string;
  auth?: string | null;
  note?: string;
  status?: string;
  tool_policy?: { include?: unknown; exclude?: unknown } | null;
}

export interface McpPanel {
  connected: boolean;
  server_count: number;
  stdio_count?: number;
  remote_count?: number;
  tool_count: number;
  servers: McpServer[];
  config_paths?: McpConfigPath[];
  sources?: string[];
  runtime?: string;
  error?: string | null;
  summary?: string | null;
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
  providers: VoiceProvider[];
}

export interface RuntimeStatus {
  installed: boolean;
  connected: boolean;
  gateway_url?: string;
  ws_url?: string;
}

export interface AlphaState {
  agents: AgentCard[];
  greeting: string;
  runtime: string;
  runtime_preference?: string;
  hermes_installed?: boolean;
  openclaw_installed?: boolean;
  runtimes?: {
    hermes: RuntimeStatus;
    openclaw: RuntimeStatus;
  };
  live?: boolean;
  hermes_connected: boolean;
  openclaw_connected: boolean;
  hermes?: { connected: boolean; gateway_url?: string };
  openclaw?: { connected: boolean; gateway_url?: string };
  metrics: Metrics;
  live_events: LiveEvent[];
  event_seq: number;
  orb_pulse: boolean;
  integrations: Integrations;
  mcp: McpPanel;
  tailscale: TailscaleStatus;
  memory?: { recent?: { who: string; text: string }[] };
  voice_config?: VoiceConfig;
}