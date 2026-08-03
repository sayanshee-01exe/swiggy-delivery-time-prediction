import { test, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = path.resolve(__dirname, '../../..', 'tests/screenshots');

// These must stay identical to the pydantic bounds in scripts/api_payload.py.
// Anything looser lets the UI submit a request the API will reject.
const NUMERIC_BOUNDS = [
  { field: 'distance_km', min: '0.1', max: '25' },
  { field: 'age', min: '18', max: '65' },
  { field: 'ratings', min: '1', max: '5' },
  { field: 'pickup_minutes', min: '1', max: '60' },
  { field: 'order_hour', min: '7', max: '23' },
];

const SELECT_OPTIONS = [
  { field: 'weather', values: ['sunny', 'stormy', 'sandstorms', 'cloudy', 'fog', 'windy'] },
  { field: 'traffic', values: ['low', 'medium', 'high', 'jam'] },
  { field: 'type_of_order', values: ['snack', 'meal', 'drinks', 'buffet'] },
  // no "bicycle": the fitted encoder has never seen it
  { field: 'type_of_vehicle', values: ['motorcycle', 'scooter', 'electric_scooter'] },
  { field: 'city_type', values: ['metropolitian', 'urban', 'semi-urban'] },
  { field: 'festival', values: ['no', 'yes'] },
  { field: 'vehicle_condition', values: ['0', '1', '2', '3'] },
  { field: 'multiple_deliveries', values: ['0', '1', '2', '3'] },
];

test.describe('Task 5 — prediction form', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('renders every control', async ({ page }) => {
    for (const { field } of [...NUMERIC_BOUNDS, ...SELECT_OPTIONS]) {
      await expect(page.getByTestId(`field-${field}`)).toBeVisible();
    }
    await expect(page.getByTestId('submit-button')).toBeVisible();

    await page.screenshot({
      path: path.join(SHOTS, 'task5-01-form-desktop.png'),
      fullPage: true,
    });
  });

  test('every control has a visible label', async ({ page }) => {
    for (const { field } of [...NUMERIC_BOUNDS, ...SELECT_OPTIONS]) {
      const control = page.getByTestId(`field-${field}`);
      const id = await control.getAttribute('id');
      expect(id, `${field} needs an id to be labelled`).toBeTruthy();
      await expect(page.locator(`label[for="${id}"]`)).toBeVisible();
    }
  });

  for (const { field, min, max } of NUMERIC_BOUNDS) {
    test(`${field} input bounds mirror the API`, async ({ page }) => {
      const input = page.getByTestId(`field-${field}`);
      await expect(input).toHaveAttribute('type', 'number');
      await expect(input).toHaveAttribute('min', min);
      await expect(input).toHaveAttribute('max', max);
    });
  }

  for (const { field, values } of SELECT_OPTIONS) {
    test(`${field} offers exactly the accepted values`, async ({ page }) => {
      const options = await page
        .getByTestId(`field-${field}`)
        .locator('option')
        .evaluateAll((els) => els.map((e) => e.value));
      expect(options).toEqual(values);
    });
  }

  test('every field starts with a valid default', async ({ page }) => {
    for (const { field } of [...NUMERIC_BOUNDS, ...SELECT_OPTIONS]) {
      const value = await page.getByTestId(`field-${field}`).inputValue();
      expect(value, `${field} must not start empty`).not.toBe('');
    }
  });

  test('lays out in two columns on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    const first = await page.getByTestId('field-distance_km').boundingBox();
    const second = await page.getByTestId('field-age').boundingBox();
    // side by side: same row, different columns
    expect(Math.abs(first.y - second.y)).toBeLessThan(4);
    expect(second.x).toBeGreaterThan(first.x);
  });

  test('collapses to one column on mobile without overflow', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 720 });
    const first = await page.getByTestId('field-distance_km').boundingBox();
    const second = await page.getByTestId('field-age').boundingBox();
    // stacked: same column, different rows
    expect(Math.abs(first.x - second.x)).toBeLessThan(4);
    expect(second.y).toBeGreaterThan(first.y);

    const overflows = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth
    );
    expect(overflows).toBe(false);

    await page.screenshot({
      path: path.join(SHOTS, 'task5-02-form-mobile.png'),
      fullPage: true,
    });
  });
});
