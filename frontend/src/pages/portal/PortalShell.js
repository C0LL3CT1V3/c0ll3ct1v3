import React from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import { useArtistProfile } from '../../hooks/useArtistProfile';
import PortalLayout from '../../layouts/PortalLayout';
import PortalHome from './PortalHome';
import DesignStudio from '../../features/epk-design/DesignStudio';
import PortalAudience from './PortalAudience';

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
      <nav className="portal-tabs">
        <NavLink to="/portal" end className={({ isActive }) => (isActive ? 'portal-tab portal-tab--active' : 'portal-tab')}>
          Studio
        </NavLink>
        <NavLink to="/portal/design" className={({ isActive }) => (isActive ? 'portal-tab portal-tab--active' : 'portal-tab')}>
          Design EPK
        </NavLink>
        <NavLink to="/portal/audience" className={({ isActive }) => (isActive ? 'portal-tab portal-tab--active' : 'portal-tab')}>
          Audience
        </NavLink>
      </nav>
      <Routes>
        <Route index element={<PortalHome profile={profile} />} />
        <Route path="design" element={<DesignStudio />} />
        <Route path="audience" element={<PortalAudience />} />
      </Routes>
    </PortalLayout>
  );
}

export default PortalShell;
