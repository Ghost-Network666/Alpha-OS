"use client";

import { useEffect, useMemo, useState } from "react";
import { postConfig } from "@/lib/api";

type RuntimeChoice = "hermes" | "openclaw";

interface ConnectScreenProps {
  hermesInstalled: boolean;
  openclawInstalled: boolean;
  hermesConnected: boolean;
  openclawConnected: boolean;
  runtimePreference?: string;
  onOpenSettings: () => void;
  onReconnect: () => void;
}

const HERMES_INSTALL = [
  "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash",
  "hermes setup",
  "pip install alpha-os && alpha-os setup",
  "Enable API_SERVER_ENABLED=true in ~/.hermes/.env",
  "hermes gateway",
];

const OPENCLAW_INSTALL = [
  "curl -fsSL https://openclaw.ai/install.sh | bash",
  "openclaw onboard --install-daemon",
  "openclaw models auth login --provider xai --method oauth",
  "openclaw gateway run",
];

const HERMES_CONNECT = [
  "Start the Hermes API server: hermes gateway",
  "Confirm API_SERVER_ENABLED=true in ~/.hermes/.env",
  "Set API_SERVER_KEY in ~/.hermes/.env",
  "Click Reconnect below",
];

const OPENCLAW_CONNECT = [
  "Start the OpenClaw gateway: openclaw gateway run",
  "Confirm ~/.openclaw/openclaw.json gateway port (default 18789)",
  "Set gateway auth token if configured",
  "Click Reconnect below",
];

function statusBadge(installed: boolean, connected: boolean) {
  if (connected) return { label: "Live", className: "text-emerald-400 border-emerald-900/50 bg-emerald-950/30" };
  if (installed) return { label: "Installed", className: "text-amber-400 border-amber-900/50 bg-amber-950/30" };
  return { label: "Not found", className: "text-slate-500 border-slate-800 bg-[#0a0a0f]" };
}

export function ConnectScreen({
  hermesInstalled,
  openclawInstalled,
  hermesConnected,
  openclawConnected,
  runtimePreference = "auto",
  onOpenSettings,
  onReconnect,
}: ConnectScreenProps) {
  const defaultChoice: RuntimeChoice = useMemo(() => {
    if (runtimePreference === "openclaw") return "openclaw";
    if (runtimePreference === "hermes") return "hermes";
    if (openclawConnected && !hermesConnected) return "openclaw";
    if (hermesInstalled || !openclawInstalled) return "hermes";
    return "openclaw";
  }, [
    runtimePreference,
    hermesInstalled,
    openclawInstalled,
    hermesConnected,
    openclawConnected,
  ]);

  const [choice, setChoice] = useState<RuntimeChoice>(defaultChoice);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setChoice(defaultChoice);
  }, [defaultChoice]);

  const neitherInstalled = !hermesInstalled && !openclawInstalled;
  const selectedInstalled = choice === "hermes" ? hermesInstalled : openclawInstalled;
  const selectedConnected = choice === "hermes" ? hermesConnected : openclawConnected;

  const title = neitherInstalled
    ? "Choose your agent runtime"
    : !selectedInstalled
      ? choice === "hermes"
        ? "Install Hermes Agent"
        : "Install OpenClaw"
      : !selectedConnected
        ? choice === "hermes"
          ? "Connect Hermes Gateway"
          : "Connect OpenClaw Gateway"
        : "Connecting…";

  const steps = neitherInstalled
    ? choice === "hermes"
      ? HERMES_INSTALL
      : OPENCLAW_INSTALL
    : !selectedInstalled
      ? choice === "hermes"
        ? HERMES_INSTALL
        : OPENCLAW_INSTALL
      : !selectedConnected
        ? choice === "hermes"
          ? HERMES_CONNECT
          : OPENCLAW_CONNECT
        : [];

  const selectRuntime = async (runtime: RuntimeChoice) => {
    setChoice(runtime);
    setSaving(true);
    try {
      await postConfig({ runtime });
      onReconnect();
    } finally {
      setSaving(false);
    }
  };

  const hermesBadge = statusBadge(hermesInstalled, hermesConnected);
  const openclawBadge = statusBadge(openclawInstalled, openclawConnected);

  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-xl rounded-2xl border border-cyan-900/30 bg-[#0d0d14]/90 p-8">
        <h1 className="mb-2 text-center text-xl font-bold tracking-wide text-[#00f5ff]">
          {title}
        </h1>
        <p className="mb-6 text-center text-sm text-slate-500">
          Alpha OS stays blank until a runtime gateway is live. We detected
          your local installs below — pick Hermes or OpenClaw. No demo data.
        </p>

        <div className="mb-6 grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => selectRuntime("hermes")}
            disabled={saving}
            className={`rounded-xl border p-4 text-left transition ${
              choice === "hermes"
                ? "border-cyan-700 bg-cyan-950/40 ring-1 ring-cyan-800/60"
                : "border-slate-800 bg-[#0a0a0f] hover:border-slate-700"
            }`}
          >
            <div className="mb-1 text-sm font-semibold text-slate-200">Hermes</div>
            <div className="mb-2 font-mono text-[10px] text-slate-600">~/.hermes</div>
            <span
              className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${hermesBadge.className}`}
            >
              {hermesBadge.label}
            </span>
          </button>

          <button
            type="button"
            onClick={() => selectRuntime("openclaw")}
            disabled={saving}
            className={`rounded-xl border p-4 text-left transition ${
              choice === "openclaw"
                ? "border-cyan-700 bg-cyan-950/40 ring-1 ring-cyan-800/60"
                : "border-slate-800 bg-[#0a0a0f] hover:border-slate-700"
            }`}
          >
            <div className="mb-1 text-sm font-semibold text-slate-200">OpenClaw</div>
            <div className="mb-2 font-mono text-[10px] text-slate-600">~/.openclaw</div>
            <span
              className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${openclawBadge.className}`}
            >
              {openclawBadge.label}
            </span>
          </button>
        </div>

        {neitherInstalled && (
          <p className="mb-4 text-center text-[10px] text-slate-600">
            No ~/.hermes or ~/.openclaw found — choose one to install first.
          </p>
        )}

        {hermesInstalled && openclawInstalled && !selectedConnected && (
          <p className="mb-4 text-center text-[10px] text-amber-600/80">
            Both runtimes detected. Select which gateway to connect, then follow
            the steps below.
          </p>
        )}

        <ol className="mb-6 space-y-2 text-left font-mono text-xs text-slate-400">
          {steps.map((step, i) => (
            <li
              key={i}
              className="rounded-lg border border-slate-800/60 bg-[#0a0a0f] px-3 py-2"
            >
              <span className="mr-2 text-cyan-700">{i + 1}.</span>
              {step}
            </li>
          ))}
        </ol>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onReconnect}
            disabled={saving}
            className="flex-1 rounded-xl border border-cyan-800 bg-cyan-950/50 py-2.5 text-sm font-semibold text-cyan-300 hover:bg-cyan-900/40 disabled:opacity-50"
          >
            Reconnect
          </button>
          <button
            type="button"
            onClick={onOpenSettings}
            className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-400 hover:border-slate-600"
          >
            Settings
          </button>
        </div>
      </div>
    </div>
  );
}