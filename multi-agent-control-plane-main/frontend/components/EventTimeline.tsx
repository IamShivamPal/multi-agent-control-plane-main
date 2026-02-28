type EventItem = {
  title: string;
  time_ago: string;
  tone: string;
};

type EventTimelineProps = {
  events: EventItem[];
};

const toneClass: Record<string, string> = {
  green: "border-emerald-400",
  blue: "border-blue-400",
  indigo: "border-indigo-400",
  orange: "border-amber-400",
  purple: "border-purple-400",
  teal: "border-teal-400"
};

export function EventTimeline({ events }: EventTimelineProps) {
  return (
    <ul className="space-y-3">
      {events.map((event) => (
        <li
          key={`${event.title}-${event.time_ago}`}
          className={`rounded-xl border-l-4 bg-slate-50 px-4 py-3 ${toneClass[event.tone] ?? "border-slate-300"}`}
        >
          <p className="text-sm font-semibold text-slate-800">🛰️ {event.title}</p>
          <p className="mt-1 text-xs text-slate-500">{event.time_ago}</p>
        </li>
      ))}
    </ul>
  );
}
