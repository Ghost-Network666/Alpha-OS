"use client";

import { getTailscaleHttpsUrl, micBlockedReason } from "@/lib/secure-context";

interface MicSecureBannerProps {
  tailscaleHttpsUrl?: string | null;
}

export function MicSecureBanner({ tailscaleHttpsUrl }: MicSecureBannerProps) {
  const blocked = micBlockedReason(tailscaleHttpsUrl);
  const httpsUrl = getTailscaleHttpsUrl(tailscaleHttpsUrl);

  if (!blocked || !httpsUrl) return null;

  const openUrl = `${httpsUrl}/`;

  return (
    <div
      role="alert"
      className="shrink-0 border-b border-amber-800/50 bg-amber-950/40 px-4 py-2.5"
    >
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-2">
        <p className="text-xs leading-relaxed text-amber-200/90">
          <span className="font-semibold text-amber-300">Voice is off</span> — browsers
          block the microphone on plain HTTP. Open Alpha OS over Tailscale HTTPS to use
          “hey alpha”.
        </p>
        <a
          href={openUrl}
          className="shrink-0 rounded-lg border border-amber-600/60 bg-amber-900/30 px-3 py-1.5 text-xs font-semibold text-amber-200 transition hover:bg-amber-800/40"
        >
          Open secure URL →
        </a>
      </div>
      <p className="mx-auto mt-1 max-w-4xl font-mono text-[10px] text-amber-600/80">
        {openUrl}
      </p>
    </div>
  );
}