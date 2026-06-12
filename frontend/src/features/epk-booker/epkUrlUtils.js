/** Rewrite backend preview URLs that still point at localhost (missing EPK_SIM_BASE_URL). */
export function normalizeApiUrl(url) {
  if (!url) return url;
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.hostname !== 'localhost' && parsed.hostname !== '127.0.0.1') {
      return url;
    }
    const apiBase = (process.env.REACT_APP_API_URL || '/api').replace(/\/$/, '');
    const absoluteApi = apiBase.startsWith('http')
      ? apiBase
      : `${window.location.origin}${apiBase}`;
    return `${absoluteApi}${parsed.pathname}${parsed.search}`;
  } catch {
    return url;
  }
}
