"use client";

interface ActivityOrbProps {
  pulse: boolean;
  active: boolean;
}

export function ActivityOrb({ pulse, active }: ActivityOrbProps) {
  return (
    <div
      className={`relative h-20 w-20 shrink-0 ${pulse ? "animate-orb-pulse" : ""}`}
      title={active ? "Live agent activity" : "Awaiting activity"}
    >
      <div
        className="absolute inset-0 rounded-full opacity-60 blur-md"
        style={{
          background: active
            ? "radial-gradient(circle, #ff2d78 0%, #ff006e 55%, transparent 70%)"
            : "radial-gradient(circle, #ff2d7844 0%, transparent 70%)",
        }}
      />
      <div
        className="absolute inset-2 rounded-full border border-[#ff2d78]/40"
        style={{
          background:
            "radial-gradient(circle at 35% 35%, #ff5a9a, #ff006e 60%, #8a0038 100%)",
          boxShadow: active
            ? "0 0 24px rgba(255,45,120,0.7), inset 0 0 12px rgba(255,0,110,0.4)"
            : "0 0 8px rgba(255,45,120,0.2)",
        }}
      />
      <div className="absolute inset-5 rounded-full bg-white/10 blur-[2px]" />
    </div>
  );
}