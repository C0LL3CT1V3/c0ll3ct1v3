import React, { useCallback, useEffect, useRef, useState } from 'react';
import { getSubdomain } from '../../hooks/useTenantSlug';

function BookerEpkPage() {
  const tenantSlug = getSubdomain();
  const [html, setHtml] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const iframeRef = useRef(null);

  const resizeIframe = useCallback(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    try {
      const doc = iframe.contentDocument || iframe.contentWindow?.document;
      if (!doc?.body) return;
      const height = Math.max(
        doc.body.scrollHeight,
        doc.documentElement?.scrollHeight || 0,
      );
      iframe.style.height = `${height}px`;
    } catch {
      // srcDoc is same-origin; ignore if unavailable during load
    }
  }, []);

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

  useEffect(() => {
    if (!html) return undefined;
    const t = window.setTimeout(resizeIframe, 0);
    window.addEventListener('resize', resizeIframe);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener('resize', resizeIframe);
    };
  }, [html, resizeIframe]);

  if (loading) return <p className="portal-loading">Loading press kit…</p>;
  if (error) return <div className="error-message">{error}</div>;
  if (html) {
    return (
      <iframe
        ref={iframeRef}
        title="Booker EPK"
        className="booker-epk-iframe"
        srcDoc={html}
        onLoad={resizeIframe}
      />
    );
  }
  return null;
}

export default BookerEpkPage;
