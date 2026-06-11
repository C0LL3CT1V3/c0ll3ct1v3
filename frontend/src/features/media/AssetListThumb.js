import React from 'react';

function AssetListThumb({ asset, thumbUrl }) {
  if (thumbUrl) {
    return <img src={thumbUrl} alt="" className="portal-file-thumb" />;
  }

  const type = asset?.asset_type;
  if (type === 'audio') {
    return (
      <span className="portal-file-thumb portal-file-thumb--placeholder portal-file-thumb--audio" aria-hidden>
        ♫
      </span>
    );
  }
  if (type === 'video') {
    return (
      <span className="portal-file-thumb portal-file-thumb--placeholder portal-file-thumb--video" aria-hidden>
        ▶
      </span>
    );
  }
  if (type === 'image') {
    return (
      <span className="portal-file-thumb portal-file-thumb--placeholder" aria-hidden>
        ◻
      </span>
    );
  }

  return (
    <span className="portal-file-thumb portal-file-thumb--placeholder" aria-hidden>
      {type?.[0]?.toUpperCase() || '?'}
    </span>
  );
}

export default AssetListThumb;
