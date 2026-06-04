import React from 'react';
import { useArtistProfile } from '../../hooks/useArtistProfile';
import PortalLayout from '../../layouts/PortalLayout';
import PortalHome from './PortalHome';

function PortalShell() {
  const { profile, loading, error: profileError } = useArtistProfile();

  if (loading) {
    return (
      <PortalLayout profile={profile}>
        <p className="portal-loading">Loading your studio…</p>
      </PortalLayout>
    );
  }

  return (
    <PortalLayout profile={profile}>
      {profileError ? <div className="error-message">{profileError}</div> : null}
      <PortalHome profile={profile} />
    </PortalLayout>
  );
}

export default PortalShell;
