import React, { useEffect, useMemo, useState } from 'react';
import { getSubdomain } from '../../hooks/useTenantSlug';

function parseEpkDocument(htmlText) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlText, 'text/html');
  const styles = Array.from(doc.querySelectorAll('style'))
    .map((node) => node.textContent || '')
    .join('\n');
  const bodyHtml = doc.body?.innerHTML?.trim() || htmlText;
  return { styles, bodyHtml };
}

function BookerEpkPage() {
  const tenantSlug = getSubdomain();
  const [html, setHtml] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const parsed = useMemo(() => (html ? parseEpkDocument(html) : null), [html]);

  useEffect(() => {
    if (!tenantSlug) {
      setError('No artist subdomain.');
      setLoading(false);
      return;
    }
    const apiBase = (process.env.REACT_APP_API_URL || '/api').replace(/\/$/, '');
    const url = apiBase.startsWith('http')
      ? `${apiBase}/artists/public/${tenantSlug}/epk/page`
      : `${window.location.origin}${apiBase}/artists/public/${tenantSlug}/epk/page`;
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error('EPK not found or not published.');
        return res.text();
      })
      .then((text) => {
        setHtml(text);
        setError('');
      })
      .catch((err) => setError(err.message || 'Failed to load EPK.'))
      .finally(() => setLoading(false));
  }, [tenantSlug]);

  if (loading) return <p className="portal-loading">Loading press kit…</p>;
  if (error) return <div className="error-message">{error}</div>;
  if (!parsed) return null;

  return (
    <div className="booker-epk-page">
      {parsed.styles ? <style>{parsed.styles}</style> : null}
      <div
        className="booker-epk-page__content"
        dangerouslySetInnerHTML={{ __html: parsed.bodyHtml }}
      />
    </div>
  );
}

export default BookerEpkPage;
