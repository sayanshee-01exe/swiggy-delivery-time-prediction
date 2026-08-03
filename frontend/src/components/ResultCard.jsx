export default function ResultCard({ minutes }) {
  return (
    <section
      data-testid="result-card"
      aria-live="polite"
      className="mt-6 rounded-lg border border-slate-900 bg-slate-900 p-6 text-white shadow-sm"
    >
      <p className="text-sm uppercase tracking-wide text-slate-300">
        Estimated delivery time
      </p>
      <p className="mt-2 flex items-baseline gap-2">
        <span data-testid="result-minutes" className="text-5xl font-bold tabular-nums">
          {Math.round(minutes)}
        </span>
        <span className="text-xl text-slate-300">minutes</span>
      </p>
      <p className="mt-3 text-xs text-slate-400">
        Predicted from the conditions above — not a live order.
      </p>
    </section>
  );
}
