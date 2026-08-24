import React from 'react';
import HomebaseStudio from '../../features/homebase/HomebaseStudio';

function PortalHomebasePage({ profile, onProfileRefresh }) {
  return (
    <div className="portal-studio portal-studio--homebase">
      <header className="portal-section-header">
        <h1 className="portal-section-title">Homebase</h1>
        <p className="portal-section-lead">
          Public events calendar and Square checkout — publish shows and a Pay button for fans.
        </p>
      </header>
      <HomebaseStudio profile={profile} onProfileRefresh={onProfileRefresh} />
    </div>
  );
}

export default PortalHomebasePage;
