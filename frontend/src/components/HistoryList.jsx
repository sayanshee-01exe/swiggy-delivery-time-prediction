import { humanize } from '../constants';

export default function HistoryList({ entries }) {
  if (entries.length === 0) return null;

  return (
    <section data-testid="history-list" className="mt-8">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        This session
      </h2>

      <ul className="mt-3 divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white">
        {entries.map((entry) => (
          <li
            key={entry.id}
            data-testid="history-row"
            className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-3"
          >
            <span className="min-w-0 text-sm text-slate-600">
              <span className="font-medium text-slate-900">
                {entry.distance_km} km
              </span>
              {' · '}
              {humanize(entry.traffic)} traffic
              {' · '}
              {humanize(entry.weather)}
            </span>
            <span className="whitespace-nowrap text-sm font-semibold tabular-nums text-slate-900">
              {Math.round(entry.minutes)} min
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
