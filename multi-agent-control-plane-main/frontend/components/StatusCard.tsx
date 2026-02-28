import { HealthBadge } from "@/components/HealthBadge";

type DomainStatus = {
  name: string;
  domain: string;
  url: string;
  status: string;
  health_score: number;
  response_time_ms: number;
  cpu_percent: number;
  memory_percent: number;
  uptime_percent: number;
  last_action: string;
  errors_24h: number;
};

type StatusCardProps = {
  item: DomainStatus;
};

export function StatusCard({ item }: StatusCardProps) {
  return (
    <article className="rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 p-6 text-white shadow-lg">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">{item.name}</h3>
          <p className="mt-1 text-sm text-slate-300">{item.domain}</p>
          <a href={item.url} target="_blank" rel="noreferrer" className="text-xs text-indigo-300 hover:text-indigo-200">
            {item.url}
          </a>
        </div>
        <HealthBadge status={item.status} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-xl bg-white/10 p-3">
          <p className="text-slate-300">Health Score</p>
          <p className="text-xl font-bold">{item.health_score}%</p>
        </div>
        <div className="rounded-xl bg-white/10 p-3">
          <p className="text-slate-300">Response Time</p>
          <p className="text-xl font-bold">{item.response_time_ms}ms</p>
        </div>
        <div className="rounded-xl bg-white/10 p-3">
          <p className="text-slate-300">CPU / Memory</p>
          <p className="font-semibold">{item.cpu_percent}% / {item.memory_percent}%</p>
        </div>
        <div className="rounded-xl bg-white/10 p-3">
          <p className="text-slate-300">Uptime</p>
          <p className="font-semibold">{item.uptime_percent}%</p>
        </div>
        <div className="rounded-xl bg-white/10 p-3">
          <p className="text-slate-300">Last Action</p>
          <p className="font-semibold">{item.last_action}</p>
        </div>
        <div className="rounded-xl bg-white/10 p-3">
          <p className="text-slate-300">Errors (24h)</p>
          <p className="font-semibold">{item.errors_24h}</p>
        </div>
      </div>
    </article>
  );
}
