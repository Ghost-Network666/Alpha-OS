"use client";

import { useLayoutEffect } from "react";
import { clientLog } from "@/lib/client-log";
import { getTailscaleHttpsUrl, needsHttpsForMic } from "@/lib/secure-context";

interface SecureTailscaleRedirectProps {
  tailscaleHttpsUrl?: string | null;
}

/** Redirect HTTP → Tailscale HTTPS immediately (enables microphone). */
export function SecureTailscaleRedirect({
  tailscaleHttpsUrl,
}: SecureTailscaleRedirectProps) {
  useLayoutEffect(() => {
    if (!needsHttpsForMic()) return;
    const base = getTailscaleHttpsUrl(tailscaleHttpsUrl);
    if (!base) return;
    const target =
      base.replace(/\/$/, "") + window.location.pathname + window.location.search;
    if (window.location.href === target) return;
    clientLog(
      "info",
      "Redirecting to Tailscale HTTPS for voice",
      target,
      "secure"
    );
    window.location.replace(target);
  }, [tailscaleHttpsUrl]);

  return null;
}