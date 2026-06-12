import React from 'react';
import EpkBookerStudio from '../../features/epk-booker/EpkBookerStudio';

function PortalEpkPage({ profile, updateProfile, onProfileRefresh }) {
  return (
    <div className="portal-studio portal-studio--epk">
      <header className="portal-section-header">
        <h1 className="portal-section-title">EPK</h1>
        <p className="portal-section-lead">
          Booker-ready press kit — fill the template from your Vault, preview, publish, and export PDF.
        </p>
      </header>
      <EpkBookerStudio
        profile={profile}
        updateProfile={updateProfile}
        onProfileRefresh={onProfileRefresh}
      />
    </div>
  );
}

export default PortalEpkPage;
