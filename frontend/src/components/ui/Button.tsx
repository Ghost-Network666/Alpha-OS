"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'prefix'> {
  variant?: "default" | "ghost" | "outline" | "destructive";
  size?: "default" | "sm" | "icon" | "xs";
  prefix?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", prefix, children, disabled, ...props }, ref) => {
    const base =
      "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#00f5ff] disabled:opacity-50 disabled:pointer-events-none";

    const variants = {
      default:
        "bg-[#00f5ff]/10 text-[#00f5ff] border border-[#00f5ff]/40 hover:bg-[#00f5ff]/20 hover:border-[#00f5ff]/60 active:bg-[#00f5ff]/30",
      ghost:
        "text-slate-400 hover:text-[#00f5ff] hover:bg-white/5 border border-transparent hover:border-white/10",
      outline:
        "border border-slate-700/80 text-slate-300 hover:border-[#00f5ff]/60 hover:text-[#00f5ff] bg-transparent",
      destructive:
        "bg-[#ff3366]/10 text-[#ff3366] border border-[#ff3366]/40 hover:bg-[#ff3366]/20",
    };

    const sizes = {
      default: "h-9 px-4 text-sm",
      sm: "h-8 px-3 text-xs",
      xs: "h-6 px-2 text-[10px]",
      icon: "h-9 w-9",
    };

    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], sizes[size], className)}
        disabled={disabled}
        {...props}
      >
        {prefix && <span className="shrink-0">{prefix}</span>}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button };
