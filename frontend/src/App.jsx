import { useState } from 'react';
import PredictionForm from './components/PredictionForm';
import ResultCard from './components/ResultCard';
import { predict } from './api';
import { DEFAULT_ORDER } from './constants';

export default function App() {
  const [order, setOrder] = useState(DEFAULT_ORDER);
  const [minutes, setMinutes] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

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
        <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
          <h1 data-testid="app-heading" className="text-3xl font-bold tracking-tight">
            Delivery Time Predictor
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Estimate how long a food order takes to arrive.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
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
