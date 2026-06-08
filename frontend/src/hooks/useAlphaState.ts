"use client";

import { useCallback, useEffect, useState } from "react";
import { API_BASE, fetchState, resolveWsUrl } from "@/lib/api";
import type { AlphaState } from "@/types/state";

const EMPTY_METRICS: AlphaState["metrics"] = {
  sessions: 0,
  agents: 0,
  tools: 0,
  skills: 0,
  events_per_min: 0,
};

const EMPTY_STATE: AlphaState = {
  agents: [],
  greeting: "",
  runtime: "offline",
  hermes_installed: false,
  openclaw_installed: false,
  live: false,
  hermes_connected: false,
  openclaw_connected: false,
  metrics: EMPTY_METRICS,
  live_events: [],
  event_seq: 0,
  orb_pulse: false,
  integrations: { connected: false, toolsets: [], skills: [], sessions: [] },
  mcp: {
    connected: false,
    server_count: 0,
    stdio_count: 0,
    remote_count: 0,
    tool_count: 0,
    servers: [],
    summary: null,
  },
  tailscale: {
    available: false,
    backend_state: "unknown",
    self_ip: null,
    hostname: null,
    peers: [],
  },
};

function pushHist(prev: Record<string, number[]>, key: string, value: number) {
  const hist = [...(prev[key] ?? []), value];
  if (hist.length > 24) hist.shift();
  return { ...prev, [key]: hist };
}

export function useAlphaState() {
  const [state, setState] = useState<AlphaState>(EMPTY_STATE);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metricHistory, setMetricHistory] = useState<Record<string, number[]>>({});
  const [pulseKey, setPulseKey] = useState(0);

  const applyState = useCallback((data: AlphaState) => {
    setState(data);
    setConnected(Boolean(data.live));
    setError(null);
    if (!data.live) {
      setMetricHistory({});
      return;
    }
    if (data.orb_pulse) setPulseKey((k) => k + 1);
    const m = data.metrics;
    if (m) {
      setMetricHistory((prev) => {
        let next = prev;
        next = pushHist(next, "sessions", m.sessions);
        next = pushHist(next, "agents", m.agents);
        next = pushHist(next, "tools", m.tools);
        next = pushHist(next, "skills", m.skills);
        next = pushHist(next, "events", m.events_per_min);
        return next;
      });
    }
  }, []);

  const reconnect = useCallback(async () => {
    try {
      const data = await fetchState();
      applyState(data);
      await fetch(`${API_BASE}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reconnect failed");
    }
  }, [applyState]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;

    const connect = async () => {
      if (cancelled) return;
      try {
        const wsUrl = await resolveWsUrl();
        ws = new WebSocket(wsUrl);
        ws.onopen = () => setError(null);
        ws.onmessage = (ev) => {
          try {
            applyState(JSON.parse(ev.data));
          } catch {
            /* ignore */
          }
        };
        ws.onerror = () => setError("WebSocket error");
        ws.onclose = () => {
          timer = setTimeout(() => {
            void connect();
          }, 3000);
        };
      } catch (e) {
        setError(e instanceof Error ? e.message : "WS failed");
        timer = setTimeout(() => {
          void connect();
        }, 3000);
      }
    };

    fetchState()
      .then(applyState)
      .catch((e) => setError(e instanceof Error ? e.message : "API offline"))
      .finally(() => {
        void connect();
      });

    return () => {
      cancelled = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, [applyState]);

  return { state, connected, error, reconnect, metricHistory, pulseKey };
}