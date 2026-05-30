import React from 'react';

function EpkLayout({ site, children }) {
  return (
    <div className="epk-layout">
      <header className="epk-header">
        <h1 className="epk-artist-name">{site?.display_name || 'Artist'}</h1>
        {site?.tagline ? <p className="epk-tagline">{site.tagline}</p> : null}
      </header>
      <main className="epk-main">{children}</main>
      <footer className="epk-footer">
        {site?.booking_email ? (
          <a href={`mailto:${site.booking_email}`} className="epk-booking-link">
            Book {site.display_name}
          </a>
        ) : null}
      </footer>
    </div>
  );
}

export default EpkLayout;
