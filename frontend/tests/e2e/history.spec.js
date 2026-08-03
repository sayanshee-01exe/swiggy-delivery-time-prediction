import { test, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = path.resolve(__dirname, '../../..', 'tests/screenshots');

const HEALTHY = {
  status: 'ok',
  model_loaded: true,
  model_name: 'swiggy-delivery-time-model',
  error: null,
};

/** Serve an incrementing prediction so rows are distinguishable. */
async function setup(page, { predictions = [12, 24, 36, 48, 60, 72] } = {}) {
  let call = 0;
  await page.route('**/api/health', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(HEALTHY),
    })
  );
  await page.route('**/api/predict', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        prediction_minutes: predictions[call++ % predictions.length],
      }),
    })
  );
  await page.goto('/');
}

const submit = async (page) => {
  const before = await page.getByTestId('history-row').count();
  await page.getByTestId('submit-button').click();
  await expect(page.getByTestId('history-row')).toHaveCount(before + 1);
};

test.describe('Task 10 — session prediction history', () => {
  test('is hidden until the first prediction', async ({ page }) => {
    await setup(page);
    await expect(page.getByTestId('history-list')).toBeHidden();
  });

  test('records a row per successful prediction', async ({ page }) => {
    await setup(page);

    await submit(page);
    await expect(page.getByTestId('history-list')).toBeVisible();

    await submit(page);
    await expect(page.getByTestId('history-row')).toHaveCount(2);

    await page.screenshot({
      path: path.join(SHOTS, 'task10-01-history.png'),
      fullPage: true,
    });
  });

  test('shows the newest prediction first', async ({ page }) => {
    await setup(page);

    await submit(page); // 12
    await submit(page); // 24

    const rows = page.getByTestId('history-row');
    await expect(rows.first()).toContainText('24');
    await expect(rows.last()).toContainText('12');
  });

  test('each row shows distance, traffic, weather and the result', async ({
    page,
  }) => {
    await setup(page);

    await page.getByTestId('field-distance_km').fill('9.4');
    await page.getByTestId('field-traffic').selectOption('jam');
    await page.getByTestId('field-weather').selectOption('fog');
    await submit(page);

    const row = page.getByTestId('history-row').first();
    await expect(row).toContainText('9.4');
    await expect(row).toContainText(/jam/i);
    await expect(row).toContainText(/fog/i);
    await expect(row).toContainText('12');
  });

  test('keeps only the last five', async ({ page }) => {
    // 12, 24, 36, 48, 60, 72 -- the 7th call wraps back to 12
    await setup(page);

    for (let i = 0; i < 5; i += 1) await submit(page);
    await expect(page.getByTestId('history-row')).toHaveCount(5);

    // a sixth prediction must evict the oldest rather than grow the list
    await page.getByTestId('submit-button').click();
    await expect(page.getByTestId('history-row').first()).toContainText('72');
    await expect(page.getByTestId('history-row')).toHaveCount(5);
    // 12 was the oldest and should be gone
    await expect(page.getByTestId('history-list')).not.toContainText('12 min');
  });

  test('a failed prediction is not recorded', async ({ page }) => {
    await setup(page);
    await submit(page);

    await page.route('**/api/predict', (route) =>
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Model is unavailable' }),
      })
    );

    await page.getByTestId('submit-button').click();
    await expect(page.getByTestId('error-message')).toBeVisible();
    await expect(page.getByTestId('history-row')).toHaveCount(1);
  });

  test('clears on reload', async ({ page }) => {
    await setup(page);
    await submit(page);
    await expect(page.getByTestId('history-row')).toHaveCount(1);

    await page.reload();
    await expect(page.getByTestId('history-list')).toBeHidden();
  });

  test('does not overflow on a 360px viewport', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 720 });
    await setup(page);
    await submit(page);
    await submit(page);

    const overflows = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth
    );
    expect(overflows).toBe(false);

    await page.screenshot({
      path: path.join(SHOTS, 'task10-02-history-mobile.png'),
      fullPage: true,
    });
  });
});
