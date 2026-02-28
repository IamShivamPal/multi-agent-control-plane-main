import { HealthBadge } from "@/components/HealthBadge";

type FileRow = {
  filename: string;
  status: string;
  size: string;
};

type FileStatusCardProps = {
  icon: string;
  title: string;
  active: number;
  total: number;
  files: FileRow[];
};

export function FileStatusCard({ icon, title, active, total, files }: FileStatusCardProps) {
  return (
    <article className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <span aria-hidden="true">{icon}</span>
        <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      </div>
      <p className="mt-2 text-sm text-slate-500">{active} / {total} files active</p>

      <div className="mt-4 max-h-44 space-y-2 overflow-y-auto pr-1">
        {files.map((file) => (
          <div key={file.filename} className="rounded-xl border border-slate-200 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-xs font-medium text-slate-700">{file.filename}</p>
              <HealthBadge status={file.status} />
            </div>
            <p className="mt-1 text-xs text-slate-500">Size: {file.size}</p>
          </div>
        ))}
      </div>
    </article>
  );
}
