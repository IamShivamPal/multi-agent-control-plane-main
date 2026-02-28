type StatCardProps = {
  icon: string;
  title: string;
  value: string;
  subtext: string;
};

export function StatCard({ icon, title, value, subtext }: StatCardProps) {
  return (
    <article className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
      <div className="mb-4 flex items-center gap-2 text-slate-700">
        <span aria-hidden="true">{icon}</span>
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <p className="text-3xl font-bold text-slate-900">{value}</p>
      <p className="mt-1 text-sm text-slate-500">{subtext}</p>
    </article>
  );
}
