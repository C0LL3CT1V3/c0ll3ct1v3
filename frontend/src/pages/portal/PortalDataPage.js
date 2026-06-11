import React from 'react';
import DataDashboard from '../../features/data/DataDashboard';

function PortalDataPage({ profile }) {
  return (
    <div className="portal-studio portal-studio--data">
      <header className="portal-section-header">
        <h1 className="portal-section-title">Data</h1>
        <p className="portal-section-lead">
          Audience insights — genre positioning, comparable artists, and pitch lines.
        </p>
      </header>
      <DataDashboard profile={profile} />
    </div>
  );
}

export default PortalDataPage;
