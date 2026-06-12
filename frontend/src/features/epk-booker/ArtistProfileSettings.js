import React, { useEffect, useState } from 'react';
import { profilePublicUrl } from '../../hooks/useTenantSlug';

function ArtistProfileSettings({ profile, updateProfile, onSaved, onError }) {
  const [displayName, setDisplayName] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setDisplayName(profile?.display_name || '');
    setTenantSlug(profile?.tenant_slug || '');
  }, [profile?.display_name, profile?.tenant_slug]);

  const previewOrigin = tenantSlug ? profilePublicUrl(tenantSlug) : null;
  const epkUrl = previewOrigin ? `${previewOrigin}/epk` : null;

  const handleSave = async () => {
    if (!updateProfile) return;
    setBusy(true);
    onError?.('');
    try {
      await updateProfile({
        display_name: displayName.trim(),
        tenant_slug: tenantSlug.trim().toLowerCase(),
      });
      onSaved?.();
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not save artist page settings.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="epk-artist-settings">
      <h2 className="epk-artist-settings-title">Artist page</h2>
      <p className="epk-artist-settings-lead">
        Your display name appears on the EPK. Your page URL uses the subdomain slug below.
      </p>
      <div className="epk-artist-settings-grid">
        <label className="epk-booker-field">
          <span>Artist name</span>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Phillip James"
          />
        </label>
        <label className="epk-booker-field">
          <span>Subdomain (page URL)</span>
          <input
            type="text"
            value={tenantSlug}
            onChange={(e) => setTenantSlug(e.target.value)}
            placeholder="phillipjames"
            spellCheck={false}
          />
          <span className="epk-artist-settings-hint">
            Lowercase letters, numbers, and hyphens only. Changing this changes your public link.
          </span>
        </label>
      </div>
      {epkUrl ? (
        <p className="epk-artist-settings-url">
          Public EPK:{' '}
          <a href={epkUrl} target="_blank" rel="noreferrer">
            {epkUrl}
          </a>
        </p>
      ) : null}
      <button
        type="button"
        className="portal-btn portal-btn--ghost"
        disabled={busy || !displayName.trim() || !tenantSlug.trim()}
        onClick={handleSave}
      >
        {busy ? 'Saving…' : 'Save artist page'}
      </button>
    </section>
  );
}

export default ArtistProfileSettings;
