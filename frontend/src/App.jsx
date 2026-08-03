import { useState } from 'react';
import PredictionForm from './components/PredictionForm';
import { DEFAULT_ORDER } from './constants';

export default function App() {
  const [order, setOrder] = useState(DEFAULT_ORDER);

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
          onSubmit={() => {}}
          busy={false}
        />
      </main>
    </div>
  );
}
