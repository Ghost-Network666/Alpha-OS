export function buildWsUrl(apiBase: string, token?: string): string {
  const trimmed = apiBase.replace(/\/$/, "");
  const wsBase = trimmed.replace(/^http/, "ws");
  const path = wsBase.endsWith("/ws/state") ? wsBase : `${wsBase}/ws/state`;
  if (!token?.trim()) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}token=${encodeURIComponent(token.trim())}`;
}

export function parseBootstrapWsUrl(data: {
  ws_url?: string;
  api_url?: string;
  auth_required?: boolean;
}): string {
  if (data.ws_url) return data.ws_url;
  if (data.api_url) return buildWsUrl(data.api_url);
  throw new Error("Bootstrap missing ws_url");
}