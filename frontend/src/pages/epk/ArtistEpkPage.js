import React, { useEffect, useState } from 'react';
import axios from 'axios';
import EpkLayout from '../../layouts/EpkLayout';
import EpkRenderer from '../../features/epk/EpkRenderer';
import { useTenantSlug } from '../../hooks/useTenantSlug';

const API_BASE = (process.env.REACT_APP_API_URL || 'http://localhost:8080').replace(/\/$/, '');

function ArtistEpkPage() {
  const tenantSlug = useTenantSlug();
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantSlug) {
      setError('No artist subdomain found.');
      setLoading(false);
      return;
    }

    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API_BASE}/epk/site`, { params: { tenant_slug: tenantSlug } });
        if (!cancelled) {
          setPayload(res.data);
          setError('');
        }
      } catch (err) {
        if (!cancelled) {
          const detail = err?.response?.data?.detail;
          setError(detail || 'Could not load EPK.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [tenantSlug]);

  if (loading) {
    return <div className="epk-loading">Loading…</div>;
  }

  if (error) {
    return <div className="epk-error">{error}</div>;
  }

  const site = {
    display_name: payload.display_name,
    tagline: payload.tagline,
    bio: payload.bio,
    booking_email: payload.booking_email,
    social: payload.social,
    sections: payload.sections,
  };

  return (
    <EpkLayout site={site}>
      <EpkRenderer
        site={site}
        design={payload.design}
        tracks={payload.tracks || []}
        photos={payload.photos || []}
      />
      {payload.social && Object.keys(payload.social).length > 0 ? (
        <section className="epk-section epk-social">
          {Object.entries(payload.social).map(([key, url]) =>
            url ? (
              <a key={key} href={url} target="_blank" rel="noreferrer">
                {key}
              </a>
            ) : null,
          )}
        </section>
      ) : null}
    </EpkLayout>
  );
}

export default ArtistEpkPage;
