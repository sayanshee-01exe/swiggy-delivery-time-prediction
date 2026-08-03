import { test, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = path.resolve(__dirname, '../../..', 'tests/screenshots');

const mockHealth = (page, body, status = 200) =>
  page.route('**/api/health', (route) =>
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
  );

const HEALTHY = {
  status: 'ok',
  model_loaded: true,
  model_name: 'swiggy-delivery-time-model',
  error: null,
};

const DEGRADED = {
  status: 'degraded',
  model_loaded: false,
  model_name: null,
  error: 'JSONDecodeError: Expecting value: line 1 column 1 (char 0)',
};

test.describe('Task 9 — health badge', () => {
  test('shows a live badge when the model is loaded', async ({ page }) => {
    await mockHealth(page, HEALTHY);
    await page.goto('/');

    const badge = page.getByTestId('health-badge');
    await expect(badge).toBeVisible();
    await expect(badge).toHaveText(/live/i);
    await expect(badge).toHaveAttribute('data-state', 'ok');

    await page.screenshot({
      path: path.join(SHOTS, 'task9-01-health-live.png'),
      fullPage: true,
    });
  });

  test('shows an unavailable badge when the model failed to load', async ({
    page,
  }) => {
    await mockHealth(page, DEGRADED);
    await page.goto('/');

    const badge = page.getByTestId('health-badge');
    await expect(badge).toHaveText(/unavailable/i);
    await expect(badge).toHaveAttribute('data-state', 'degraded');

    await page.screenshot({
      path: path.join(SHOTS, 'task9-02-health-degraded.png'),
      fullPage: true,
    });
  });

  test('distinguishes an unreachable API from a degraded one', async ({
    page,
  }) => {
    await page.route('**/api/health', (route) => route.abort('failed'));
    await page.goto('/');

    const badge = page.getByTestId('health-badge');
    await expect(badge).toHaveAttribute('data-state', 'unreachable');
    // must not claim the model is fine, nor reuse the "degraded" wording
    await expect(badge).not.toHaveText(/live/i);
  });

  test('does not block the form while health is still loading', async ({
    page,
  }) => {
    await page.route('**/api/health', async (route) => {
      await new Promise((r) => setTimeout(r, 1500));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(HEALTHY),
      });
    });
    await page.goto('/');

    // the form is usable immediately, health resolves in the background
    await expect(page.getByTestId('submit-button')).toBeEnabled();
    await expect(page.getByTestId('field-distance_km')).toBeEditable();
  });
});

test.describe('Task 9 — try an example', () => {
  test('fills every field with a valid sample order', async ({ page }) => {
    await mockHealth(page, HEALTHY);
    await page.goto('/');

    // change a couple of fields away from the sample first
    await page.getByTestId('field-distance_km').fill('1.1');
    await page.getByTestId('field-traffic').selectOption('low');

    await page.getByTestId('example-button').click();

    // every control must hold a non-empty value afterwards
    for (const field of [
      'distance_km',
      'age',
      'ratings',
      'pickup_minutes',
      'order_hour',
      'weather',
      'traffic',
      'type_of_order',
      'type_of_vehicle',
      'city_type',
      'festival',
      'vehicle_condition',
      'multiple_deliveries',
    ]) {
      await expect(page.getByTestId(`field-${field}`)).not.toHaveValue('');
    }

    // and the values must have actually changed
    await expect(page.getByTestId('field-distance_km')).not.toHaveValue('1.1');
  });

  test('the example submits successfully', async ({ page }) => {
    await mockHealth(page, HEALTHY);

    let received;
    await page.route('**/api/predict', (route) => {
      received = route.request().postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ prediction_minutes: 24.6 }),
      });
    });

    await page.goto('/');
    await page.getByTestId('example-button').click();
    await page.getByTestId('submit-button').click();

    await expect(page.getByTestId('result-minutes')).toHaveText('25');

    // the sample must respect the API bounds, or it would 422 in production
    expect(received.distance_km).toBeGreaterThan(0);
    expect(received.distance_km).toBeLessThanOrEqual(25);
    expect(received.age).toBeGreaterThanOrEqual(18);
    expect(received.ratings).toBeLessThanOrEqual(5);
    expect(received.order_hour).toBeGreaterThanOrEqual(7);
    expect(received.type_of_vehicle).not.toBe('bicycle');

    await page.screenshot({
      path: path.join(SHOTS, 'task9-03-example-result.png'),
      fullPage: true,
    });
  });
});
