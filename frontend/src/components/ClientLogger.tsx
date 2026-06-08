"use client";

import { useEffect } from "react";
import { initClientLogging } from "@/lib/client-log";

/** Registers global error handlers that POST to /api/log → alpha-os.log */
export function ClientLogger() {
  useEffect(() => {
    initClientLogging();
  }, []);
  return null;
}