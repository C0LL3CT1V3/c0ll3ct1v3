import { expect, type Page } from '@playwright/test';
import {
  isIpHostname,
  isLocalDevHostname,
  PUBLIC_SITE_DOMAIN,
  subdomainFromHostname,
} from '../../frontend/src/hooks/useTenantSlug.js';
import { loadE2eEnv } from './env';

loadE2eEnv();

export type HostMode = 'apex' | 'tenant';
export type HostEnv = 'local' | 'production' | 'unknown';

export type E2ETarget = {
  baseURL: string;
  tenantURL: string | null;
  unknownTenantURL: string | null;
  apiURL: string;
  hostname: string;
  mode: HostMode;
  env: HostEnv;
  tenantSlug: string;
  liveTenantSlug: string;
  unknownSlug: string;
  writesAllowed: boolean;
  agentKey: string;
  authEmail: string;
  authPassword: string;
  authAllowed: boolean;
};

const DEFAULT_LOCAL_UI = 'http://localhost:3030';
const DEFAULT_LOCAL_API = 'http://127.0.0.1:8080';
const DEFAULT_PROD_APEX = `https://${PUBLIC_SITE_DOMAIN}`;
const UNKNOWN_SLUG = 'e2e-missing-artist';

function stripTrailingSlash(url: string) {
  return url.replace(/\/+$/, '');
}

function classifyEnv(hostname: string): HostEnv {
  const h = hostname.toLowerCase().replace(/^\[|\]$/g, '');
  if (isLocalDevHostname(h)) return 'local';
  if (h === PUBLIC_SITE_DOMAIN || h === `www.${PUBLIC_SITE_DOMAIN}` || h.endsWith(`.${PUBLIC_SITE_DOMAIN}`)) {
    return 'production';
  }
  return 'unknown';
}

function defaultApiURL(parsed: URL, env: HostEnv): string {
  if (process.env.E2E_API_URL) {
    return stripTrailingSlash(process.env.E2E_API_URL);
  }
  if (env === 'local') {
    return DEFAULT_LOCAL_API;
  }
  return `${parsed.protocol}//${parsed.host}/api`;
}

function originWithSlug(base: URL, slug: string): string {
  const port = base.port ? `:${base.port}` : '';
  if (isLocalDevHostname(base.hostname)) {
    return `${base.protocol}//${slug}.localhost${port}`;
  }
  return `${base.protocol}//${slug}.${PUBLIC_SITE_DOMAIN}${port}`;
}

export function publicTenantOrigin(baseURL: string, slug: string): string {
  return originWithSlug(new URL(baseURL), slug);
}

function writesAllowedFor(env: HostEnv, hostname: string): boolean {
  if (env === 'production') return false;
  if (!isLocalDevHostname(hostname) && !isIpHostname(hostname)) return false;
  return process.env.E2E_ALLOW_WRITES === '1';
}

function isLoopbackOrLocalTenantHost(hostname: string): boolean {
  const h = hostname.toLowerCase().replace(/^\[|\]$/g, '');
  return h === 'localhost' || h === '127.0.0.1' || h === '::1' || h.endsWith('.localhost');
}

function isInScopeErrorUrl(url: string, pageUrl: string, apiURL: string): boolean {
  let res: URL;
  try {
    res = new URL(url);
  } catch {
    return false;
  }
  try {
    if (res.origin === new URL(pageUrl).origin) return true;
  } catch {
    /* page may still be about:blank */
  }
  try {
    if (res.origin === new URL(apiURL).origin) return true;
  } catch {
    /* ignore */
  }
  return isLoopbackOrLocalTenantHost(res.hostname);
}

/** Resolve the current E2E target from env. Safe to call at spec load time. */
export function resolveTarget(): E2ETarget {
  const baseURL = stripTrailingSlash(process.env.E2E_BASE_URL || DEFAULT_LOCAL_UI);
  const parsed = new URL(baseURL);
  const hostname = parsed.hostname;
  const tenantSlug = subdomainFromHostname(hostname);
  const mode: HostMode = tenantSlug ? 'tenant' : 'apex';
  const env = classifyEnv(hostname);
  const liveTenantSlug =
    process.env.E2E_TENANT_SLUG || (env === 'production' ? 'phillipjames' : 'demo');

  let tenantURL = process.env.E2E_TENANT_URL
    ? stripTrailingSlash(process.env.E2E_TENANT_URL)
    : null;
  if (!tenantURL && mode === 'tenant') {
    tenantURL = baseURL;
  } else if (!tenantURL && (env === 'local' || env === 'production')) {
    tenantURL = originWithSlug(parsed, liveTenantSlug);
  }

  const unknownTenantURL =
    env === 'local' || env === 'production' ? originWithSlug(parsed, UNKNOWN_SLUG) : null;

  return {
    baseURL,
    tenantURL,
    unknownTenantURL,
    apiURL: defaultApiURL(parsed, env),
    hostname,
    mode,
    env,
    tenantSlug,
    liveTenantSlug,
    unknownSlug: UNKNOWN_SLUG,
    writesAllowed: writesAllowedFor(env, hostname),
    agentKey: process.env.E2E_AGENT_KEY ?? 'dev-agent-local',
    authEmail: (process.env.E2E_AUTH_EMAIL || '').trim(),
    authPassword: process.env.E2E_AUTH_PASSWORD || '',
    authAllowed:
      Boolean((process.env.E2E_AUTH_EMAIL || '').trim() && process.env.E2E_AUTH_PASSWORD) &&
      (env === 'local' || (env === 'production' && process.env.E2E_AUTH_ALLOW_PROD === '1')),
  };
}

export const DEFAULT_PROD = {
  apex: DEFAULT_PROD_APEX,
  tenant: `https://phillipjames.${PUBLIC_SITE_DOMAIN}`,
};

export type PageErrorCollector = {
  assert: () => void;
};

/**
 * Fail on page crashes and same-origin / API 4xx-5xx.
 * Ignores Auth0, favicons, and optional URL patterns (expected 404s).
 */
export function attachPageErrorCollector(
  page: Page,
  opts?: { ignoreUrl?: RegExp[] },
): PageErrorCollector {
  const errors: string[] = [];
  const ignore = opts?.ignoreUrl ?? [];

  page.on('pageerror', (err) => {
    errors.push(`pageerror: ${err.message}`);
  });

  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    if (/Download the React DevTools/i.test(text)) return;
    if (/Failed to load resource/i.test(text)) return;
    if (/auth0\.com/i.test(text)) return;
    errors.push(`console.error: ${text}`);
  });

  page.on('response', (res) => {
    if (res.status() < 400) return;
    const url = res.url();
    if (/auth0\.com/i.test(url)) return;
    if (/favicon\.ico(\?|$)/i.test(url)) return;
    if (ignore.some((re) => re.test(url))) return;

    if (!isInScopeErrorUrl(url, page.url(), resolveTarget().apiURL)) return;

    errors.push(`${res.request().method()} ${url} → ${res.status()}`);
  });

  return {
    assert() {
      expect(errors, errors.join('\n')).toEqual([]);
    },
  };
}

export { DEFAULT_LOCAL_UI, DEFAULT_LOCAL_API };
