import { test, expect } from '@playwright/test';
import { attachPageErrorCollector, publicTenantOrigin, resolveTarget } from './helpers/target';
import { loginAsTester } from './helpers/flows';
import {
  fillNewHomebaseEvent,
  futureShowStart,
  openHomebaseStudio,
  openPublishedShow,
  publishHomebase,
  readPortalTenantSlug,
  removeHomebaseEventsByTitlePrefix,
} from './helpers/homebase';

const target = resolveTarget();
const E2E_TITLE_PREFIX = 'E2E tickets';

test.describe('Homebase event tickets', { tag: ['@auth', '@write', '@local'] }, () => {
  test.describe.configure({ timeout: 120_000 });

  test.beforeEach(() => {
    test.skip(!target.authAllowed, 'Set E2E_AUTH_EMAIL and E2E_AUTH_PASSWORD in e2e/.env');
    test.skip(!target.writesAllowed, 'writes are blocked for this target (local + E2E_ALLOW_WRITES=1 only)');
    test.skip(target.mode !== 'apex', 'portal lives on the apex host');
    test.skip(target.env !== 'local', 'do not create Homebase events against production');
  });

  test('create an event, publish, click it, and buy a ticket', async ({ page }) => {
    const stamp = Date.now();
    const title = `${E2E_TITLE_PREFIX} ${stamp}`;
    const ticketUrl = `https://example.com/e2e-tickets/${stamp}`;
    const start = futureShowStart();
    const venue = 'E2E Hall';
    const city = 'Denver';

    const errors = attachPageErrorCollector(page);
    await loginAsTester(page);
    await openHomebaseStudio(page);
    await removeHomebaseEventsByTitlePrefix(page, E2E_TITLE_PREFIX);

    try {
      await fillNewHomebaseEvent(page, {
        title,
        start,
        venue,
        city,
        ticketUrl,
        notes: 'Door at 7, show at 8',
      });
      await publishHomebase(page);

      const slug = await readPortalTenantSlug(page);
      const liveUrl = `${publicTenantOrigin(target.baseURL, slug)}/homebase`;

      await page.goto(liveUrl, { waitUntil: 'networkidle' });
      const detail = await openPublishedShow(page, start, title);
      const show = detail.locator('.homebase-show').filter({ hasText: title });
      await expect(show).toBeVisible();
      await expect(show).toContainText(venue);
      await expect(show).toContainText(city);

      const tickets = show.getByRole('link', { name: 'Tickets' });
      await expect(tickets).toBeVisible();
      await expect(tickets).toHaveAttribute('href', ticketUrl);

      const popupPromise = page.waitForEvent('popup');
      await tickets.click();
      const checkout = await popupPromise;
      await checkout.waitForLoadState('domcontentloaded');
      expect(checkout.url()).toContain(`example.com/e2e-tickets/${stamp}`);
      await checkout.close();
      errors.assert();
    } finally {
      await removeHomebaseEventsByTitlePrefix(page, E2E_TITLE_PREFIX);
    }
  });
});
