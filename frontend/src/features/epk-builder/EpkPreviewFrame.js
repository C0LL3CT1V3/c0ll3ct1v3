import React from 'react';
import EpkRenderer from '../epk/EpkRenderer';
import '../../styles/epk.css';

function EpkPreviewFrame({ draft }) {
  if (!draft) {
    return <div className="epk-preview-empty">Loading EPK preview…</div>;
  }

  return (
    <div className="epk-preview-frame-inner">
      <EpkRenderer
        site={draft.site}
        design={draft.design}
        tracks={draft.tracks}
        photos={draft.photos}
      />
    </div>
  );
}

export default EpkPreviewFrame;
