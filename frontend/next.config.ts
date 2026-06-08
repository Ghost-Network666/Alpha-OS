import type { NextConfig } from "next";

function tailscaleDevOrigins(): string[] {
  const raw = process.env.NEXT_PUBLIC_TAILSCALE_HTTPS_URL ?? "";
  if (!raw) return [];
  try {
    const host = new URL(raw.startsWith("http") ? raw : `https://${raw}`).hostname;
    return host ? [host, `*.${host.split(".").slice(-3).join(".")}`] : [];
  } catch {
    return [];
  }
}

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    ...tailscaleDevOrigins(),
  ],
  async rewrites() {
    const api =
      process.env.INTERNAL_API_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      `http://127.0.0.1:${process.env.NEXT_PUBLIC_API_PORT ?? "9000"}`;
    return [
      {
        source: "/api/:path*",
        destination: `${api}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;