import { test, expect } from '@playwright/test';
import { attachPageErrorCollector, resolveTarget } from './helpers/target';

const target = resolveTarget();

test.describe('client bugtracker widget', { tag: ['@apex'] }, () => {
  test.beforeEach(() => {
    test.skip(target.mode !== 'apex', 'baseURL is a tenant host; skip apex suite');
    test.skip(target.env !== 'local', 'bugtracker e2e is local-only (mocked POST)');
  });

  test('opens a fixture modal and submits a mocked report', async ({ page }) => {
    const errors = attachPageErrorCollector(page, {
      ignoreUrl: [/\/__bugtracker-reports/i, /\/prod\/reports/i, /execute-api/i],
    });

    const fulfillReport = async (route) => {
      const body = route.request().postDataJSON();
      expect(body.summary).toMatch(/vault/i);
      expect(body.type).toBe('bug');
      expect(body.image_data_url).toMatch(/^data:image\/jpeg/);
      expect(body.page_url).toContain('bugtracker=1');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, issue_url: 'https://github.com/example/c0ll3ct1v3/issues/1' }),
      });
    };
    await page.route('**/__bugtracker-reports', fulfillReport);
    await page.route('**/prod/reports', fulfillReport);

    await page.goto('/?bugtracker=1', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('bugtracker-modal')).toBeVisible();
    await page.getByTestId('bugtracker-summary').fill('Vault upload hangs after choosing a file');
    await page.getByTestId('bugtracker-submit').click();
    await expect(page.getByTestId('bugtracker-modal')).toHaveCount(0);
    await expect(page.getByRole('status')).toContainText(/Filed https:\/\/github.com\/example/i);
    errors.assert();
  });
});
