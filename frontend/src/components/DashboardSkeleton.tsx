"use client";

/** Lightweight placeholder — no spinners, minimal paint for fast FCP. */
export function DashboardSkeleton() {
  return (
    <main
      className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-12"
      aria-busy="true"
      aria-label="Loading dashboard"
    >
      <div className="hidden rounded-2xl border border-slate-800/40 bg-[#0d0d14]/60 lg:col-span-3 lg:block">
        <div className="h-full min-h-[200px] animate-pulse p-4">
          <div className="mb-3 h-2 w-24 rounded bg-slate-800/80" />
          <div className="space-y-2">
            <div className="h-10 rounded-lg bg-slate-800/50" />
            <div className="h-10 rounded-lg bg-slate-800/40" />
            <div className="h-10 rounded-lg bg-slate-800/40" />
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-3 lg:col-span-6">
        <div className="rounded-2xl border border-slate-800/40 bg-[#0d0d14]/60 p-4">
          <div className="mb-3 h-3 w-3/4 max-w-md rounded bg-slate-800/60" />
          <div className="h-2 w-40 rounded bg-slate-800/40" />
        </div>
      </div>
    </main>
  );
}