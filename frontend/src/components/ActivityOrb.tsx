"use client";

import { memo } from "react";

interface ActivityOrbProps {
  pulse: boolean;
  active: boolean;
}

export const ActivityOrb = memo(function ActivityOrb({
  pulse,
  active,
}: ActivityOrbProps) {
  return (
    <div
      className={`relative h-16 w-16 shrink-0 sm:h-20 sm:w-20 ${pulse ? "animate-orb-pulse" : ""}`}
      title={active ? "Live agent activity" : "Awaiting activity"}
    >
      <div
        className="absolute inset-0 rounded-full opacity-45 sm:opacity-55"
        style={{
          background: active
            ? "radial-gradient(circle, #ff2d78 0%, #ff006e 55%, transparent 70%)"
            : "radial-gradient(circle, #ff2d7844 0%, transparent 70%)",
        }}
      />
      <div
        className="absolute inset-1.5 rounded-full border border-[#ff2d78]/40 sm:inset-2"
        style={{
          background:
            "radial-gradient(circle at 35% 35%, #ff5a9a, #ff006e 60%, #8a0038 100%)",
          boxShadow: active
            ? "0 0 10px rgba(255,45,120,0.4)"
            : "0 0 4px rgba(255,45,120,0.12)",
        }}
      />
    </div>
  );
});