import { test, expect } from '@playwright/test';
import { attachPageErrorCollector, resolveTarget } from './helpers/target';
import { expectAuth0Login } from './helpers/flows';

const target = resolveTarget();

test.describe('marketing and portal gate', { tag: ['@functional', '@apex'] }, () => {
  test.beforeEach(() => {
    test.skip(target.mode !== 'apex', 'baseURL is a tenant host; skip apex suite');
  });

  test('landing shows product copy and both account CTAs', async ({ page }) => {
    const errors = attachPageErrorCollector(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    await expect(page.locator('.marketing-logo')).toHaveText(/c0ll3ct1v3/i);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'MySpace for musicians — but you own it.',
    );
    await expect(page.locator('.marketing-lead')).toContainText('you.c0ll3ct1v3.xyz');
    await expect(page.getByRole('button', { name: 'Artist login' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible();
    await expect(page.locator('.marketing-footer')).toContainText(/Independent artists, owned stack/i);
    await expect(page.locator('.error-message')).toHaveCount(0);
    errors.assert();
  });

  test('Artist login opens Auth0 Universal Login', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: 'Artist login' }).click();
    await expectAuth0Login(page);
    await expect(page).toHaveURL(/auth0\.com/i);
  });

  test('Create account opens Auth0 (signup or login hosted page)', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: 'Create account' }).click();
    await expectAuth0Login(page);
    await expect(page).toHaveURL(/auth0\.com/i);
  });

  for (const path of ['/portal', '/portal/vault', '/portal/homebase', '/portal/epk', '/portal/attestation']) {
    test(`${path} redirects an anonymous user to Auth0`, async ({ page }) => {
      await page.goto(path, { waitUntil: 'domcontentloaded' });
      await expectAuth0Login(page);
    });
  }
});
