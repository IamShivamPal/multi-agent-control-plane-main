type MetricCardProps = {
  label: string;
  value: string | number;
  tone?: "default" | "green" | "orange" | "blue" | "red";
  className?: string;
};

const toneClass: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  default: "text-slate-900",
  green: "text-emerald-600",
  orange: "text-amber-600",
  blue: "text-blue-600",
  red: "text-rose-600"
};

export function MetricCard({ label, value, tone = "default", className = "" }: MetricCardProps) {
  return (
    <article className={`rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100 ${className}`}>
      <p className={`text-3xl font-bold ${toneClass[tone]}`}>{value}</p>
      <p className="mt-2 text-sm font-medium text-slate-500">{label}</p>
    </article>
  );
}
