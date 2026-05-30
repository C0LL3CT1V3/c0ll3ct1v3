import React from 'react';

/**
 * Render the right HTML element from a media URL and MIME type (or stream vs image URL shape).
 */
function EpkMediaEmbed({ url, mimeType, title, className }) {
  if (!url) return null;

  const mime = (mimeType || '').toLowerCase();
  const label = title || 'Media';

  if (mime.startsWith('image/') || (!mime && looksLikeImageUrl(url))) {
    return <img className={className} src={url} alt={label} loading="lazy" />;
  }
  if (mime.startsWith('video/')) {
    return <video className={className} controls preload="metadata" src={url} />;
  }
  if (mime.startsWith('audio/') || !mime) {
    return <audio className={className} controls preload="none" src={url} />;
  }

  return (
    <a className={className} href={url} target="_blank" rel="noopener noreferrer">
      {label}
    </a>
  );
}

function looksLikeImageUrl(url) {
  return /\.(jpe?g|png|gif|webp|avif)(\?|$)/i.test(url);
}

export default EpkMediaEmbed;
