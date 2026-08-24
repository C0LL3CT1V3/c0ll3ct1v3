import { expect, type Locator, type Page } from '@playwright/test';

function isHomebaseConfigGet(res: { url: () => string; request: () => { method: () => string } }) {
  const url = res.url();
  const method = res.request().method();
  return method === 'GET' && url.includes('/artists/me/homebase') && !url.includes('/publish');
}

function isHomebaseConfigPatch(res: { url: () => string; request: () => { method: () => string } }) {
  const url = res.url();
  const method = res.request().method();
  return method === 'PATCH' && url.includes('/artists/me/homebase') && !url.includes('/publish');
}

function isHomebasePublish(res: { url: () => string; request: () => { method: () => string } }) {
  return res.request().method() === 'POST' && res.url().includes('/artists/me/homebase/publish');
}

export function pad2(n: number) {
  return String(n).padStart(2, '0');
}

export function toDatetimeLocalValue(d: Date) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

export function futureShowStart(monthsAhead = 4) {
  const start = new Date();
  start.setMonth(start.getMonth() + monthsAhead);
  start.setDate(15);
  start.setHours(20, 0, 0, 0);
  return start;
}

export function monthLabel(d: Date) {
  return d.toLocaleString('en-US', { month: 'long', year: 'numeric' });
}

export async function fillDatetimeLocal(input: Locator, value: string) {
  await input.evaluate((el, v) => {
    const proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
    proto?.set?.call(el, v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
}

export async function openHomebaseStudio(page: Page) {
  const loaded = page.waitForResponse((res) => isHomebaseConfigGet(res) && res.ok());
  await page.goto('/portal/homebase', { waitUntil: 'domcontentloaded' });
  const res = await loaded;
  const body = (await res.json().catch(() => ({}))) as { config?: { events?: unknown[] } };
  const eventCount = Array.isArray(body?.config?.events) ? body.config.events.length : 0;
  await expect(page.getByRole('button', { name: 'Add event' })).toBeVisible();
  await expect(page.locator('.homebase-event-row')).toHaveCount(eventCount);
  return eventCount;
}

export async function fillNewHomebaseEvent(
  page: Page,
  fields: { title: string; start: Date; venue: string; city: string; ticketUrl: string; notes?: string },
) {
  const before = await page.locator('.homebase-event-row').count();
  await page.getByRole('button', { name: 'Add event' }).click();
  await expect(page.locator('.homebase-event-row')).toHaveCount(before + 1);
  const row = page.locator('.homebase-event-row').last();
  await row.getByLabel('Title').fill(fields.title);
  await fillDatetimeLocal(row.locator('input[type="datetime-local"]'), toDatetimeLocalValue(fields.start));
  await row.getByLabel('Venue').fill(fields.venue);
  await row.getByLabel('City').fill(fields.city);
  await row.getByLabel('Ticket URL').fill(fields.ticketUrl);
  if (fields.notes) {
    await row.getByLabel('Notes').fill(fields.notes);
  }
  await expect(row.getByLabel('Title')).toHaveValue(fields.title);
  return row;
}

export async function publishHomebase(page: Page) {
  await page.locator('.homebase-studio').evaluate((el) => {
    el.scrollTop = 0;
  });
  const patched = page.waitForResponse(isHomebaseConfigPatch);
  const published = page.waitForResponse(isHomebasePublish);
  await page.getByRole('button', { name: 'Publish Homebase' }).click();
  const patchRes = await patched;
  expect(patchRes.ok(), `save before publish: ${patchRes.url()} ${await patchRes.text()}`).toBeTruthy();
  const publishRes = await published;
  expect(publishRes.ok(), `publish: ${publishRes.url()} ${await publishRes.text()}`).toBeTruthy();
}

export async function readPortalTenantSlug(page: Page) {
  const slug = (await page.locator('.portal-tenant-slug code').innerText()).trim();
  expect(slug, 'portal tenant slug').toBeTruthy();
  return slug;
}

export async function showCalendarMonth(page: Page, when: Date) {
  const target = monthLabel(when);
  for (let i = 0; i < 24; i += 1) {
    const label = (await page.locator('.homebase-cal-month').innerText()).trim();
    if (label === target) return;
    const shown = Date.parse(`1 ${label}`);
    if (!Number.isNaN(shown) && shown > when.getTime()) {
      await page.getByRole('button', { name: 'Previous' }).click();
    } else {
      await page.getByRole('button', { name: 'Next' }).click();
    }
  }
  throw new Error(`Could not reach calendar month ${target}`);
}

export async function openPublishedShow(page: Page, start: Date, title: string) {
  await expect(page.locator('.homebase-page')).toBeVisible();
  const detail = page.locator('#homebase-cal-detail');
  if ((await detail.isVisible()) && (await detail.getByText(title).count())) {
    return detail;
  }

  await showCalendarMonth(page, start);
  const dayRe = new RegExp(`${monthLabel(start)} ${start.getDate()}\\b`);
  const dayBtn = page.getByRole('button', { name: dayRe });
  await expect(dayBtn).toBeVisible();
  if ((await dayBtn.getAttribute('aria-pressed')) !== 'true') {
    await dayBtn.click();
  }
  await expect(detail).toBeVisible();
  await expect(detail).toContainText(title);
  return detail;
}

export async function removeHomebaseEventsByTitlePrefix(page: Page, prefix: string) {
  if (page.isClosed()) return;
  await openHomebaseStudio(page);
  let removed = 0;
  for (let i = 0; i < 20; i += 1) {
    const row = page.locator('.homebase-event-row').filter({ hasText: prefix }).first();
    if ((await row.count()) === 0) break;
    await row.getByRole('button', { name: 'Remove' }).click();
    removed += 1;
  }
  if (!removed) return;
  await page.locator('.homebase-studio').evaluate((el) => {
    el.scrollTop = 0;
  });
  const saved = page.waitForResponse(isHomebaseConfigPatch);
  await page.getByRole('button', { name: 'Save draft' }).click();
  const res = await saved;
  expect(res.ok(), await res.text()).toBeTruthy();
}
