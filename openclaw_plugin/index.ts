/**
 * Alpha OS OpenClaw plugin — registers `openclaw alpha` CLI command.
 * Full UI runs via: pip install alpha-os && alpha-os serve
 */

// @ts-nocheck — minimal plugin stub; compile when publishing to ClawHub

export default function register(api: {
  registerCliCommand?: (
    name: string,
    help: string,
    handler: () => Promise<void> | void,
  ) => void;
}) {
  if (!api.registerCliCommand) return;

  api.registerCliCommand(
    "alpha",
    "Open Alpha OS cyber command-center (alpha-os serve)",
    async () => {
      const { execSync } = await import("node:child_process");
      try {
        execSync("alpha-os serve --open", { stdio: "inherit" });
      } catch {
        console.log("\n  Alpha OS not installed. Run:\n");
        console.log("    pip install alpha-os");
        console.log("    alpha-os setup");
        console.log("    alpha-os serve\n");
      }
    },
  );
}