type HealthBadgeProps = {
  status: string;
};

const toneClass: Record<string, string> = {
  CONNECTED: "bg-emerald-500/20 text-emerald-200 border-emerald-400/40",
  HEALTHY: "bg-emerald-500/20 text-emerald-200 border-emerald-400/40",
  DISCONNECTED: "bg-rose-500/20 text-rose-200 border-rose-400/40",
  DOWN: "bg-rose-500/20 text-rose-200 border-rose-400/40",
  MEDIUM: "bg-amber-500/20 text-amber-200 border-amber-400/40",
  CRITICAL: "bg-rose-500/20 text-rose-200 border-rose-400/40"
};

export function HealthBadge({ status }: HealthBadgeProps) {
  const normalized = status.toUpperCase();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass[normalized] ?? "bg-slate-200 text-slate-700 border-slate-300"}`}
    >
      {status}
    </span>
  );
}
