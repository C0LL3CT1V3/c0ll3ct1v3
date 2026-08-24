/**
 * Resolve artist tenant slug from hostname (e.g. phillipjames.c0ll3ct1v3.xyz).
 *
 * Dev: http://phillipjames.localhost:3030  → phillipjames
 * Prod: https://phillipjames.c0ll3ct1v3.xyz → phillipjames
 * Apex: http://localhost:3030, http://127.0.0.1:3030, or https://c0ll3ct1v3.xyz → ''
 */

export const PUBLIC_SITE_DOMAIN = 'c0ll3ct1v3.xyz';

function stripBrackets(hostname) {
  return String(hostname || '')
    .toLowerCase()
    .replace(/^\[|\]$/g, '');
}

export function isIPv4Hostname(hostname) {
  return /^(?:\d{1,3}\.){3}\d{1,3}$/.test(stripBrackets(hostname));
}

export function isIPv6Hostname(hostname) {
  const h = stripBrackets(hostname);
  return h.includes(':');
}

export function isIpHostname(hostname) {
  return isIPv4Hostname(hostname) || isIPv6Hostname(hostname);
}

export function isLocalDevHostname(hostname) {
  const h = stripBrackets(hostname);
  return h === 'localhost' || h.endsWith('.localhost') || isIpHostname(h);
}

/**
 * Pure hostname → tenant slug. Empty string means apex (marketing / portal).
 * IPv4/IPv6 addresses are never tenants (127.0.0.1 is not slug "127").
 */
export function subdomainFromHostname(hostname) {
  const h = stripBrackets(hostname);
  if (!h || isIpHostname(h)) {
    return '';
  }

  const labels = h.split('.').filter(Boolean);
  if (labels.length <= 1) {
    return '';
  }

  // phillipjames.localhost / www.localhost
  if (labels[labels.length - 1] === 'localhost') {
    const sub = labels[0];
    return sub === 'www' || sub === 'localhost' ? '' : sub;
  }

  if (h === PUBLIC_SITE_DOMAIN || h === `www.${PUBLIC_SITE_DOMAIN}`) {
    return '';
  }

  // artist.c0ll3ct1v3.xyz (hyphenated slugs allowed)
  if (h.endsWith(`.${PUBLIC_SITE_DOMAIN}`)) {
    const sub = labels[0];
    return sub === 'www' ? '' : sub;
  }

  return '';
}

export function getSubdomain() {
  return subdomainFromHostname(window.location.hostname);
}

export function useTenantSlug() {
  return getSubdomain();
}

export function profilePublicUrl(tenantSlug) {
  if (!tenantSlug) return null;
  const { protocol, port } = window.location;
  const hostname = window.location.hostname;

  if (isLocalDevHostname(hostname)) {
    return `${protocol}//${tenantSlug}.localhost${port ? `:${port}` : ''}`;
  }
  return `${protocol}//${tenantSlug}.${PUBLIC_SITE_DOMAIN}`;
}

/** @deprecated use profilePublicUrl */
export const epkPublicUrl = profilePublicUrl;
