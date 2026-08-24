import { test, expect } from '@playwright/test';
import { resolveTarget } from './helpers/target';

const target = resolveTarget();

test.describe('machine-readable artist declarations', { tag: ['@functional', '@site'] }, () => {
  test.beforeEach(() => {
    test.skip(!target.tenantURL && target.env === 'unknown', 'no tenant host');
  });

  test('robots.txt is a robots file, not the React SPA', async ({ request }) => {
    if (target.env === 'local') {
      const res = await request.get(`${target.apiURL}/site/robots.txt`, {
        headers: { Host: `${target.liveTenantSlug}.localhost` },
      });
      const text = await res.text();
      expect(res.ok(), text).toBeTruthy();
      expect(text).not.toMatch(/<html/i);
      expect(text).toMatch(/User-Agent:/i);
      expect(text).toMatch(/Content-Usage:/i);
      expect(text).toMatch(/License:/i);
      return;
    }

    test.skip(!target.tenantURL, 'no tenant URL');
    const res = await request.get(`${target.tenantURL}/robots.txt`);
    const text = await res.text();
    const contentType = res.headers()['content-type'] || '';
    expect(contentType, text.slice(0, 180)).not.toMatch(/text\/html/i);
    expect(text).not.toMatch(/<div id="root">/);
    expect(text).toMatch(/User-Agent:/i);
  });

  test('ai.txt and tdmrep.json are declarations, not the SPA', async ({ request }) => {
    if (target.env === 'local') {
      const ai = await request.get(`${target.apiURL}/site/ai.txt`, {
        headers: { Host: `${target.liveTenantSlug}.localhost` },
      });
      const aiText = await ai.text();
      expect(ai.ok(), aiText).toBeTruthy();
      expect(aiText).not.toMatch(/<html/i);
      expect(aiText).toMatch(/train:|cite:|sync:/i);

      const tdm = await request.get(`${target.apiURL}/site/tdmrep.json`, {
        headers: { Host: `${target.liveTenantSlug}.localhost` },
      });
      const tdmText = await tdm.text();
      expect(tdm.ok(), tdmText).toBeTruthy();
      const body = JSON.parse(tdmText);
      expect(body).toEqual(
        expect.objectContaining({
          tdmrep: expect.anything(),
          artist: target.liveTenantSlug,
        }),
      );
      return;
    }

    test.skip(!target.tenantURL, 'no tenant URL');
    const ai = await request.get(`${target.tenantURL}/ai.txt`);
    const aiText = await ai.text();
    expect(ai.headers()['content-type'] || '', aiText.slice(0, 180)).not.toMatch(/text\/html/i);
    expect(aiText).not.toMatch(/<div id="root">/);
    expect(aiText).toMatch(/train:|cite:|sync:/i);

    const tdm = await request.get(`${target.tenantURL}/.well-known/tdmrep.json`);
    const tdmText = await tdm.text();
    expect(tdm.headers()['content-type'] || '', tdmText.slice(0, 180)).not.toMatch(/text\/html/i);
    expect(tdmText).not.toMatch(/<div id="root">/);
    const body = JSON.parse(tdmText);
    expect(body.artist || body.tdmrep).toBeTruthy();
  });
});
