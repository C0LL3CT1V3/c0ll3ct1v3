/**
 * Resolve artist tenant slug from hostname (e.g. phillipjames.c0ll3ct1v3.xyz).
 *
 * Dev: http://phillipjames.localhost:3030  → phillipjames
 * Prod: https://phillipjames.c0ll3ct1v3.xyz → phillipjames
 * Apex: http://localhost:3030 or https://c0ll3ct1v3.xyz → ''
 */

function isLocalDevHostname(hostname) {
  const h = hostname.toLowerCase();
  return h === 'localhost' || h.endsWith('.localhost') || h === '127.0.0.1';
}

export function getSubdomain() {
  const hostname = window.location.hostname.toLowerCase();
  const labels = hostname.split('.').filter(Boolean);

  if (labels.length <= 1) {
    return '';
  }

  // phillipjames.localhost (two labels; *.localhost resolves in modern browsers)
  if (labels[labels.length - 1] === 'localhost') {
    const sub = labels[0];
    return sub === 'www' ? '' : sub;
  }

  // artist.c0ll3ct1v3.xyz (three or more labels)
  if (labels.length >= 3) {
    const sub = labels[0];
    return sub === 'www' ? '' : sub;
  }

  // apex: c0ll3ct1v3.xyz, www.c0ll3ct1v3.xyz handled above as www → ''
  return '';
}

export function useTenantSlug() {
  return getSubdomain();
}

export function epkPublicUrl(tenantSlug) {
  if (!tenantSlug) return null;
  const { protocol, port } = window.location;
  const hostname = window.location.hostname;

  if (isLocalDevHostname(hostname)) {
    return `${protocol}//${tenantSlug}.localhost${port ? `:${port}` : ''}`;
  }
  return `${protocol}//${tenantSlug}.c0ll3ct1v3.xyz`;
}
