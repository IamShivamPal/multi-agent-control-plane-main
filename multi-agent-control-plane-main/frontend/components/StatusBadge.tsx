type StatusBadgeProps = {
  label: string;
  icon: string;
  variant: "green" | "blue" | "purple";
};

const variantClasses: Record<StatusBadgeProps["variant"], string> = {
  green: "bg-emerald-100 text-emerald-700 border-emerald-200",
  blue: "bg-sky-100 text-sky-700 border-sky-200",
  purple: "bg-violet-100 text-violet-700 border-violet-200"
};

export function StatusBadge({ label, icon, variant }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${variantClasses[variant]}`}
      aria-label={label}
    >
      <span aria-hidden="true">{icon}</span>
      {label}
    </span>
  );
}
