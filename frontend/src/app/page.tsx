"use client";

import { useCallback, useState } from "react";
import { CapabilitiesPanel } from "@/components/CapabilitiesPanel";
import { CommandPanel } from "@/components/CommandPanel";
import { ConnectScreen } from "@/components/ConnectScreen";
import { LoadingScreen } from "@/components/LoadingScreen";
import { GridBackground } from "@/components/GridBackground";
import { MetricsBar } from "@/components/MetricsBar";
import { ProfileAgentsRow } from "@/components/ProfileAgentsRow";
import { SettingsDrawer } from "@/components/SettingsDrawer";
import { SidePanels } from "@/components/SidePanels";
import { ViewCustomizer } from "@/components/ViewCustomizer";
import { ClientLogger } from "@/components/ClientLogger";
import { MicSecureBanner } from "@/components/MicSecureBanner";
import { SecureTailscaleRedirect } from "@/components/SecureTailscaleRedirect";
import { micBlockedReason } from "@/lib/secure-context";
import { TelemetryPanel } from "@/components/TelemetryPanel";
import { TopBar } from "@/components/TopBar";
import { useAlphaState } from "@/hooks/useAlphaState";
import { useDashboardLayout } from "@/hooks/useDashboardLayout";
import { useWakeWordListener } from "@/hooks/useWakeWordListener";
import { clientLog } from "@/lib/client-log";
import { sendCommand } from "@/lib/api";
import { speakAlphaReply } from "@/lib/speech";
import type { CapabilityCard } from "@/types/state";

export default function DashboardPage() {
  const { state, loading, reconnect, metricHistory, pulseKey } = useAlphaState();
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

  const speakReply = useCallback(
    (reply: string) => {
      if (!autoTts) return;
      speakAlphaReply(reply, ttsVoice);
    },
    [autoTts, ttsVoice]
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
      try {
        const res = await sendCommand(cmd);
        const reply = res.reply ?? "No response";
        onLog(reply, "alpha");
        speakReply(reply);
      } catch (e) {
        onLog(e instanceof Error ? e.message : "Voice command failed", "system");
      }
    },
    [live, gatewayOnline, onLog, speakReply]
  );

  const { status: wakeStatus, detail: wakeDetail } = useWakeWordListener({
    enabled: live && gatewayOnline && browserWake,
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
        onReconnect={reconnect}
        onSettings={() => setSettingsOpen(true)}
        onCustomizeView={() => setViewOpen(true)}
      />

      <ViewCustomizer
        open={viewOpen}
        onClose={() => setViewOpen(false)}
        widgets={layout.widgets}
        mcpCategories={layout.mcpCategories}
        mcp={state.mcp}
        onToggleWidget={toggleWidget}
        onToggleMcpCategory={toggleMcpCategory}
      />

      {live && isWidgetOn("metrics") && (
        <>
          <MetricsBar
            metrics={state.metrics}
            polymarket={state.polymarket}
            history={metricHistory}
            gatewayOnline={gatewayOnline}
            pulseKey={pulseKey}
          />
          <ProfileAgentsRow profiles={state.profile_agents ?? []} />
        </>
      )}

      {loading ? (
        <LoadingScreen />
      ) : !live ? (
        <ConnectScreen
          hermesInstalled={Boolean(state.hermes_installed)}
          openclawInstalled={Boolean(state.openclaw?.gateway_url) || state.openclaw_connected}
          hermesConnected={state.hermes_connected}
          openclawConnected={state.openclaw_connected}
          runtimePreference={state.runtime}
          onOpenSettings={() => setSettingsOpen(true)}
          onReconnect={reconnect}
        />
      ) : (
        <main className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-12">
          {isWidgetOn("capabilities") && (
            <div className="flex min-h-0 flex-col lg:col-span-3">
              <CapabilitiesPanel
                capabilities={capabilities}
                gatewayOnline={gatewayOnline}
              />
            </div>
          )}

          <div
            className={`flex min-h-0 flex-col gap-3 ${
              isWidgetOn("capabilities") ? "lg:col-span-6" : "lg:col-span-9"
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
                  onLog={onLog}
                  onReply={speakReply}
                />
              </div>
            )}
            {isWidgetOn("telemetry") && (
              <TelemetryPanel events={state.live_events} logs={logs} />
            )}
          </div>

          {(isWidgetOn("tailscale") ||
            isWidgetOn("integrations") ||
            isWidgetOn("mcp_tools") ||
            isWidgetOn("mcp_data")) && (
            <div className="min-h-0 lg:col-span-3">
              <SidePanels
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

      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        runtime={state.runtime}
        live={live}
        voiceConfig={state.voice_config}
        onSaved={reconnect}
      />
    </div>
  );
}