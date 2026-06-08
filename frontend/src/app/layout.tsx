import type { Metadata } from "next";
import Script from "next/script";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const TAILSCALE_HTTPS = (
  process.env.NEXT_PUBLIC_TAILSCALE_HTTPS_URL ?? ""
).replace(/\/$/, "");

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Alpha OS",
  description:
    "Voice-first command center for Hermes and OpenClaw — stdio MCP from your runtime configs",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body
        className={`${geistSans.variable} ${geistMono.variable} h-full font-sans antialiased`}
      >
        {TAILSCALE_HTTPS ? (
          <Script id="alpha-os-https-redirect" strategy="beforeInteractive">
            {`(function(){var h=location.hostname;if(location.protocol!=="http:")return;if(h==="localhost"||h==="127.0.0.1")return;var u=${JSON.stringify(TAILSCALE_HTTPS)};if(!u)return;location.replace(u+location.pathname+location.search);})();`}
          </Script>
        ) : null}
        {children}
      </body>
    </html>
  );
}