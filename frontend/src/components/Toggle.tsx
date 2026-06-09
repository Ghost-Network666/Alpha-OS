"use client";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  hint?: string;
  disabled?: boolean;
}

export function Toggle({
  checked,
  onChange,
  label,
  hint,
  disabled = false,
}: ToggleProps) {
  return (
    <label
      className={`flex items-center justify-between gap-3 rounded-lg border border-slate-800/80 bg-[#0a0a0f]/80 px-3 py-2 ${
        disabled ? "opacity-50" : "cursor-pointer hover:border-slate-700"
      }`}
    >
      <span className="min-w-0">
        <span className="block text-xs text-slate-300">{label}</span>
        {hint ? (
          <span className="mt-0.5 block text-[10px] leading-snug text-slate-600">
            {hint}
          </span>
        ) : null}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 shrink-0 rounded-full transition ${
          checked ? "bg-cyan-600" : "bg-slate-700"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition ${
            checked ? "left-4" : "left-0.5"
          }`}
        />
      </button>
    </label>
  );
}