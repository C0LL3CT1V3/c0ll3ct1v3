import React from 'react';
import EpkMediaEmbed from '../EpkMediaEmbed';
import { blockById, collectAssetIds } from '../layoutUtils';

function EditorialTemplate({ site, layout, trackById, photoById, theme }) {
  const hero = blockById(layout, 'hero', 'hero');
  const bioBlock = blockById(layout, 'bio-main', 'bio');
  const contact = blockById(layout, 'contact-1', 'contact');
  const photoIds = collectAssetIds(layout, 'photo_grid');
  const musicIds = collectAssetIds(layout, 'music');
  const photos = photoIds.map((id) => photoById[id]).filter(Boolean);
  const tracks = musicIds.map((id) => trackById[id]).filter(Boolean);

  return (
    <div className="epk-tpl-editorial" style={{ background: theme.background }}>
      <header className="epk-tpl-hero" data-epk-id="hero">
        <h1>{hero.headline || site.display_name}</h1>
        {(hero.subhead || site.tagline) && (
          <p className="epk-tpl-tagline">{hero.subhead || site.tagline}</p>
        )}
      </header>
      {tracks.length > 0 ? (
        <section className="epk-section" data-epk-id="music-1">
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
      {(bioBlock.body || site.bio) ? (
        <section className="epk-section" data-epk-id="bio-main">
          <h2>About</h2>
          <p className="epk-bio">{bioBlock.body || site.bio}</p>
        </section>
      ) : null}
      {photos.length > 0 ? (
        <section className="epk-section" data-epk-id="photos-1">
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
      {(contact.email || site.booking_email) ? (
        <footer className="epk-tpl-contact" data-epk-id="contact-1">
          <a href={`mailto:${contact.email || site.booking_email}`}>Book {site.display_name}</a>
        </footer>
      ) : null}
    </div>
  );
}

export default EditorialTemplate;
