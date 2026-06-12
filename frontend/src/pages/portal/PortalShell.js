import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useArtistProfile } from '../../hooks/useArtistProfile';
import PortalLayout from '../../layouts/PortalLayout';
import { PortalWorkbenchProvider } from '../../features/media/PortalWorkbenchProvider';
import PortalVaultPage from './PortalVaultPage';
import PortalEpkPage from './PortalEpkPage';

function PortalShell() {
  const { profile, loading, error: profileError, refresh, updateProfile } = useArtistProfile();

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
      <PortalWorkbenchProvider>
        <Routes>
          <Route index element={<Navigate to="vault" replace />} />
          <Route path="vault" element={<PortalVaultPage profile={profile} />} />
          <Route
            path="epk"
            element={
              <PortalEpkPage
                profile={profile}
                updateProfile={updateProfile}
                onProfileRefresh={refresh}
              />
            }
          />
          <Route path="profile" element={<Navigate to="/portal/vault" replace />} />
          <Route path="data" element={<Navigate to="/portal/vault" replace />} />
          <Route path="*" element={<Navigate to="vault" replace />} />
        </Routes>
      </PortalWorkbenchProvider>
    </PortalLayout>
  );
}

export default PortalShell;
