import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Public artist subdomain placeholder — EPK paused while media workbench ships.
 */
function ArtistEpkPage() {
  return (
    <div className="epk-layout" style={{ padding: '3rem 1.5rem', textAlign: 'center' }}>
      <h1 className="epk-artist-name">Artist page</h1>
      <p className="epk-tagline">Public EPK is paused. Media workbench and gallery are in the portal.</p>
      <p>
        <Link to="/portal">Go to portal</Link>
      </p>
    </div>
  );
}

export default ArtistEpkPage;
