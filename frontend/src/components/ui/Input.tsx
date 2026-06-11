"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-lg border border-slate-700 bg-[#0a0a0f] px-3 py-1.5 text-sm font-mono placeholder:text-slate-600",
          "focus-visible:outline-none focus-visible:border-[#00f5ff]/60 focus-visible:ring-1 focus-visible:ring-[#00f5ff]/30",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
