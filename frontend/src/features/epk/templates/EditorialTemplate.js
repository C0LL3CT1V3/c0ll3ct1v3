import React from 'react';
import EpkMediaEmbed from '../EpkMediaEmbed';

function blockPhotos(layout, photoById) {
  const ids = [];
  layout.forEach((b) => {
    if (b.type === 'photo_grid' && b.asset_ids) ids.push(...b.asset_ids);
  });
  return ids.map((id) => photoById[id]).filter(Boolean);
}

function blockTracks(layout, trackById) {
  const ids = [];
  layout.forEach((b) => {
    if (b.type === 'music' && b.asset_ids) ids.push(...b.asset_ids);
  });
  return ids.map((id) => trackById[id]).filter(Boolean);
}

function EditorialTemplate({ site, layout, trackById, photoById, theme }) {
  const hero = layout.find((b) => b.type === 'hero') || {};
  const photos = blockPhotos(layout, photoById);
  const tracks = blockTracks(layout, trackById);
  const bioBlock = layout.find((b) => b.type === 'bio');
  const contact = layout.find((b) => b.type === 'contact');

  return (
    <div className="epk-tpl-editorial" style={{ background: theme.background }}>
      <header className="epk-tpl-hero">
        <h1>{hero.headline || site.display_name}</h1>
        {(hero.subhead || site.tagline) && <p className="epk-tpl-tagline">{hero.subhead || site.tagline}</p>}
      </header>
      {tracks.length > 0 ? (
        <section className="epk-section">
          <h2>Music</h2>
          <ul className="epk-tracks">
            {tracks.map((t) => (
              <li key={t.asset_id} className="epk-track">
                <span className="epk-track-title">{t.title}</span>
                {t.stream_url ? (
                  <EpkMediaEmbed url={t.stream_url} mimeType={t.mime_type} title={t.title} />
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {(bioBlock?.body || site.bio) ? (
        <section className="epk-section">
          <h2>About</h2>
          <p className="epk-bio">{bioBlock?.body || site.bio}</p>
        </section>
      ) : null}
      {photos.length > 0 ? (
        <section className="epk-section">
          <h2>Photos</h2>
          <div className="epk-photo-grid">
            {photos.map((p) => (
              <figure key={p.asset_id} className="epk-photo">
                <img src={p.url} alt={p.title || ''} loading="lazy" />
              </figure>
            ))}
          </div>
        </section>
      ) : null}
      {(contact?.email || site.booking_email) ? (
        <footer className="epk-tpl-contact">
          <a href={`mailto:${contact?.email || site.booking_email}`}>Book {site.display_name}</a>
        </footer>
      ) : null}
    </div>
  );
}

export default EditorialTemplate;
