import { HealthBadge } from "@/components/HealthBadge";

type DomainStatusRowProps = {
  name: string;
  status: string;
};

export function DomainStatusRow({ name, status }: DomainStatusRowProps) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2">
      <p className="text-sm font-semibold text-slate-700">{name}</p>
      <HealthBadge status={status} />
    </div>
  );
}
