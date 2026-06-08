"use client";

export function LoadingScreen() {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-cyan-900/30 bg-[#0d0d14]/90 p-8 text-center">
        <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-cyan-900 border-t-cyan-400" />
        <h1 className="mb-2 text-lg font-bold tracking-wide text-[#00f5ff]">
          Connecting
        </h1>
        <p className="text-sm text-slate-500">
          Loading Alpha OS state from backend…
        </p>
      </div>
    </div>
  );
}