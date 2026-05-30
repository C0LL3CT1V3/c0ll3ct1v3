import React from 'react';
import EpkMediaEmbed from '../EpkMediaEmbed';

function GalleryTemplate({ site, layout, trackById, photoById, theme }) {
  const hero = layout.find((b) => b.type === 'hero') || {};
  const grid = layout.find((b) => b.type === 'photo_grid') || { asset_ids: [] };
  const photos = (grid.asset_ids || []).map((id) => photoById[id]).filter(Boolean);
  const music = layout.find((b) => b.type === 'music') || { asset_ids: [] };
  const tracks = (music.asset_ids || []).map((id) => trackById[id]).filter(Boolean);

  return (
    <div className="epk-tpl-gallery" style={{ background: theme.background }}>
      <h1 className="epk-tpl-gallery-title">{hero.headline || site.display_name}</h1>
      <div className="epk-tpl-gallery-mosaic">
        {photos.map((p) => (
          <img key={p.asset_id} src={p.url} alt={p.title || ''} loading="lazy" />
        ))}
      </div>
      {tracks.length > 0 ? (
        <section className="epk-section epk-tpl-gallery-audio">
          {tracks.map((t) => (
            <div key={t.asset_id}>
              <span>{t.title}</span>
              {t.stream_url ? (
                <EpkMediaEmbed url={t.stream_url} mimeType={t.mime_type} title={t.title} />
              ) : null}
            </div>
          ))}
        </section>
      ) : null}
    </div>
  );
}

export default GalleryTemplate;
