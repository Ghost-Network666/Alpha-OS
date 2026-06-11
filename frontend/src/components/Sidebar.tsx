"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  PanelLeftClose,
  PanelLeftOpen,
  X,
  Terminal,
  Users,
  Plug,
  Settings,
  KeyRound,
  Activity,
  Package,
  MessageSquare,
  Wrench,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";

export type ViewKey =
  | "command"
  | "agents"
  | "mcp"
  | "config"
  | "keys"
  | "telemetry"
  | "skills"
  | "sessions"
  | "system";

export interface NavItem {
  key: ViewKey;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  group?: string;
}

const NAV_ITEMS: NavItem[] = [
  { key: "command", label: "Command Center", icon: Terminal },
  { key: "agents", label: "Agents", icon: Users, group: "core" },
  { key: "mcp", label: "MCP", icon: Plug, group: "core" },
  { key: "config", label: "Config", icon: Settings, group: "admin" },
  { key: "keys", label: "Keys & Env", icon: KeyRound, group: "admin" },
  { key: "telemetry", label: "Telemetry & Logs", icon: Activity, group: "monitor" },
  { key: "skills", label: "Skills", icon: Package, group: "admin" },
  { key: "sessions", label: "Sessions", icon: MessageSquare, group: "monitor" },
  { key: "system", label: "System", icon: Wrench, group: "admin" },
];

const SIDEBAR_COLLAPSED_KEY = "alpha-sidebar-collapsed";

interface SidebarProps {
  currentView: ViewKey;
  onViewChange: (view: ViewKey) => void;
  onCloseMobile?: () => void;
  mobileOpen?: boolean;
}

export function Sidebar({ currentView, onViewChange, onCloseMobile, mobileOpen = false }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true";
    } catch {
      return false;
    }
  });

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const isMobile = typeof window !== "undefined" && window.innerWidth < 1024;
  const showCollapsed = collapsed && !isMobile;

  // Close on escape for mobile
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && onCloseMobile) onCloseMobile();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileOpen, onCloseMobile]);

  const handleNav = (key: ViewKey) => {
    onViewChange(key);
    if (onCloseMobile) onCloseMobile();
  };

  return (
    <aside
      className={cn(
        "fixed top-0 left-0 z-50 flex h-dvh w-64 flex-col border-r border-slate-800/70 bg-[#0a0a0f]/95 backdrop-blur-md",
        "transition-[transform,width] duration-200 ease-out lg:sticky lg:top-0 lg:h-dvh lg:shrink-0",
        mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        showCollapsed && "lg:w-14"
      )}
      aria-label="Main navigation"
    >
      {/* Header */}
      <div
        className={cn(
          "flex h-14 shrink-0 items-center gap-2 border-b border-slate-800/70 px-3",
          showCollapsed ? "lg:justify-center" : "justify-between"
        )}
      >
        <div className={cn("flex items-center gap-2", showCollapsed && "lg:hidden")}>
          <div className="flex items-center gap-1.5">
            <Zap className="h-4 w-4 text-[#00f5ff]" />
            <span className="text-sm font-semibold tracking-[0.15em] text-[#00f5ff]">ALPHA</span>
            <span className="text-sm font-light tracking-[0.2em] text-slate-500">OS</span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={onCloseMobile}
            className="lg:hidden"
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={toggleCollapsed}
            className="hidden lg:flex"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Nav */}
      <nav className="min-h-0 flex-1 overflow-y-auto py-2 text-sm">
        <ul className="flex flex-col">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.key;

            return (
              <li key={item.key}>
                <button
                  onClick={() => handleNav(item.key)}
                  className={cn(
                    "group relative flex w-full items-center gap-3 px-4 py-2 text-left transition-colors",
                    "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#00f5ff]/40",
                    isActive
                      ? "text-[#00f5ff] bg-white/5"
                      : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                  )}
                  aria-current={isActive ? "page" : undefined}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span
                    className={cn(
                      "truncate transition-opacity",
                      showCollapsed ? "lg:opacity-0 lg:pointer-events-none" : "lg:opacity-100"
                    )}
                  >
                    {item.label}
                  </span>

                  {/* Active indicator - left accent bar */}
                  {isActive && (
                    <span className="absolute left-0 top-1 bottom-1 w-px bg-[#00f5ff]" />
                  )}

                  {/* Hover wash */}
                  <span
                    aria-hidden
                    className="absolute inset-y-0.5 left-1.5 right-1.5 bg-[#00f5ff] opacity-0 pointer-events-none transition-opacity duration-150 group-hover:opacity-[0.04]"
                  />
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer status-ish */}
      <div className={cn("shrink-0 border-t border-slate-800/70 p-3 text-[10px] text-slate-500", showCollapsed && "lg:hidden")}>
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-[#00ff88]" />
          <span>Alpha OS • Hermes powered</span>
        </div>
      </div>

      {/* Collapsed tooltips host (simple) */}
      {showCollapsed && (
        <div className="hidden lg:block" />
      )}
    </aside>
  );
}

export const VIEWS = NAV_ITEMS;
