import React, { useEffect, useState } from 'react';
import EpkRenderer from '../epk/EpkRenderer';
import { fetchPublicProfile, publicPageUrl } from '../../api/publicApi';
import { useTenantSlug } from '../../hooks/useTenantSlug';
import '../../styles/epk.css';

function ArtistProfilePage() {
  const tenantSlug = useTenantSlug();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantSlug) return;
    setLoading(true);
    fetchPublicProfile(tenantSlug)
      .then((data) => {
        setProfile(data);
        setError('');
      })
      .catch((err) => {
        setError(err?.response?.data?.detail || 'Profile not found.');
        setProfile(null);
      })
      .finally(() => setLoading(false));
  }, [tenantSlug]);

  if (!tenantSlug) {
    return (
      <div className="profile-page profile-page--empty">
        <p>Open an artist subdomain to view their page.</p>
      </div>
    );
  }

  if (loading) {
    return <div className="profile-page profile-page--loading">Loading…</div>;
  }

  if (error || !profile) {
    return (
      <div className="profile-page profile-page--empty">
        <h1>@{tenantSlug}</h1>
        <p>{error || 'This page does not exist yet.'}</p>
      </div>
    );
  }

  if (!profile.profile_published) {
    return (
      <div className="profile-page profile-page--draft">
        <h1 className="profile-page-name">{profile.display_name}</h1>
        {profile.tagline ? <p className="profile-page-tagline">{profile.tagline}</p> : null}
        <p className="profile-page-notice">
          This musician is still building their page. Check back soon.
        </p>
      </div>
    );
  }

  if (profile.format === 'html_v1') {
    const pageSrc = publicPageUrl(tenantSlug);
    return (
      <div className="profile-page profile-page--html">
        <iframe
          title={`${profile.display_name} profile`}
          className="profile-page-iframe"
          src={pageSrc}
          sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
        />
      </div>
    );
  }

  const site = {
    ...profile.site,
    display_name: profile.display_name,
    tagline: profile.tagline,
    bio: profile.bio,
    booking_email: profile.booking_email,
    social: profile.social,
    sections: profile.sections,
  };

  return (
    <div className="profile-page profile-page--layout epk-layout">
      <header className="profile-page-header">
        <h1 className="epk-artist-name">{profile.display_name}</h1>
        {profile.tagline ? <p className="epk-tagline">{profile.tagline}</p> : null}
        {profile.social && Object.keys(profile.social).length ? (
          <nav className="profile-page-social epk-social">
            {Object.entries(profile.social).map(([key, url]) => (
              <a key={key} href={url.startsWith('http') ? url : `https://${url}`} target="_blank" rel="noreferrer">
                {key}
              </a>
            ))}
          </nav>
        ) : null}
      </header>
      <EpkRenderer
        site={site}
        design={profile.design}
        tracks={profile.tracks}
        photos={profile.photos}
      />
    </div>
  );
}

export default ArtistProfilePage;
