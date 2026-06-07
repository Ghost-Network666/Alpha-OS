"use client";

interface ConnectScreenProps {
  hermesInstalled: boolean;
  hermesConnected: boolean;
  onOpenSettings: () => void;
  onReconnect: () => void;
}

export function ConnectScreen({
  hermesInstalled,
  hermesConnected,
  onOpenSettings,
  onReconnect,
}: ConnectScreenProps) {
  const title = !hermesInstalled
    ? "Install Hermes Agent"
    : !hermesConnected
      ? "Connect Hermes Gateway"
      : "";

  const steps = !hermesInstalled
    ? [
        "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash",
        "hermes setup",
        "pip install alpha-os && alpha-os setup",
        "Enable API_SERVER_ENABLED=true in ~/.hermes/.env",
        "hermes gateway",
      ]
    : !hermesConnected
      ? [
          "Start the Hermes API server: hermes gateway",
          "Confirm API_SERVER_ENABLED=true in ~/.hermes/.env",
          "Set API_SERVER_KEY in ~/.hermes/.env",
          "Click Reconnect below",
        ]
      : [];

  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-lg rounded-2xl border border-cyan-900/30 bg-[#0d0d14]/90 p-8">
        <h1 className="mb-2 text-center text-xl font-bold tracking-wide text-[#00f5ff]">
          {title}
        </h1>
        <p className="mb-6 text-center text-sm text-slate-500">
          Alpha OS stays blank until ~/.hermes is installed and the gateway is
          live. No demo data.
        </p>
        <ol className="mb-6 space-y-2 text-left font-mono text-xs text-slate-400">
          {steps.map((step, i) => (
            <li key={i} className="rounded-lg border border-slate-800/60 bg-[#0a0a0f] px-3 py-2">
              <span className="mr-2 text-cyan-700">{i + 1}.</span>
              {step}
            </li>
          ))}
        </ol>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onReconnect}
            className="flex-1 rounded-xl border border-cyan-800 bg-cyan-950/50 py-2.5 text-sm font-semibold text-cyan-300 hover:bg-cyan-900/40"
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