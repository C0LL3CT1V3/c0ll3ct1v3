import { test, expect } from '@playwright/test';
import { resolveTarget } from './helpers/target';

const target = resolveTarget();

test.describe('attestation writes', { tag: ['@local', '@write'] }, () => {
  test.beforeEach(() => {
    test.skip(!target.writesAllowed, 'writes are blocked for this target (local + E2E_ALLOW_WRITES=1 only)');
  });

  test('agent can list claims and create an unsigned draft', async ({ request }) => {
    const headers = {
      Authorization: `Bearer ${target.agentKey}`,
      'X-Tenant-Slug': target.liveTenantSlug,
    };
    const list = await request.get(`${target.apiURL}/manager/attestations`, { headers });
    expect(list.ok(), await list.text()).toBeTruthy();
    const listed = await list.json();
    expect(listed).toEqual(expect.objectContaining({ claims: expect.any(Array) }));

    const created = await request.post(`${target.apiURL}/manager/attestations`, {
      headers,
      data: {
        claim_type: 'consent_cite',
        value: { allowed: true },
        source: 'manual',
      },
    });
    expect(created.status(), await created.text()).toBe(201);
    const body = await created.json();
    expect(body.id).toBeTruthy();
    expect(body.claim_type).toBe('consent_cite');
    expect(body.source).toBe('manual');
    expect(body.status).toBe('draft');
    expect(body.signature).toBeNull();
    expect(body.value).toEqual(expect.objectContaining({ allowed: true }));
  });
});
