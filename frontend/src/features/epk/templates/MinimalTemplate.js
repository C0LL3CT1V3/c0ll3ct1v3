import React from 'react';
import { blockById, collectAssetIds } from '../layoutUtils';

function MinimalTemplate({ site, layout, trackById, photoById, theme }) {
  const hero = blockById(layout, 'hero', 'hero');
  const photos = collectAssetIds(layout, 'photo_grid')
    .map((id) => photoById[id])
    .filter(Boolean)
    .slice(0, 3);

  return (
    <div className="epk-tpl-minimal" style={{ background: theme.background }}>
      <h1 data-epk-id="hero">{hero.headline || site.display_name}</h1>
      <p className="epk-tpl-minimal-sub">{hero.subhead || site.tagline}</p>
      {photos.length > 0 ? (
        <div className="epk-tpl-minimal-strip" data-epk-id="photos-1">
          {photos.map((p) => (
            <img key={p.asset_id} src={p.url} alt="" loading="lazy" />
          ))}
        </div>
      ) : null}
      {site.bio ? (
        <p className="epk-bio" data-epk-id="bio-main">
          {site.bio}
        </p>
      ) : null}
    </div>
  );
}

export default MinimalTemplate;
