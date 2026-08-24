import { test, expect } from '@playwright/test';
import { attachPageErrorCollector, resolveTarget } from './helpers/target';
import { loginAsTester } from './helpers/flows';

const target = resolveTarget();

test.describe('signed-in portal', { tag: ['@functional', '@auth'] }, () => {
  test.describe.configure({ timeout: 60_000 });

  test.beforeEach(() => {
    test.skip(!target.authAllowed, 'Set E2E_AUTH_EMAIL and E2E_AUTH_PASSWORD in e2e/.env (local only unless E2E_AUTH_ALLOW_PROD=1)');
    test.skip(target.mode !== 'apex', 'portal lives on the apex host');
  });

  test('Vault loads the workbench after Auth0 login', async ({ page }) => {
    const errors = attachPageErrorCollector(page);
    await loginAsTester(page);
    await page.goto('/portal/vault', { waitUntil: 'networkidle' });

    await expect(page.getByRole('navigation', { name: 'Portal sections' })).toBeVisible();
    const nav = page.getByRole('navigation', { name: 'Portal sections' });
    await expect(nav.getByRole('link', { name: 'Vault', exact: true })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Homebase', exact: true })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'EPK', exact: true })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Attestation', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Vault' })).toBeVisible();
    await expect(page.locator('body')).toContainText(/All your IP in one place/i);
    await expect(page.getByText('Choose files')).toBeVisible();
    await expect(page.getByRole('button', { name: /new folder/i })).toBeVisible();
    await expect(page.locator('body')).not.toContainText(/Not signed in or session expired/i);
    await expect(page.locator('body')).not.toContainText(/Failed to load workbench/i);
    await expect(page.locator('body')).not.toContainText(/Failed to load artist profile/i);
    errors.assert();
  });

  test('Homebase studio shows publish and view live actions', async ({ page }) => {
    const errors = attachPageErrorCollector(page);
    await loginAsTester(page);
    await page.goto('/portal/homebase', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'Homebase' })).toBeVisible();
    await expect(page.locator('body')).toContainText(/events calendar and Square checkout/i);
    await expect(page.getByRole('button', { name: 'Publish Homebase' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save draft' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add event' })).toBeVisible();
    await expect(page.getByLabel('Venmo')).toHaveCount(0);
    await expect(page.getByPlaceholder('https://square.link/')).toHaveCount(0);
    await page.getByRole('button', { name: 'Add event' }).click();
    await expect(page.locator('.homebase-event-row').last().locator('.epk-booker-slot-header')).toContainText(
      'Flyer',
    );
    const vaultList = page.locator('.portal-studio-panels--homebase .portal-file-list');
    await expect(vaultList).toBeVisible();
    await expect
      .poll(async () => vaultList.evaluate((el) => getComputedStyle(el).overflowY))
      .toMatch(/auto|scroll/);
    await expect(page.locator('.error-message')).toHaveCount(0);
    errors.assert();
  });

  test('EPK studio shows preview and publish actions', async ({ page }) => {
    const errors = attachPageErrorCollector(page);
    await loginAsTester(page);
    await page.goto('/portal/epk', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'EPK' })).toBeVisible();
    await expect(page.locator('body')).toContainText(/Booker-ready press kit/i);
    await expect(page.getByRole('button', { name: 'Preview EPK' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Publish EPK' })).toBeVisible();
    await expect(page.locator('.error-message')).toHaveCount(0);
    errors.assert();
  });

  test('Attestation studio is reachable and lists vault audio or an empty hint', async ({ page }) => {
    const errors = attachPageErrorCollector(page);
    await loginAsTester(page);
    await page.goto('/portal/attestation', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'Attestation' })).toBeVisible();
    await expect(page.locator('body')).toContainText(/signed record machines will see/i);
    await expect(page.locator('body')).toContainText(
      /Upload a track in Vault first|Select a track to review|Audio in Vault/i,
    );
    await expect(page.locator('body')).not.toContainText(/Failed to load claims/i);
    errors.assert();
  });
});
