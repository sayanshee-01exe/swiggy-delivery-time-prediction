import { test, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Screenshots live at the repo root per the sprint convention:
// frontend/tests/e2e -> ../../.. -> repo root
const SHOTS = path.resolve(__dirname, '../../..', 'tests/screenshots');

test.describe('Task 1 — frontend scaffold', () => {
  test('dev server serves the app shell', async ({ page }) => {
    await page.goto('/');

    const heading = page.getByTestId('app-heading');
    await expect(heading).toBeVisible();
    await expect(heading).toHaveText('Delivery Time Predictor');

    await page.screenshot({
      path: path.join(SHOTS, 'task1-01-dev-server-loaded.png'),
      fullPage: true,
    });
  });

  test('tailwind stylesheet is compiled and applied', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('app-heading')).toBeVisible();

    // `text-3xl` resolves to 1.875rem = 30px. The browser default for an <h1>
    // is 2em = 32px, so this only passes if Tailwind actually compiled.
    const fontSize = await page
      .getByTestId('app-heading')
      .evaluate((el) => getComputedStyle(el).fontSize);
    expect(fontSize).toBe('30px');

    // Tailwind's preflight zeroes the body margin; the UA default is 8px.
    const bodyMargin = await page.evaluate(
      () => getComputedStyle(document.body).margin
    );
    expect(bodyMargin).toBe('0px');
  });

  test('renders without horizontal overflow on a 360px viewport', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 720 });
    await page.goto('/');
    await expect(page.getByTestId('app-heading')).toBeVisible();

    const overflows = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth
    );
    expect(overflows).toBe(false);

    await page.screenshot({
      path: path.join(SHOTS, 'task1-02-mobile-360px.png'),
      fullPage: true,
    });
  });
});
