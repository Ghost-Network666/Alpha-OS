let runtimeTailscaleHttps: string | null = null;

function envTailscaleHttpsUrl(): string | null {
  const env = process.env.NEXT_PUBLIC_TAILSCALE_HTTPS_URL?.trim();
  if (env) return env.replace(/\/$/, "");
  return null;
}

/** Called when /api/state returns tailscale_https_url (works without Next rebuild). */
export function setRuntimeTailscaleHttps(url: string | null | undefined): void {
  runtimeTailscaleHttps = url?.trim().replace(/\/$/, "") || null;
}

function resolveTailscaleHttpsUrl(override?: string | null): string | null {
  if (override) return override.replace(/\/$/, "");
  if (runtimeTailscaleHttps) return runtimeTailscaleHttps;
  return envTailscaleHttpsUrl();
}

/** Browsers only allow microphone / Web Speech on HTTPS or localhost. */
export function isSecureMicContext(): boolean {
  if (typeof window === "undefined") return true;
  return window.isSecureContext;
}

export function isLocalDevHost(host: string): boolean {
  return host === "localhost" || host === "127.0.0.1";
}

/** True when page is HTTP and not localhost (mic blocked in all such cases). */
export function needsHttpsForMic(): boolean {
  if (typeof window === "undefined") return false;
  if (window.isSecureContext) return false;
  const host = window.location.hostname;
  if (isLocalDevHost(host)) return false;
  return window.location.protocol === "http:";
}

export function isTailscaleHttpInsecure(): boolean {
  return needsHttpsForMic();
}

export function micBlockedReason(tailscaleHttps?: string | null): string | null {
  if (!needsHttpsForMic()) return null;
  const httpsUrl =
    resolveTailscaleHttpsUrl(tailscaleHttps) ?? "https://<machine>.ts.net";
  return `Voice needs HTTPS — open ${httpsUrl}/ (not HTTP on a Tailscale IP).`;
}

export function getTailscaleHttpsUrl(override?: string | null): string | null {
  return resolveTailscaleHttpsUrl(override);
}

export function usesTailscaleHttps(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.isSecureContext &&
    window.location.protocol === "https:" &&
    /\.ts\.net$/i.test(window.location.hostname)
  );
}