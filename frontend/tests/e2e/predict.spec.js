import { test, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = path.resolve(__dirname, '../../..', 'tests/screenshots');

const mockPredict = (page, handler) =>
  page.route('**/api/predict', handler);

test.describe('Task 6 — submitting a prediction', () => {
  test('shows the predicted minutes on success', async ({ page }) => {
    await mockPredict(page, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ prediction_minutes: 27.4 }),
      })
    );

    await page.goto('/');
    await expect(page.getByTestId('result-card')).toBeHidden();

    await page.getByTestId('submit-button').click();

    const result = page.getByTestId('result-card');
    await expect(result).toBeVisible();
    await expect(page.getByTestId('result-minutes')).toHaveText('27');

    await page.screenshot({
      path: path.join(SHOTS, 'task6-01-prediction-success.png'),
      fullPage: true,
    });
  });

  test('posts the form values as JSON', async ({ page }) => {
    let received;
    await mockPredict(page, (route) => {
      received = route.request().postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ prediction_minutes: 20 }),
      });
    });

    await page.goto('/');
    await page.getByTestId('field-distance_km').fill('12.5');
    await page.getByTestId('field-traffic').selectOption('jam');
    await page.getByTestId('submit-button').click();
    await expect(page.getByTestId('result-card')).toBeVisible();

    expect(received.distance_km).toBe(12.5);
    expect(received.traffic).toBe('jam');
    // numeric selects must not arrive as strings
    expect(typeof received.vehicle_condition).toBe('number');
  });

  test('disables the button and shows progress while in flight', async ({
    page,
  }) => {
    let release;
    const gate = new Promise((resolve) => {
      release = resolve;
    });

    await mockPredict(page, async (route) => {
      await gate;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ prediction_minutes: 18 }),
      });
    });

    await page.goto('/');
    await page.getByTestId('submit-button').click();

    const button = page.getByTestId('submit-button');
    await expect(button).toBeDisabled();
    await expect(button).toHaveText(/Predicting/);

    await page.screenshot({
      path: path.join(SHOTS, 'task6-02-loading-state.png'),
      fullPage: true,
    });

    release();
    await expect(button).toBeEnabled();
    await expect(page.getByTestId('result-minutes')).toHaveText('18');
  });

  test('surfaces the server error message on a 503', async ({ page }) => {
    await mockPredict(page, (route) =>
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Model is unavailable; the service failed to load it.',
        }),
      })
    );

    await page.goto('/');
    await page.getByTestId('submit-button').click();

    const error = page.getByTestId('error-message');
    await expect(error).toBeVisible();
    await expect(error).toContainText('Model is unavailable');
    await expect(page.getByTestId('result-card')).toBeHidden();

    await page.screenshot({
      path: path.join(SHOTS, 'task6-03-server-error.png'),
      fullPage: true,
    });
  });

  test('surfaces a field message from a 422', async ({ page }) => {
    await mockPredict(page, (route) =>
      route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: [
            {
              type: 'less_than_equal',
              loc: ['body', 'distance_km'],
              msg: 'Input should be less than or equal to 25',
            },
          ],
        }),
      })
    );

    await page.goto('/');
    await page.getByTestId('submit-button').click();

    const error = page.getByTestId('error-message');
    await expect(error).toBeVisible();
    await expect(error).toContainText('distance_km');
    await expect(error).toContainText('less than or equal to 25');
  });

  test('shows a readable message when the network fails', async ({ page }) => {
    await mockPredict(page, (route) => route.abort('failed'));

    await page.goto('/');
    await page.getByTestId('submit-button').click();

    const error = page.getByTestId('error-message');
    await expect(error).toBeVisible();
    await expect(error).not.toHaveText('');
    // a raw "TypeError: Failed to fetch" is not an acceptable user message
    await expect(error).not.toContainText('TypeError');
  });

  test('a new submission clears the previous error', async ({ page }) => {
    let fail = true;
    await mockPredict(page, (route) =>
      fail
        ? route.fulfill({
            status: 503,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'temporarily down' }),
          })
        : route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ prediction_minutes: 31 }),
          })
    );

    await page.goto('/');
    await page.getByTestId('submit-button').click();
    await expect(page.getByTestId('error-message')).toBeVisible();

    fail = false;
    await page.getByTestId('submit-button').click();
    await expect(page.getByTestId('result-minutes')).toHaveText('31');
    await expect(page.getByTestId('error-message')).toBeHidden();
  });
});
