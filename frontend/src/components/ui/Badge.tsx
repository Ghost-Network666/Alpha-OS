"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  tone?: "default" | "success" | "warning" | "danger" | "secondary";
}

export function Badge({ className, tone = "default", ...props }: BadgeProps) {
  const tones: Record<string, string> = {
    default: "border-slate-700 text-slate-300 bg-slate-800/40",
    success: "border-[#00ff88]/40 text-[#00ff88] bg-[#00ff88]/10",
    warning: "border-amber-500/40 text-amber-400 bg-amber-500/10",
    danger: "border-[#ff3366]/40 text-[#ff3366] bg-[#ff3366]/10",
    secondary: "border-slate-700/60 text-slate-400 bg-slate-800/30",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-[0.08em] uppercase",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
