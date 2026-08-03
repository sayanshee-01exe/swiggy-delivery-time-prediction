import { NUMBER_FIELDS, SELECT_FIELDS, humanize } from '../constants';

const labelClass = 'block text-sm font-medium text-slate-700';
const controlClass =
  'mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 ' +
  'text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none ' +
  'focus:ring-2 focus:ring-slate-400 disabled:bg-slate-100';

export default function PredictionForm({ values, onChange, onSubmit, busy }) {
  const update = (name, raw, numeric) => {
    onChange({ ...values, [name]: numeric ? Number(raw) : raw });
  };

  return (
    <form
      data-testid="prediction-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {NUMBER_FIELDS.map(({ name, label, unit, min, max, step, hint }) => (
          <div key={name}>
            <label htmlFor={name} className={labelClass}>
              {label}{' '}
              <span className="font-normal text-slate-400">({unit})</span>
            </label>
            <input
              id={name}
              data-testid={`field-${name}`}
              type="number"
              inputMode="decimal"
              min={min}
              max={max}
              step={step}
              required
              disabled={busy}
              value={values[name]}
              onChange={(e) => update(name, e.target.value, true)}
              className={controlClass}
            />
            <p className="mt-1 text-xs text-slate-500">{hint}</p>
          </div>
        ))}

        {SELECT_FIELDS.map(({ name, label, options, numeric }) => (
          <div key={name}>
            <label htmlFor={name} className={labelClass}>
              {label}
            </label>
            <select
              id={name}
              data-testid={`field-${name}`}
              disabled={busy}
              value={values[name]}
              onChange={(e) => update(name, e.target.value, numeric)}
              className={controlClass}
            >
              {options.map((option) => (
                <option key={option} value={option}>
                  {humanize(option)}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      <button
        type="submit"
        data-testid="submit-button"
        disabled={busy}
        className="mt-6 w-full rounded-md bg-slate-900 px-4 py-3 font-semibold
                   text-white shadow-sm transition hover:bg-slate-700
                   focus:outline-none focus:ring-2 focus:ring-slate-500
                   focus:ring-offset-2 disabled:cursor-not-allowed
                   disabled:bg-slate-400 sm:w-auto sm:px-8"
      >
        {busy ? 'Predicting…' : 'Predict delivery time'}
      </button>
    </form>
  );
}
