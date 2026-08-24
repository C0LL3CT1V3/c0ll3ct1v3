import { expect, type APIRequestContext, type Page } from '@playwright/test';
import { attachPageErrorCollector, resolveTarget, type E2ETarget } from './target';
import { authEmail, authPassword } from './env';

export async function getJson(request: APIRequestContext, url: string) {
  const res = await request.get(url);
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { res, status: res.status(), body, text };
}

export async function fetchLiveProfile(request: APIRequestContext, target: E2ETarget) {
  return getJson(request, `${target.apiURL}/artists/public/${target.liveTenantSlug}`);
}

export async function expectAuth0Login(page: Page) {
  await expect
    .poll(async () => {
      const url = page.url();
      const body = await page.locator('body').innerText().catch(() => '');
      return (
        /auth0\.com/i.test(url) ||
        /loading authentication|redirecting to login|auth0 configuration error/i.test(body)
      );
    }, { timeout: 20_000 })
    .toBeTruthy();

  if (!/auth0\.com/i.test(page.url())) {
    return;
  }

  await expect(page.getByLabel(/email/i).first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByLabel(/password/i).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /^continue$/i }).first()).toBeVisible();
}

export async function loginAsTester(page: Page) {
  const email = authEmail();
  const password = authPassword();
  if (!email || !password) {
    throw new Error('E2E_AUTH_EMAIL and E2E_AUTH_PASSWORD must be set in e2e/.env');
  }

  await page.goto('/', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Artist login' }).click();
  await expectAuth0Login(page);
  await expect(page).toHaveURL(/auth0\.com/i);

  await page.getByLabel(/email/i).first().fill(email);

  const passwordField = page.getByLabel(/password/i).first();
  const passwordVisible = await passwordField.isVisible().catch(() => false);
  if (passwordVisible) {
    await passwordField.fill(password);
    await page.getByRole('button', { name: /^continue$/i }).first().click();
  } else {
    await page.getByRole('button', { name: /^continue$/i }).first().click();
    await expect(page.getByLabel(/password/i).first()).toBeVisible({ timeout: 15_000 });
    await page.getByLabel(/password/i).first().fill(password);
    await page.getByRole('button', { name: /^continue$/i }).first().click();
  }

  try {
    await page.waitForURL((url) => !/auth0\.com/i.test(url.hostname), { timeout: 30_000 });
  } catch (err) {
    const body = await page.locator('body').innerText().catch(() => '');
    if (/verify your identity|multi-factor|authenticator|one-time/i.test(body)) {
      throw new Error('Auth0 asked for MFA. Use a password-only tester user (MFA off).');
    }
    if (/wrong email or password|invalid.*password|user does not exist/i.test(body)) {
      throw new Error('Auth0 rejected E2E_AUTH_EMAIL / E2E_AUTH_PASSWORD.');
    }
    throw err;
  }
  await page.waitForURL(/\/portal/, { timeout: 20_000 });
  await expect(page.getByRole('button', { name: /logout/i })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/loading your studio timed out/i)).toHaveCount(0);
  await expect(page.getByText('Loading your studio…')).toHaveCount(0, { timeout: 20_000 });
}

export async function openAndCollect(page: Page, url: string, opts?: { ignoreUrl?: RegExp[] }) {
  const errors = attachPageErrorCollector(page, opts);
  await page.goto(url, { waitUntil: 'networkidle' });
  return errors;
}

export { expect, resolveTarget };
