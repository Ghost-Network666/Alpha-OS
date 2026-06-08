"use client";

import { useCallback, useEffect, useState } from "react";
import {
  DEFAULT_LAYOUT,
  type DashboardLayout,
  type McpCategoryFilter,
  type WidgetId,
  loadDashboardLayout,
  saveDashboardLayout,
} from "@/lib/dashboard-layout";

export function useDashboardLayout() {
  const [layout, setLayout] = useState<DashboardLayout>(DEFAULT_LAYOUT);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setLayout(loadDashboardLayout());
    setReady(true);
  }, []);

  const persist = useCallback((next: DashboardLayout) => {
    setLayout(next);
    saveDashboardLayout(next);
  }, []);

  const toggleWidget = useCallback(
    (id: WidgetId) => {
      persist({
        ...layout,
        widgets: { ...layout.widgets, [id]: !layout.widgets[id] },
      });
    },
    [layout, persist]
  );

  const setMcpCategories = useCallback(
    (categories: McpCategoryFilter[]) => {
      persist({
        ...layout,
        mcpCategories: categories.length ? categories : ["all"],
      });
    },
    [layout, persist]
  );

  const toggleMcpCategory = useCallback(
    (category: string) => {
      const current = layout.mcpCategories;
      if (category === "all") {
        setMcpCategories(["all"]);
        return;
      }
      const withoutAll = current.filter((c) => c !== "all");
      const has = withoutAll.includes(category);
      const next = has
        ? withoutAll.filter((c) => c !== category)
        : [...withoutAll, category];
      setMcpCategories(next.length ? next : ["all"]);
    },
    [layout.mcpCategories, setMcpCategories]
  );

  const isWidgetOn = useCallback(
    (id: WidgetId) => layout.widgets[id] !== false,
    [layout.widgets]
  );

  const mcpCategoryActive = useCallback(
    (category: string) => {
      const cats = layout.mcpCategories;
      return cats.includes("all") || cats.includes(category);
    },
    [layout.mcpCategories]
  );

  return {
    layout,
    ready,
    toggleWidget,
    toggleMcpCategory,
    setMcpCategories,
    isWidgetOn,
    mcpCategoryActive,
  };
}