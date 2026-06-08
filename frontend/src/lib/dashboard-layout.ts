export type WidgetId =
  | "metrics"
  | "capabilities"
  | "command"
  | "telemetry"
  | "tailscale"
  | "integrations"
  | "mcp_tools"
  | "mcp_data";

export type McpCategoryFilter = "all" | string;

export interface DashboardLayout {
  widgets: Record<WidgetId, boolean>;
  mcpCategories: McpCategoryFilter[];
}

const STORAGE_KEY = "alpha-os-dashboard-layout-v1";

export const WIDGET_LABELS: Record<WidgetId, { label: string; hint: string }> = {
  metrics: { label: "Metrics bar", hint: "Toolsets, skills, tools, MCP counts" },
  capabilities: { label: "Capabilities", hint: "Hermes toolsets, skills, sessions" },
  command: { label: "Command center", hint: "Voice + text commands" },
  telemetry: { label: "Telemetry", hint: "Live events and logs" },
  tailscale: { label: "Tailscale", hint: "Network status" },
  integrations: { label: "Integrations", hint: "Hermes / OpenClaw connection" },
  mcp_tools: { label: "MCP tool list", hint: "Every tool with online/offline status" },
  mcp_data: { label: "MCP live data", hint: "Human-readable data from your MCP servers" },
};

export const DEFAULT_LAYOUT: DashboardLayout = {
  widgets: {
    metrics: true,
    capabilities: true,
    command: true,
    telemetry: true,
    tailscale: true,
    integrations: true,
    mcp_tools: true,
    mcp_data: true,
  },
  mcpCategories: ["all"],
};

export function loadDashboardLayout(): DashboardLayout {
  if (typeof window === "undefined") return DEFAULT_LAYOUT;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_LAYOUT;
    const parsed = JSON.parse(raw) as Partial<DashboardLayout>;
    return {
      widgets: { ...DEFAULT_LAYOUT.widgets, ...parsed.widgets },
      mcpCategories: parsed.mcpCategories?.length
        ? parsed.mcpCategories
        : ["all"],
    };
  } catch {
    return DEFAULT_LAYOUT;
  }
}

export function saveDashboardLayout(layout: DashboardLayout): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
}