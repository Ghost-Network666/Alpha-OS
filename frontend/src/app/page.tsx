"use client";

import { useCallback, useState } from "react";
import { AgentsPanel } from "@/components/AgentsPanel";
import { CommandPanel } from "@/components/CommandPanel";
import { ConnectScreen } from "@/components/ConnectScreen";
import { GridBackground } from "@/components/GridBackground";
import { MetricsBar } from "@/components/MetricsBar";
import { SettingsDrawer } from "@/components/SettingsDrawer";
import { McpPanel } from "@/components/McpPanel";
import { SidePanels } from "@/components/SidePanels";
import { TelemetryPanel } from "@/components/TelemetryPanel";
import { TopBar } from "@/components/TopBar";
import { useAlphaState } from "@/hooks/useAlphaState";
import { useWakeWordListener } from "@/hooks/useWakeWordListener";
import { fetchState, sendCommand } from "@/lib/api";
import { speakAlphaReply } from "@/lib/speech";

export default function DashboardPage() {
  const { state, reconnect, metricHistory, pulseKey } = useAlphaState();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [logs, setLogs] = useState<{ ts: string; who: string; msg: string }[]>(
    []
  );

  const live = Boolean(state.live);
  const wakeWord = state.voice_config?.wake_word ?? "hey alpha";
  const browserWake = state.voice_config?.browser_wake ?? true;
  const autoTts = state.voice_config?.auto_tts ?? true;
  const ttsVoice = state.voice_config?.tts_voice ?? "en-US-AriaNeural";
  const ttsProvider = state.voice_config?.tts_provider ?? "edge";

  const speakReply = useCallback(
    (reply: string) => {
      if (!autoTts) return;
      void speakAlphaReply(reply, ttsVoice, ttsProvider);
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
      if (!cmd || !live) return;
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
    [live, onLog, speakReply]
  );

  const { status: wakeStatus } = useWakeWordListener({
    enabled: live && browserWake,
    wakeWord,
    onWake: () => onLog("Wake phrase detected — listening for command", "voice"),
    onCommand: handleVoiceCommand,
    onStatus: (status, detail) => {
      if (status === "error" && detail) onLog(detail, "system");
    },
  });

  const hasActivity =
    live &&
    (state.live_events.length > 0 || state.metrics.events_per_min > 0);

  return (
    <div className="flex h-full min-h-screen flex-col">
      <GridBackground />

      <TopBar
        connected={live}
        runtime={state.runtime}
        hermesConnected={state.hermes_connected}
        openclawConnected={state.openclaw_connected}
        onReconnect={reconnect}
        onSettings={() => setSettingsOpen(true)}
      />

      {live && (
        <MetricsBar
          metrics={state.metrics}
          mcp={state.mcp}
          history={metricHistory}
          pulseKey={pulseKey}
        />
      )}

      {!live ? (
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <ConnectScreen
              hermesInstalled={Boolean(state.hermes_installed)}
              openclawInstalled={Boolean(state.openclaw_installed)}
              hermesConnected={state.hermes_connected}
              openclawConnected={state.openclaw_connected}
              runtimePreference={state.runtime_preference}
              onOpenSettings={() => setSettingsOpen(true)}
              onReconnect={reconnect}
            />
          </div>
          <div className="min-h-0 lg:col-span-4">
            <McpPanel
              mcp={state.mcp}
              runtime={state.runtime}
              onRefresh={reconnect}
            />
          </div>
        </div>
      ) : (
        <main className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-12">
          <div className="flex min-h-0 flex-col lg:col-span-3">
            <AgentsPanel agents={state.agents} />
          </div>

          <div className="flex min-h-0 flex-col gap-3 lg:col-span-6">
            <div className="shrink-0">
              <CommandPanel
                greeting={state.greeting}
                orbPulse={state.orb_pulse}
                hasActivity={hasActivity}
                wakeStatus={wakeStatus}
                wakeWord={wakeWord}
                onLog={onLog}
                onReply={speakReply}
              />
            </div>
            <TelemetryPanel events={state.live_events} logs={logs} />
          </div>

          <div className="min-h-0 lg:col-span-3">
            <SidePanels
              tailscale={state.tailscale}
              integrations={state.integrations}
              mcp={state.mcp}
              runtime={state.runtime}
              onMcpRefresh={async () => {
                await fetchState();
                onLog("MCP stdio probe complete", "system");
              }}
            />
          </div>
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