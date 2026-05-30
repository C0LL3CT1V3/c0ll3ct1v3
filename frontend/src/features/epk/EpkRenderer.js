import React from 'react';
import EditorialTemplate from './templates/EditorialTemplate';
import GalleryTemplate from './templates/GalleryTemplate';
import MinimalTemplate from './templates/MinimalTemplate';
import EpkMediaEmbed from './EpkMediaEmbed';

function LegacyEpk({ site, tracks, photos }) {
  const sections = site?.sections || {};
  return (
    <>
      {sections.music !== false && tracks?.length > 0 ? (
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
      {site?.bio ? (
        <section className="epk-section">
          <h2>About</h2>
          <p className="epk-bio">{site.bio}</p>
        </section>
      ) : null}
      {sections.photos !== false && photos?.length > 0 ? (
        <section className="epk-section">
          <h2>Photos</h2>
          <div className="epk-photo-grid">
            {photos.map((p) => (
              <figure key={p.asset_id} className="epk-photo">
                <img src={p.url} alt={p.title || 'Photo'} loading="lazy" />
                {p.title ? <figcaption>{p.title}</figcaption> : null}
              </figure>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}

function resolveMediaMaps(tracks, photos) {
  const trackById = Object.fromEntries((tracks || []).map((t) => [t.asset_id, t]));
  const photoById = Object.fromEntries((photos || []).map((p) => [p.asset_id, p]));
  return { trackById, photoById };
}

function EpkRenderer({ site, design, tracks, photos }) {
  if (!design?.layout?.length) {
    return <LegacyEpk site={site} tracks={tracks} photos={photos} />;
  }

  const { trackById, photoById } = resolveMediaMaps(tracks, photos);
  const theme = design.theme || {};
  const style = {
    '--epk-accent': theme.accent || '#c4a574',
    '--epk-bg': theme.background || '#faf9f6',
  };

  const props = { site, design, layout: design.layout, trackById, photoById, theme };

  if (design.template_id === 'gallery') {
    return (
      <div className="epk-themed" style={style}>
        <GalleryTemplate {...props} />
      </div>
    );
  }
  if (design.template_id === 'minimal') {
    return (
      <div className="epk-themed" style={style}>
        <MinimalTemplate {...props} />
      </div>
    );
  }
  return (
    <div className="epk-themed" style={style}>
      <EditorialTemplate {...props} />
    </div>
  );
}

export default EpkRenderer;
