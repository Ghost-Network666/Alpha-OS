import { getHttpApiBase } from "@/lib/api";

export type ClientLogLevel = "info" | "warning" | "error";

export function clientLog(
  level: ClientLogLevel,
  message: string,
  detail?: string,
  source = "frontend"
): void {
  if (typeof window === "undefined") return;

  const body = JSON.stringify({ level, source, message, detail });
  const url = `${getHttpApiBase()}/api/log`;

  if (navigator.sendBeacon) {
    try {
      const blob = new Blob([body], { type: "application/json" });
      if (navigator.sendBeacon(url, blob)) return;
    } catch {
      /* fall through */
    }
  }

  void fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {});
}

export function initClientLogging(): void {
  if (typeof window === "undefined") return;
  if ((window as Window & { __alphaOsLogInit?: boolean }).__alphaOsLogInit) return;
  (window as Window & { __alphaOsLogInit?: boolean }).__alphaOsLogInit = true;

  window.addEventListener("error", (ev) => {
    const detail = [ev.filename, ev.lineno, ev.colno].filter(Boolean).join(":");
    clientLog("error", ev.message || "Uncaught error", detail || undefined, "window");
  });

  window.addEventListener("unhandledrejection", (ev) => {
    const reason = ev.reason;
    const message =
      reason instanceof Error ? reason.message : String(reason ?? "unknown");
    const detail = reason instanceof Error ? reason.stack : undefined;
    clientLog("error", "Unhandled rejection", `${message}${detail ? `\n${detail}` : ""}`);
  });
}