"use client";

import { useEffect } from "react";
import { initClientLogging } from "@/lib/client-log";

/** Registers global error handlers — deferred so it never blocks first paint. */
export function ClientLogger() {
  useEffect(() => {
    const run = () => initClientLogging();
    if (typeof requestIdleCallback === "function") {
      const id = requestIdleCallback(run, { timeout: 4000 });
      return () => cancelIdleCallback(id);
    }
    const t = setTimeout(run, 1500);
    return () => clearTimeout(t);
  }, []);
  return null;
}