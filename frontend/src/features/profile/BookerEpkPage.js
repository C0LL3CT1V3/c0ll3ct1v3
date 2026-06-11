import React, { useEffect, useState } from 'react';
import { getSubdomain } from '../../hooks/useTenantSlug';

function BookerEpkPage() {
  const tenantSlug = getSubdomain();
  const [html, setHtml] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantSlug) {
      setError('No artist subdomain.');
      setLoading(false);
      return;
    }
    const apiBase = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8080';
    fetch(`${apiBase}/artists/public/${tenantSlug}/epk/page`)
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
  if (html) {
    return <iframe title="Booker EPK" className="booker-epk-iframe" srcDoc={html} />;
  }
  return null;
}

export default BookerEpkPage;
