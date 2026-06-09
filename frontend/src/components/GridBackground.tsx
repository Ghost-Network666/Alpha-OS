"use client";

/** Static grid — no infinite animation (saves GPU / Lighthouse performance). */
export function GridBackground() {
  return (
    <div
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-[#0a0a0f]"
      aria-hidden
    >
      <div className="absolute inset-0 bg-grid-static opacity-[0.28]" />
      <div className="absolute inset-0 bg-gradient-to-b from-[#0a0a0f] via-transparent to-[#0a0a0f]" />
    </div>
  );
}