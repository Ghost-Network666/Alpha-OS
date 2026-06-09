"use client";

import { useCallback, useState } from "react";
import { reportVoiceUsage } from "@/lib/api";
import { CommandPanel } from "@/components/CommandPanel";
import { DashboardSkeleton } from "@/components/DashboardSkeleton";
import { GridBackground } from "@/components/GridBackground";
import { MicSecureBanner } from "@/components/MicSecureBanner";
import { SecureTailscaleRedirect } from "@/components/SecureTailscaleRedirect";
import { ClientLogger } from "@/components/ClientLogger";
import { TailscaleLiveBar } from "@/components/TailscaleLiveBar";
import { TopBar } from "@/components/TopBar";
import { useAlphaState } from "@/hooks/useAlphaState";
import { useDashboardLayout } from "@/hooks/useDashboardLayout";
import { useWakeWordListener } from "@/hooks/useWakeWordListener";
import { clientLog } from "@/lib/client-log";
import { micBlockedReason } from "@/lib/secure-context";
import {
  LazyCapabilitiesPanel,
  LazyConnectScreen,
  LazyMetricsBar,
  LazyProfileAgentsRow,
  LazySettingsDrawer,
  LazySidePanels,
  LazyTelemetryPanel,
  LazyViewCustomizer,
} from "@/lib/lazy-panels";
import { sendCommand } from "@/lib/api";
import { speakAlphaReply } from "@/lib/speech";
import type { CapabilityCard } from "@/types/state";

export default function DashboardPage() {
  const { state, loading, reconnecting, reconnect, metricHistory, pulseKey } =
    useAlphaState();
  const {
    layout,
    toggleWidget,
    toggleMcpCategory,
    isWidgetOn,
    mcpCategoryActive,
  } = useDashboardLayout();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [logs, setLogs] = useState<{ ts: string; who: string; msg: string }[]>(
    []
  );
  const [speaking, setSpeaking] = useState(false);
  const [lastVoiceActivity, setLastVoiceActivity] = useState<{
    kind: "tts" | "stt";
    chars: number;
  } | null>(null);

  const live = Boolean(state.live);
  const gatewayOnline = Boolean(
    state.gateway_online ?? state.hermes_connected ?? state.openclaw_connected
  );
  const capabilities: CapabilityCard[] = state.capabilities?.length
    ? state.capabilities
    : (state.agents ?? []).map((agent, index) => ({
        id: agent.id ?? `agent-${index}`,
        kind: "agent" as const,
        name: agent.name,
        title: agent.title,
        status: agent.status,
        color: agent.color,
        tool_count: agent.tool_count,
      }));
  const wakeWord = state.voice_config?.wake_word ?? "hey alpha";
  const browserWake = state.voice_config?.browser_wake ?? true;
  const autoTts = state.voice_config?.auto_tts ?? true;
  const ttsVoice = state.voice_config?.tts_voice ?? "en-US-AriaNeural";
  const ttsProvider = state.voice_config?.tts_provider;

  const speakReply = useCallback(
    (reply: string) => {
      if (!autoTts) return;
      const trimmed = reply.trim();
      if (!trimmed) return;
      setLastVoiceActivity({ kind: "tts", chars: trimmed.length });
      void speakAlphaReply(trimmed, {
        voiceHint: ttsVoice,
        provider: ttsProvider,
        onSpeakingChange: setSpeaking,
      });
    },
    [autoTts, ttsVoice, ttsProvider]
  );

  const onLog = useCallback(
    (msg: string, who = "system") => {
      if (!live) return;
      setLogs((prev) => [
        { ts: new Date().toLocaleTimeString(), who, msg },
        ...prev.slice(0, 79),
      ]);
    },
    [live]
  );

  const handleVoiceCommand = useCallback(
    async (command: string) => {
      const cmd = command.trim();
      if (!cmd || !live || !gatewayOnline) return;
      onLog(cmd, "you");
      setLastVoiceActivity({ kind: "stt", chars: cmd.length });
      void reportVoiceUsage({
        kind: "stt",
        provider: state.voice_live?.stt_provider ?? state.voice_config?.stt_provider,
        characters: cmd.length,
      });
      try {
        const res = await sendCommand(cmd);
        const reply = res.reply ?? "No response";
        onLog(reply, "alpha");
        speakReply(reply);
      } catch (e) {
        onLog(e instanceof Error ? e.message : "Voice command failed", "system");
      }
    },
    [
      live,
      gatewayOnline,
      onLog,
      speakReply,
      state.voice_live?.stt_provider,
      state.voice_config?.stt_provider,
    ]
  );

  const { status: wakeStatus, detail: wakeDetail } = useWakeWordListener({
    enabled: live && gatewayOnline && browserWake && isWidgetOn("command"),
    wakeWord,
    tailscaleHttpsUrl: state.tailscale_https_url,
    onWake: () => onLog("Wake phrase detected — listening for command", "voice"),
    onCommand: handleVoiceCommand,
    onStatus: (status, detail) => {
      if (status === "error" && detail && !detail.includes("HTTPS")) {
        onLog(detail, "system");
        clientLog("warning", detail, status, "telemetry");
      }
    },
  });

  const hasActivity =
    live &&
    (state.live_events.length > 0 || state.metrics.events_per_min > 0);

  const mcpCatFilter = useCallback(
    (category: string) => mcpCategoryActive(category),
    [mcpCategoryActive]
  );

  return (
    <div className="flex h-full min-h-screen flex-col">
      <ClientLogger />
      <SecureTailscaleRedirect tailscaleHttpsUrl={state.tailscale_https_url} />
      <GridBackground />

      {micBlockedReason(state.tailscale_https_url) && (
        <MicSecureBanner tailscaleHttpsUrl={state.tailscale_https_url} />
      )}

      <TopBar
        connected={live}
        runtime={state.runtime}
        hermesConnected={state.hermes_connected}
        gatewayOnline={gatewayOnline}
        openclawConnected={state.openclaw_connected}
        reconnecting={reconnecting}
        onReconnect={reconnect}
        onSettings={() => setSettingsOpen(true)}
        onCustomizeView={() => setViewOpen(true)}
      />

      <TailscaleLiveBar tailscale={state.tailscale} />

      {viewOpen && (
        <LazyViewCustomizer
          open={viewOpen}
          onClose={() => setViewOpen(false)}
          widgets={layout.widgets}
          mcpCategories={layout.mcpCategories}
          mcp={state.mcp}
          onToggleWidget={toggleWidget}
          onToggleMcpCategory={toggleMcpCategory}
        />
      )}

      {live && isWidgetOn("metrics") && (
        <>
          <LazyMetricsBar
            metrics={state.metrics}
            polymarket={state.polymarket}
            history={metricHistory}
            gatewayOnline={gatewayOnline}
            pulseKey={pulseKey}
          />
          <LazyProfileAgentsRow profiles={state.profile_agents ?? []} />
        </>
      )}

      {loading ? (
        <DashboardSkeleton />
      ) : !live ? (
        <LazyConnectScreen
          hermesInstalled={Boolean(state.hermes_installed)}
          openclawInstalled={
            Boolean(state.openclaw?.gateway_url) || state.openclaw_connected
          }
          hermesConnected={state.hermes_connected}
          openclawConnected={state.openclaw_connected}
          runtimePreference={state.runtime}
          onOpenSettings={() => setSettingsOpen(true)}
          onReconnect={reconnect}
        />
      ) : (
        <main className="dashboard-main grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] lg:grid-cols-12">
          <div
            className={`order-1 flex min-h-0 flex-col gap-3 ${
              isWidgetOn("capabilities") ? "lg:order-2 lg:col-span-6" : "lg:col-span-9"
            }`}
          >
            {isWidgetOn("command") && (
              <div className="shrink-0">
                <CommandPanel
                  greeting={state.greeting}
                  orbPulse={state.orb_pulse}
                  hasActivity={hasActivity}
                  wakeStatus={wakeStatus}
                  wakeDetail={wakeDetail}
                  wakeWord={wakeWord}
                  voiceLive={state.voice_live}
                  speaking={speaking}
                  lastVoiceActivity={lastVoiceActivity}
                  onLog={onLog}
                  onReply={speakReply}
                />
              </div>
            )}
            {isWidgetOn("telemetry") && (
              <div className="widget-panel min-h-[12rem] flex-1 lg:min-h-0">
                <LazyTelemetryPanel events={state.live_events} logs={logs} />
              </div>
            )}
          </div>

          {isWidgetOn("capabilities") && (
            <div className="widget-panel order-2 flex min-h-0 flex-col lg:order-1 lg:col-span-3">
              <LazyCapabilitiesPanel
                capabilities={capabilities}
                gatewayOnline={gatewayOnline}
              />
            </div>
          )}

          {(isWidgetOn("tailscale") ||
            isWidgetOn("integrations") ||
            isWidgetOn("mcp_tools") ||
            isWidgetOn("mcp_data")) && (
            <div className="widget-panel order-3 min-h-0 max-h-[50vh] lg:max-h-none lg:col-span-3">
              <LazySidePanels
                tailscale={state.tailscale}
                integrations={state.integrations}
                mcp={state.mcp}
                gatewayOnline={gatewayOnline}
                showTailscale={isWidgetOn("tailscale")}
                showIntegrations={isWidgetOn("integrations")}
                showMcpTools={isWidgetOn("mcp_tools")}
                showMcpData={isWidgetOn("mcp_data")}
                mcpCategoryFilter={mcpCatFilter}
                onMcpRefresh={() => reconnect()}
              />
            </div>
          )}
        </main>
      )}

      {settingsOpen && (
        <LazySettingsDrawer
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          runtime={state.runtime}
          live={live}
          voiceConfig={state.voice_config}
          onSaved={reconnect}
        />
      )}
    </div>
  );
}