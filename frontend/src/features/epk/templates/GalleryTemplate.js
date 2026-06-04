import React from 'react';
import EpkMediaEmbed from '../EpkMediaEmbed';
import { blockById, collectAssetIds } from '../layoutUtils';

function GalleryTemplate({ site, layout, trackById, photoById, theme }) {
  const hero = blockById(layout, 'hero', 'hero');
  const photoIds = collectAssetIds(layout, 'photo_grid');
  const musicIds = collectAssetIds(layout, 'music');
  const photos = photoIds.map((id) => photoById[id]).filter(Boolean);
  const tracks = musicIds.map((id) => trackById[id]).filter(Boolean);

  return (
    <div className="epk-tpl-gallery" style={{ background: theme.background }}>
      <h1 className="epk-tpl-gallery-title" data-epk-id="hero">
        {hero.headline || site.display_name}
      </h1>
      <div className="epk-tpl-gallery-mosaic" data-epk-id="photos-1">
        {photos.map((p) => (
          <img key={p.asset_id} src={p.url} alt={p.title || ''} loading="lazy" />
        ))}
      </div>
      {tracks.length > 0 ? (
        <section className="epk-section epk-tpl-gallery-audio" data-epk-id="music-1">
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
