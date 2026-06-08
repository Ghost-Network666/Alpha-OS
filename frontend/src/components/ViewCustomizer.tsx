"use client";

import { WIDGET_LABELS, type WidgetId } from "@/lib/dashboard-layout";
import type { McpPanel } from "@/types/state";

interface ViewCustomizerProps {
  open: boolean;
  onClose: () => void;
  widgets: Record<WidgetId, boolean>;
  mcpCategories: string[];
  mcp?: McpPanel;
  onToggleWidget: (id: WidgetId) => void;
  onToggleMcpCategory: (category: string) => void;
}

const WIDGET_ORDER: WidgetId[] = [
  "metrics",
  "capabilities",
  "command",
  "telemetry",
  "tailscale",
  "integrations",
  "mcp_tools",
  "mcp_data",
];

export function ViewCustomizer({
  open,
  onClose,
  widgets,
  mcpCategories,
  mcp,
  onToggleWidget,
  onToggleMcpCategory,
}: ViewCustomizerProps) {
  const categories = mcp?.categories ?? [];

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/60 transition ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-80 max-w-[92vw] overflow-y-auto border-r border-cyan-900/30 bg-[#0d0d14] p-5 transition-transform duration-300 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-5 flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-cyan-400">
            Customize view
          </span>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-300">
            ✕
          </button>
        </div>

        <p className="mb-4 text-[11px] leading-relaxed text-slate-500">
          Turn widgets on or off. Your layout is saved in this browser — each user
          can choose what they want to read.
        </p>

        <div className="mb-6 space-y-2">
          <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-600">
            Dashboard widgets
          </div>
          {WIDGET_ORDER.map((id) => {
            const meta = WIDGET_LABELS[id];
            const on = widgets[id] !== false;
            return (
              <label
                key={id}
                className="flex cursor-pointer items-start gap-2 rounded-lg border border-slate-800/80 bg-[#0a0a0f]/50 px-3 py-2"
              >
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() => onToggleWidget(id)}
                  className="mt-0.5 accent-cyan-500"
                />
                <span>
                  <span className="block text-xs text-slate-300">{meta.label}</span>
                  <span className="block text-[10px] text-slate-600">{meta.hint}</span>
                </span>
              </label>
            );
          })}
        </div>

        {categories.length > 0 && (
          <div className="space-y-2">
            <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-600">
              MCP categories
            </div>
            <p className="text-[10px] text-slate-600">
              Filter which MCP tool groups appear in the tool list and data widgets.
            </p>
            <button
              type="button"
              onClick={() => onToggleMcpCategory("all")}
              className={`mr-1 rounded-md px-2 py-0.5 text-[9px] font-semibold uppercase ${
                mcpCategories.includes("all")
                  ? "bg-cyan-950/80 text-cyan-400"
                  : "text-slate-600 hover:text-slate-400"
              }`}
            >
              All
            </button>
            {categories.map((c) => (
              <button
                key={c.name}
                type="button"
                onClick={() => onToggleMcpCategory(c.name)}
                className={`mr-1 mt-1 rounded-md px-2 py-0.5 text-[9px] font-semibold uppercase ${
                  mcpCategories.includes("all") || mcpCategories.includes(c.name)
                    ? "bg-cyan-950/80 text-cyan-400"
                    : "text-slate-600 hover:text-slate-400"
                }`}
              >
                {c.name} ({c.online}/{c.total})
              </button>
            ))}
          </div>
        )}
      </aside>
    </>
  );
}