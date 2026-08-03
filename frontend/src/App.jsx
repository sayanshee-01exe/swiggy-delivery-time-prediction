import { useEffect, useState } from 'react';
import PredictionForm from './components/PredictionForm';
import ResultCard from './components/ResultCard';
import HealthBadge from './components/HealthBadge';
import { predict, health } from './api';
import { DEFAULT_ORDER, EXAMPLE_ORDER } from './constants';

export default function App() {
  const [order, setOrder] = useState(DEFAULT_ORDER);
  const [minutes, setMinutes] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [healthState, setHealthState] = useState('loading');
  const [healthDetail, setHealthDetail] = useState('');

  // Fired once on mount. Deliberately does not gate the form: a slow or
  // failed health check should never stop someone from trying a prediction.
  useEffect(() => {
    let cancelled = false;

    health()
      .then((body) => {
        if (cancelled) return;
        setHealthState(body.model_loaded ? 'ok' : 'degraded');
        setHealthDetail(body.error || '');
      })
      .catch((err) => {
        if (cancelled) return;
        setHealthState('unreachable');
        setHealthDetail(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit() {
    setBusy(true);
    setError(null);
    try {
      const { prediction_minutes } = await predict(order);
      setMinutes(prediction_minutes);
    } catch (err) {
      setError(err.message);
      setMinutes(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl flex-col gap-3 px-4 py-6 sm:flex-row sm:items-start sm:justify-between sm:px-6">
          <div>
            <h1
              data-testid="app-heading"
              className="text-3xl font-bold tracking-tight"
            >
              Delivery Time Predictor
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Estimate how long a food order takes to arrive.
            </p>
          </div>
          <HealthBadge state={healthState} title={healthDetail} />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <div className="mb-4 flex justify-end">
          <button
            type="button"
            data-testid="example-button"
            onClick={() => setOrder(EXAMPLE_ORDER)}
            disabled={busy}
            className="rounded-md border border-slate-300 bg-white px-3 py-2
                       text-sm font-medium text-slate-700 shadow-sm transition
                       hover:bg-slate-100 focus:outline-none focus:ring-2
                       focus:ring-slate-400 disabled:opacity-50"
          >
            Try an example
          </button>
        </div>

        <PredictionForm
          values={order}
          onChange={setOrder}
          onSubmit={onSubmit}
          busy={busy}
        />

        {error && (
          <p
            data-testid="error-message"
            role="alert"
            className="mt-6 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800"
          >
            {error}
          </p>
        )}

        {minutes !== null && !error && <ResultCard minutes={minutes} />}
      </main>
    </div>
  );
}
