import { test, expect } from '@playwright/test';
import { attachPageErrorCollector, resolveTarget } from './helpers/target';

const target = resolveTarget();

test.describe('host parity', { tag: ['@local', '@host-parity'] }, () => {
  test('localhost and 127.0.0.1 both show the marketing landing', async ({ page }) => {
    test.skip(target.env !== 'local', 'host parity is local-only');
    test.skip(target.mode !== 'apex', 'baseURL is a tenant host');

    const parsed = new URL(target.baseURL);
    const port = parsed.port || '3030';
    const origins = [`http://localhost:${port}`, `http://127.0.0.1:${port}`];

    for (const origin of origins) {
      const errors = attachPageErrorCollector(page);
      await page.goto(`${origin}/`, { waitUntil: 'networkidle' });
      const heading = page.getByRole('heading').first();
      await expect(heading, `expected marketing heading at ${origin}`).toHaveText(
        'MySpace for musicians — but you own it.',
      );
      await expect(page.getByRole('button', { name: 'Artist login' })).toBeVisible();
      await expect(page.locator('body')).not.toContainText('@127');
      errors.assert();
    }
  });
});
