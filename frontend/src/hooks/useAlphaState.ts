"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchState, reconnectRuntime, wsStateUrl } from "@/lib/api";
import { setRuntimeTailscaleHttps } from "@/lib/secure-context";
import type { AlphaState } from "@/types/state";

const EMPTY_METRICS: AlphaState["metrics"] = {
  sessions: 0,
  agents: 0,
  tools: 0,
  toolsets: 0,
  skills: 0,
  plugins: 0,
  events_per_min: 0,
};

const EMPTY_STATE: AlphaState = {
  agents: [],
  profile_agents: [],
  capabilities: [],
  greeting: "",
  runtime: "offline",
  hermes_installed: false,
  live: false,
  gateway_online: false,
  hermes_connected: false,
  openclaw_connected: false,
  metrics: EMPTY_METRICS,
  polymarket: {
    connected: false,
    pnl_today: null,
    open_positions: null,
    win_rate: null,
  },
  live_events: [],
  event_seq: 0,
  orb_pulse: false,
  integrations: { connected: false, toolsets: [], skills: [], sessions: [] },
  mcp: { connected: false, server_count: 0, tool_count: 0, servers: [] },
  tailscale: {
    available: false,
    backend_state: "unknown",
    connected: false,
    self_ip: null,
    hostname: null,
    dns_name: null,
    exit_node: null,
    uptime_sec: 0,
    downtime_sec: 0,
    peers: [],
    peer_count: 0,
    peers_online: 0,
  },
};

function pushHist(prev: Record<string, number[]>, key: string, value: number) {
  const hist = prev[key] ?? [];
  if (hist.length && hist[hist.length - 1] === value) return prev;
  const next = [...hist, value];
  if (next.length > 16) next.shift();
  return { ...prev, [key]: next };
}

type ApplyOptions = { force?: boolean };

function stateFingerprint(data: AlphaState): string {
  const m = data.metrics;
  return [
    data.event_seq ?? 0,
    data.live ? 1 : 0,
    data.gateway_online ? 1 : 0,
    data.hermes_connected ? 1 : 0,
    m?.toolsets ?? 0,
    m?.tools ?? 0,
    m?.skills ?? 0,
    data.capabilities?.length ?? data.agents?.length ?? 0,
    data.mcp?.tool_count ?? 0,
    data.mcp?.widgets?.length ?? 0,
    data.mcp?.tools_online ?? 0,
    data.voice_live?.tts_provider ?? "",
    data.voice_live?.session?.tts_requests ?? 0,
    data.voice_live?.session?.stt_requests ?? 0,
    data.voice_live?.session?.estimated_tokens ?? 0,
    ...(data.profile_agents ?? []).map(
      (p) => `${p.name}:${p.status}:${p.activity ?? ""}:${p.busy ? 1 : 0}`
    ),
    data.tailscale?.connected ? 1 : 0,
    data.tailscale?.backend_state ?? "",
    data.tailscale?.exit_node?.hostname ?? "",
    Math.floor(data.tailscale?.uptime_sec ?? 0),
    Math.floor(data.tailscale?.downtime_sec ?? 0),
  ].join(":");
}

export function useAlphaState() {
  const [state, setState] = useState<AlphaState>(EMPTY_STATE);
  const [loading, setLoading] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metricHistory, setMetricHistory] = useState<Record<string, number[]>>({});
  const [pulseKey, setPulseKey] = useState(0);
  const fingerprintRef = useRef("");
  const liveRef = useRef(false);

  const applyState = useCallback((data: AlphaState, opts?: ApplyOptions) => {
    const force = opts?.force ?? false;
    const fp = stateFingerprint(data);

    if (!force && fp === fingerprintRef.current) {
      return;
    }

    fingerprintRef.current = fp;
    liveRef.current = Boolean(data.live);
    setRuntimeTailscaleHttps(data.tailscale_https_url);

    setState(data);
    setConnected(Boolean(data.live));
    setError(null);

    if (data.orb_pulse) setPulseKey((k) => k + 1);

    const m = data.metrics;
    if (m && data.live) {
      setMetricHistory((prev) => {
        let next = prev;
        next = pushHist(next, "toolsets", m.toolsets ?? 0);
        next = pushHist(next, "skills", m.skills);
        next = pushHist(next, "tools", m.tools);
        next = pushHist(next, "plugins", m.plugins ?? 0);
        next = pushHist(next, "sessions", m.sessions);
        next = pushHist(next, "events", m.events_per_min);
        return next === prev ? prev : next;
      });
    }
  }, []);

  const reconnect = useCallback(async () => {
    try {
      setReconnecting(true);
      fingerprintRef.current = "";
      const reconnected = await reconnectRuntime();
      if (reconnected?.state) {
        applyState(reconnected.state, { force: true });
      } else {
        const data = await fetchState();
        applyState(data, { force: true });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reconnect failed");
    } finally {
      setReconnecting(false);
    }
  }, [applyState]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;
    let backoff = 2000;

    const connect = () => {
      if (cancelled) return;
      try {
        ws = new WebSocket(wsStateUrl());
        ws.onopen = () => {
          setError(null);
          backoff = 2000;
        };
        ws.onmessage = (ev) => {
          try {
            applyState(JSON.parse(ev.data as string));
          } catch {
            /* ignore */
          }
        };
        ws.onerror = () => setError("WebSocket error");
        ws.onclose = () => {
          timer = setTimeout(connect, backoff);
          backoff = Math.min(backoff * 1.5, 10000);
        };
      } catch (e) {
        setError(e instanceof Error ? e.message : "WS failed");
        timer = setTimeout(connect, backoff);
      }
    };

    setLoading(true);
    fetchState()
      .then((data) => applyState(data, { force: true }))
      .catch((e) => setError(e instanceof Error ? e.message : "API offline"))
      .finally(() => {
        setLoading(false);
        connect();
      });

    return () => {
      cancelled = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, [applyState]);

  return {
    state,
    loading,
    reconnecting,
    connected,
    error,
    reconnect,
    metricHistory,
    pulseKey,
  };
};