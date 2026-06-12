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
import { Sidebar, ViewKey } from "@/components/Sidebar";
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
import { ConfigView } from "@/components/views/ConfigView";
import { KeysView } from "@/components/views/KeysView";

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
  const [currentView, setCurrentView] = useState<ViewKey>("command");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const handleViewChange = (view: ViewKey) => {
    setCurrentView(view);
    setMobileNavOpen(false); // close drawer on mobile after selection
  };
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

  const renderView = (view: ViewKey) => {
    switch (view) {
      case "command":
        return (
          <div className="space-y-3">
            {isWidgetOn("metrics") && (
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
            {isWidgetOn("command") && (
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
            )}
            {isWidgetOn("telemetry") && (
              <div className="widget-panel min-h-[12rem] flex-1 lg:min-h-0">
                <LazyTelemetryPanel events={state.live_events} logs={logs} />
              </div>
            )}
          </div>
        );
      case "agents":
        return (
          <div className="space-y-3">
            {isWidgetOn("metrics") && (
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
            {isWidgetOn("capabilities") && (
              <LazyCapabilitiesPanel
                capabilities={capabilities}
                gatewayOnline={gatewayOnline}
              />
            )}
          </div>
        );
      case "mcp":
        return (
          <LazySidePanels
            tailscale={state.tailscale}
            integrations={state.integrations}
            mcp={state.mcp}
            gatewayOnline={gatewayOnline}
            showTailscale={false}
            showIntegrations={false}
            showMcpTools={isWidgetOn("mcp_tools")}
            showMcpData={isWidgetOn("mcp_data")}
            mcpCategoryFilter={mcpCatFilter}
            onMcpRefresh={() => reconnect()}
          />
        );
      case "config":
        return (
          <ConfigView
            voiceConfig={state.voice_config}
            runtime={state.runtime}
            live={live}
            onSaved={reconnect}
          />
        );
      case "keys":
        return <KeysView />;
      case "telemetry":
        return (
          <div className="widget-panel min-h-[12rem] flex-1 lg:min-h-0">
            <LazyTelemetryPanel events={state.live_events} logs={logs} />
          </div>
        );
      default:
        return (
          <div className="p-8 text-center text-slate-400">
            View &quot;{view}&quot; coming soon. Use the sidebar to explore other sections.
          </div>
        );
    }
  };

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

      {/* Mobile nav trigger */}
      <button
        onClick={() => setMobileNavOpen(true)}
        className="fixed bottom-4 left-4 z-50 lg:hidden rounded-full bg-[#0a0a0f] border border-cyan-900/30 p-3 text-[#00f5ff] shadow-lg"
        aria-label="Open navigation menu"
      >
        ☰
      </button>

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

      {/* Metrics and profile row are now included inside specific views (command/agents) for better layout spreading */}

      {loading ? (
        <DashboardSkeleton />
      ) : !live ? (
        <div className="flex min-h-0 flex-1">
          <Sidebar
            currentView={currentView}
            onViewChange={handleViewChange}
            mobileOpen={mobileNavOpen}
            onCloseMobile={() => setMobileNavOpen(false)}
          />
          <div className="flex-1 min-h-0 overflow-auto p-3">
            {currentView === "command" ? (
              <>
                <div className="mb-4 p-3 rounded border border-amber-800 bg-amber-950/20 text-sm text-amber-300">
                  First-run setup recommended — switch to <strong>Config</strong> view in sidebar for the guided wizard (runtime choice, permissions, MCP, Kabal agents &amp; heartbeats).
                </div>
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
              </>
            ) : (
              renderView(currentView)
            )}
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1">
          <Sidebar
            currentView={currentView}
            onViewChange={handleViewChange}
            mobileOpen={mobileNavOpen}
            onCloseMobile={() => setMobileNavOpen(false)}
          />
          <div className="flex-1 min-h-0 overflow-auto p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            {renderView(currentView)}
          </div>
        </div>
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