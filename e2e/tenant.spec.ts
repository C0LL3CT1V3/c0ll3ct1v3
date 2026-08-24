import { test, expect } from '@playwright/test';
import { attachPageErrorCollector, resolveTarget } from './helpers/target';
import { fetchLiveProfile } from './helpers/flows';

const target = resolveTarget();

test.describe('public artist pages', { tag: ['@functional', '@tenant'] }, () => {
  test.beforeEach(() => {
    test.skip(!target.tenantURL, 'no tenant URL for this target');
  });

  test('unknown slug is an empty profile, not a marketing or portal page', async ({ page }) => {
    test.skip(!target.unknownTenantURL, 'cannot derive an unknown-tenant origin');
    const errors = attachPageErrorCollector(page, {
      ignoreUrl: [/\/artists\/public\//i],
    });
    await page.goto(`${target.unknownTenantURL}/`, { waitUntil: 'networkidle' });
    await expect(page.locator('.profile-page--empty')).toBeVisible();
    await expect(page.getByRole('heading').first()).toHaveText(`@${target.unknownSlug}`);
    await expect(page.locator('body')).toContainText(/profile not found|this page does not exist yet/i);
    await expect(page.getByRole('button', { name: /artist login/i })).toHaveCount(0);
    errors.assert();
  });

  test('unknown slug EPK shows unpublished, not the SPA shell', async ({ page }) => {
    test.skip(!target.unknownTenantURL, 'cannot derive an unknown-tenant origin');
    const errors = attachPageErrorCollector(page, {
      ignoreUrl: [/\/artists\/public\/.+\/epk/i],
    });
    await page.goto(`${target.unknownTenantURL}/epk`, { waitUntil: 'networkidle' });
    await expect(page.locator('.error-message')).toContainText(
      /epk not found or not published|no artist subdomain/i,
    );
    errors.assert();
  });

  test('unknown slug Homebase shows unpublished, not the SPA shell', async ({ page }) => {
    test.skip(!target.unknownTenantURL, 'cannot derive an unknown-tenant origin');
    const errors = attachPageErrorCollector(page, {
      ignoreUrl: [/\/artists\/public\/.+\/homebase/i],
    });
    await page.goto(`${target.unknownTenantURL}/homebase`, { waitUntil: 'networkidle' });
    await expect(page.locator('.error-message')).toContainText(
      /homebase not found or not published|no artist subdomain/i,
    );
    await expect(page.locator('.profile-page--empty')).toHaveCount(0);
    await expect(page.locator('body')).not.toContainText(/profile not found/i);
    errors.assert();
  });

  test('unknown slug /homebase/ trailing slash is Homebase, not the profile', async ({ page }) => {
    test.skip(!target.unknownTenantURL, 'cannot derive an unknown-tenant origin');
    const errors = attachPageErrorCollector(page, {
      ignoreUrl: [/\/artists\/public\/.+\/homebase/i],
    });
    await page.goto(`${target.unknownTenantURL}/homebase/`, { waitUntil: 'networkidle' });
    await expect(page.locator('.error-message')).toContainText(
      /homebase not found or not published|no artist subdomain/i,
    );
    await expect(page.locator('.profile-page--empty')).toHaveCount(0);
    errors.assert();
  });

  test('live profile UI matches the public API publish state', async ({ page, request }) => {
    const { status, body } = await fetchLiveProfile(request, target);
    if (status === 404) {
      test.skip(target.env !== 'production', `local tenant ${target.liveTenantSlug} is not seeded`);
      expect(status, 'production canary profile must exist').toBe(200);
      return;
    }
    expect(status).toBe(200);
    const profile = body as {
      display_name: string;
      tagline?: string;
      profile_published: boolean;
      format: string;
    };

    const errors = attachPageErrorCollector(page);
    await page.goto(`${target.tenantURL}/`, { waitUntil: 'networkidle' });

    if (!profile.profile_published) {
      await expect(page.locator('.profile-page--draft')).toBeVisible();
      await expect(page.locator('.profile-page-name')).toHaveText(profile.display_name);
      await expect(page.locator('.profile-page-notice')).toContainText(
        /still building their page/i,
      );
      if (profile.tagline) {
        await expect(page.locator('.profile-page-tagline')).toContainText(profile.tagline);
      }
    } else if (profile.format === 'html_v1') {
      await expect(page.locator('.profile-page-iframe')).toBeVisible();
      await expect(page.locator('.profile-page-iframe')).toHaveAttribute(
        'title',
        new RegExp(profile.display_name, 'i'),
      );
    } else {
      await expect(page.locator('.profile-page--layout')).toBeVisible();
      await expect(page.getByRole('heading').first()).toHaveText(profile.display_name);
    }
    errors.assert();
  });

  test('live EPK UI matches whether the booker kit is published', async ({ page, request }) => {
    const epk = await request.get(`${target.apiURL}/artists/public/${target.liveTenantSlug}/epk`);
    const errors = attachPageErrorCollector(page, {
      ignoreUrl: epk.ok() ? [] : [/\/artists\/public\/.+\/epk/i],
    });
    await page.goto(`${target.tenantURL}/epk`, { waitUntil: 'networkidle' });

    if (!epk.ok()) {
      expect(epk.status(), await epk.text()).toBe(404);
      await expect(page.locator('.error-message')).toContainText(/epk not found or not published/i);
      errors.assert();
      return;
    }

    const body = await epk.json();
    await expect(page.locator('.booker-epk-page')).toBeVisible();
    await expect(page.locator('.error-message')).toHaveCount(0);
    if (body.display_name) {
      await expect(page.locator('body')).toContainText(body.display_name);
    }
    errors.assert();
  });

  test('live Homebase UI matches whether the page is published', async ({ page, request }) => {
    const homebase = await request.get(
      `${target.apiURL}/artists/public/${target.liveTenantSlug}/homebase`,
    );
    const errors = attachPageErrorCollector(page, {
      ignoreUrl: homebase.ok() ? [] : [/\/artists\/public\/.+\/homebase/i],
    });
    await page.goto(`${target.tenantURL}/homebase`, { waitUntil: 'networkidle' });

    if (!homebase.ok()) {
      expect(homebase.status(), await homebase.text()).toBe(404);
      await expect(page.locator('.error-message')).toContainText(
        /homebase not found or not published/i,
      );
      errors.assert();
      return;
    }

    const body = await homebase.json();
    await expect(page.locator('.homebase-page')).toBeVisible();
    await expect(page.locator('.error-message')).toHaveCount(0);
    if (body.display_name) {
      await expect(page.locator('.homebase-name')).toHaveText(body.display_name);
    }
    await expect(page.getByRole('heading', { name: 'Calendar' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Venmo' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Cash App' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'PayPal' })).toHaveCount(0);

    const events = Array.isArray(body.events) ? body.events : [];
    if (events.length > 0) {
      await expect(page.locator('.homebase-cal-cell--event').first()).toBeVisible();
      await expect(page.locator('#homebase-cal-detail')).toBeVisible();
      const now = Date.now();
      const focus =
        events.find((ev) => {
          if (!ev || typeof ev !== 'object' || !('start' in ev)) return false;
          const t = Date.parse(String(ev.start || ''));
          return Number.isNaN(t) || t >= now;
        }) || events[0];
      if (focus && typeof focus === 'object' && 'title' in focus && focus.title) {
        await expect(page.locator('#homebase-cal-detail')).toContainText(String(focus.title));
      }
        if (
          focus &&
          typeof focus === 'object' &&
          'ticket_url' in focus &&
          focus.ticket_url
        ) {
          const start = Date.parse(String('start' in focus ? focus.start : ''));
          const isPast = !Number.isNaN(start) && start < now;
          if (!isPast) {
            await expect(
              page.locator('#homebase-cal-detail').getByRole('link', { name: 'Tickets' }),
            ).toBeVisible();
          }
        }
      await page.locator('.homebase-cal-cell--selected').click();
      await expect(page.locator('#homebase-cal-detail')).toHaveCount(0);
      await page.locator('.homebase-cal-cell--event').first().click();
      await expect(page.locator('#homebase-cal-detail')).toBeVisible();
      const withFlyer = events.find(
        (ev) => ev && typeof ev === 'object' && 'image_url' in ev && ev.image_url,
      );
      if (withFlyer && typeof withFlyer === 'object' && 'image_url' in withFlyer) {
        const flyer = page.locator('.homebase-show-flyer').first();
        await expect(flyer).toBeVisible();
        const src = await flyer.getAttribute('src');
        expect(src || '').toMatch(/homebase\/media\//);
        if (target.env === 'local') {
          expect(src || '').not.toMatch(/c0ll3ct1v3\.xyz/);
        }
      }
    } else {
      await expect(page.locator('.homebase-cal-cell--event')).toHaveCount(0);
    }
    errors.assert();
  });
});
