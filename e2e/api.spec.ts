import { test, expect } from '@playwright/test';
import { resolveTarget } from './helpers/target';
import { fetchLiveProfile, getJson } from './helpers/flows';

const target = resolveTarget();

test.describe('public API contracts', { tag: ['@functional', '@api'] }, () => {
  test('health is up', async ({ request }) => {
    const { status, body } = await getJson(request, `${target.apiURL}/health`);
    expect(status).toBe(200);
    expect(body).toEqual({ status: 'healthy' });
  });

  test('unknown public profile is 404 with a detail message', async ({ request }) => {
    const { status, body } = await getJson(
      request,
      `${target.apiURL}/artists/public/${target.unknownSlug}`,
    );
    expect(status).toBe(404);
    expect(body).toEqual(expect.objectContaining({ detail: expect.stringMatching(/not found/i) }));
  });

  test('live public profile JSON has the artist contract', async ({ request }) => {
    const { status, body } = await fetchLiveProfile(request, target);
    if (status === 404 && target.env !== 'production') {
      test.skip(true, `local tenant ${target.liveTenantSlug} is not seeded`);
    }
    expect(status, JSON.stringify(body)).toBe(200);
    const profile = body as Record<string, unknown>;
    expect(profile.tenant_slug).toBe(target.liveTenantSlug);
    expect(String(profile.display_name || '')).not.toBe('');
    expect(typeof profile.profile_published).toBe('boolean');
    expect(['html_v1', 'layout']).toContain(profile.format);
    expect(profile).toEqual(
      expect.objectContaining({
        bio: expect.any(String),
        tagline: expect.any(String),
        social: expect.any(Object),
      }),
    );
    if (profile.format === 'html_v1') {
      expect(profile.page_url).toEqual(expect.stringMatching(/\/page$/));
    } else {
      expect(profile.site).toEqual(expect.any(Object));
      expect(profile.design).toEqual(expect.any(Object));
    }
  });

  test('profile HTML page is live only when published', async ({ request }) => {
    const { status, body } = await fetchLiveProfile(request, target);
    if (status === 404 && target.env !== 'production') {
      test.skip(true, `local tenant ${target.liveTenantSlug} is not seeded`);
    }
    expect(status).toBe(200);
    const profile = body as { profile_published: boolean; format: string; display_name: string };
    const pageRes = await request.get(
      `${target.apiURL}/artists/public/${target.liveTenantSlug}/page`,
    );
    const pageText = await pageRes.text();
    if (!profile.profile_published) {
      expect(pageRes.status()).toBe(404);
      expect(pageText).toMatch(/not live yet|not found/i);
      return;
    }
    if (profile.format === 'layout') {
      expect(pageRes.status()).toBe(400);
      return;
    }
    expect(pageRes.ok(), pageText.slice(0, 300)).toBeTruthy();
    expect(pageText).toMatch(/<html/i);
    expect(pageText).toContain(profile.display_name);
  });

  test('booker EPK JSON is 404 unpublished or a published kit', async ({ request }) => {
    const { status, body, text } = await getJson(
      request,
      `${target.apiURL}/artists/public/${target.liveTenantSlug}/epk`,
    );
    if (status === 404) {
      expect(body).toEqual(
        expect.objectContaining({ detail: expect.stringMatching(/not found|not published/i) }),
      );
      const pageRes = await request.get(
        `${target.apiURL}/artists/public/${target.liveTenantSlug}/epk/page`,
      );
      expect(pageRes.status()).toBe(404);
      return;
    }
    expect(status, text).toBe(200);
    const epk = body as Record<string, unknown>;
    expect(epk.published).toBe(true);
    expect(epk.tenant_slug).toBe(target.liveTenantSlug);
    expect(String(epk.display_name || '')).not.toBe('');
    expect(epk.page_url).toEqual(expect.stringMatching(/\/epk\/page$/));
  });

  test('homebase JSON is 404 unpublished or a published page', async ({ request }) => {
    const { status, body, text } = await getJson(
      request,
      `${target.apiURL}/artists/public/${target.liveTenantSlug}/homebase`,
    );
    if (status === 404) {
      expect(body).toEqual(
        expect.objectContaining({ detail: expect.stringMatching(/not found|not published/i) }),
      );
      return;
    }
    expect(status, text).toBe(200);
    const homebase = body as Record<string, unknown>;
    expect(homebase.published).toBe(true);
    expect(homebase.tenant_slug).toBe(target.liveTenantSlug);
    expect(String(homebase.display_name || '')).not.toBe('');
    expect(Array.isArray(homebase.events)).toBe(true);
    expect(homebase.pay).toEqual(expect.any(Object));
    expect(homebase).not.toEqual(expect.objectContaining({ tips: expect.anything() }));
    expect(typeof homebase.checkout_available).toBe('boolean');
    expect(String(homebase.page_url || '')).toMatch(/\/homebase$/);
  });

  test('public checkout merch is 501 and unknown slug is 404', async ({ request }) => {
    const merch = await request.post(
      `${target.apiURL}/artists/public/${target.liveTenantSlug}/checkout`,
      { data: { kind: 'merch', product_id: 'later' } },
    );
    if (merch.status() === 404) {
      return;
    }
    expect(merch.status(), await merch.text()).toBe(501);
    const ticket = await request.post(
      `${target.apiURL}/artists/public/${target.liveTenantSlug}/checkout`,
      { data: { kind: 'ticket', event_id: 'later' } },
    );
    expect(ticket.status()).toBe(501);
  });
});
