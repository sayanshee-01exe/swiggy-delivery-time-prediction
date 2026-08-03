const STATES = {
  loading: {
    label: 'Checking…',
    dot: 'bg-slate-400',
    chip: 'border-slate-200 bg-slate-100 text-slate-600',
  },
  ok: {
    label: 'Live',
    dot: 'bg-green-500',
    chip: 'border-green-200 bg-green-50 text-green-800',
  },
  // the API answered, but the model never loaded from the registry
  degraded: {
    label: 'Model unavailable',
    dot: 'bg-red-500',
    chip: 'border-red-200 bg-red-50 text-red-800',
  },
  // we could not reach the API at all - a different problem worth naming
  unreachable: {
    label: "Can't reach service",
    dot: 'bg-amber-500',
    chip: 'border-amber-200 bg-amber-50 text-amber-800',
  },
};

export default function HealthBadge({ state, title }) {
  const { label, dot, chip } = STATES[state] ?? STATES.loading;

  return (
    <span
      data-testid="health-badge"
      data-state={state}
      title={title || undefined}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${chip}`}
    >
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
      {label}
    </span>
  );
}
