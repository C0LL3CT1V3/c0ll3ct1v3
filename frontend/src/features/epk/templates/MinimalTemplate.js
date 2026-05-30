import React from 'react';

function MinimalTemplate({ site, layout, trackById, photoById, theme }) {
  const hero = layout.find((b) => b.type === 'hero') || {};
  const photos = (layout.find((b) => b.type === 'photo_grid')?.asset_ids || [])
    .map((id) => photoById[id])
    .filter(Boolean)
    .slice(0, 3);

  return (
    <div className="epk-tpl-minimal" style={{ background: theme.background }}>
      <h1>{hero.headline || site.display_name}</h1>
      <p className="epk-tpl-minimal-sub">{hero.subhead || site.tagline}</p>
      {photos.length > 0 ? (
        <div className="epk-tpl-minimal-strip">
          {photos.map((p) => (
            <img key={p.asset_id} src={p.url} alt="" loading="lazy" />
          ))}
        </div>
      ) : null}
      {site.bio ? <p className="epk-bio">{site.bio}</p> : null}
    </div>
  );
}

export default MinimalTemplate;
