/**
 * Alpha OS OpenClaw plugin — CLI command, HTTP surface, Control UI descriptor.
 * Full UI: pip install alpha-os && alpha-os serve
 */

// @ts-nocheck — loads without openclaw/plugin-sdk at build time in Alpha OS repo

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url));

function alphaPort(api: { config?: { port?: number } }): number {
  return api?.config?.port ?? Number(process.env.ALPHA_OS_PORT ?? 8080);
}

function alphaBase(port: number): string {
  const host = process.env.ALPHA_OS_HOST ?? "127.0.0.1";
  return `http://${host}:${port}`;
}

async function fetchAlphaState(port: number): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetch(`${alphaBase(port)}/api/state`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return null;
    return (await res.json()) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export default function register(api: {
  config?: { port?: number };
  registrationMode?: string;
  registerCli?: (
    registrar: (ctx: { program: unknown }) => void | Promise<void>,
    opts?: { descriptors?: Array<{ name: string; description: string }> },
  ) => void;
  registerCliCommand?: (
    name: string,
    help: string,
    handler: () => Promise<void> | void,
  ) => void;
  registerHttpRoute?: (params: {
    path: string;
    auth?: string;
    handler: (req: unknown, res: { setHeader: (k: string, v: string) => void; end: (b?: string) => void }) => void | Promise<void>;
  }) => void;
  registerGatewayMethod?: (
    name: string,
    handler: (params: Record<string, unknown>) => Promise<unknown>,
    opts?: { scope?: string },
  ) => void;
  session?: {
    controls?: {
      registerControlUiDescriptor?: (desc: Record<string, unknown>) => void;
    };
  };
}) {
  const port = alphaPort(api);
  const mode = api.registrationMode ?? "full";

  const runAlphaServe = async () => {
    const { execSync } = await import("node:child_process");
    try {
      execSync(`alpha-os serve --open --port ${port}`, { stdio: "inherit" });
    } catch {
      console.log("\n  Alpha OS not installed. Run:\n");
      console.log("    pip install alpha-os");
      console.log("    alpha-os setup");
      console.log(`    alpha-os serve --port ${port}\n`);
    }
  };

  if (api.registerCli) {
    api.registerCli(
      async () => {
        await runAlphaServe();
      },
      {
        descriptors: [
          {
            name: "alpha",
            description: "Open Alpha OS cyber command-center (alpha-os serve)",
          },
        ],
      },
    );
  } else if (api.registerCliCommand) {
    api.registerCliCommand(
      "alpha",
      "Open Alpha OS cyber command-center (alpha-os serve)",
      runAlphaServe,
    );
  }

  if (mode !== "full") {
    return;
  }

  if (api.registerHttpRoute) {
    api.registerHttpRoute({
      path: "/alpha-os",
      auth: "plugin",
      handler: async (_req, res) => {
        try {
          const html = readFileSync(join(PLUGIN_DIR, "dashboard", "index.html"), "utf8");
          const withPort = html.replace(
            'var port = params.get("port")',
            `var port = params.get("port") || "${port}"`,
          );
          res.setHeader("Content-Type", "text/html; charset=utf-8");
          res.end(withPort);
        } catch (e) {
          res.setHeader("Content-Type", "text/plain");
          res.end(`Alpha OS dashboard missing: ${e}`);
        }
      },
    });

    api.registerHttpRoute({
      path: "/alpha-os/status",
      auth: "plugin",
      handler: async (_req, res) => {
        const state = await fetchAlphaState(port);
        res.setHeader("Content-Type", "application/json");
        res.end(
          JSON.stringify(
            state ?? {
              runtime: "offline",
              error: `alpha-os serve not reachable on ${alphaBase(port)}`,
            },
          ),
        );
      },
    });
  }

  if (api.registerGatewayMethod) {
    api.registerGatewayMethod(
      "alpha-os.status",
      async () => {
        const state = await fetchAlphaState(port);
        return (
          state ?? {
            connected: false,
            runtime: "offline",
            alpha_os_url: alphaBase(port),
          }
        );
      },
      { scope: "operator.read" },
    );
  }

  const registerUi =
    api.session?.controls?.registerControlUiDescriptor ??
    (api as { registerControlUiDescriptor?: (d: Record<string, unknown>) => void })
      .registerControlUiDescriptor;

  if (registerUi) {
    registerUi({
      id: "alpha-os",
      label: "Alpha OS",
      surface: "settings",
      kind: "link",
      href: `/alpha-os?port=${port}`,
      description: "Cyber command-center — agents, MCP, Tailscale, voice",
    });
    registerUi({
      id: "alpha-os-nav",
      label: "Alpha OS",
      surface: "nav",
      kind: "external",
      href: alphaBase(port),
      description: "Open Alpha OS command center",
    });
  }
}