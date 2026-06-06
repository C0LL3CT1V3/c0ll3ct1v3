import React from 'react';
import EpkRenderer from '../epk/EpkRenderer';
import '../../styles/epk.css';

function EpkPreviewFrame({ draft }) {
  if (!draft) {
    return <div className="epk-preview-empty">Loading EPK preview…</div>;
  }

  if (draft.format === 'html_v1' && draft.sim_render_url) {
    return (
      <div className="epk-preview-frame-inner epk-preview-frame-inner--html">
        <iframe
          title="EPK preview"
          className="epk-preview-iframe"
          src={draft.sim_render_url}
          sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
        />
      </div>
    );
  }

  if (draft.design?.layout?.length) {
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

  return (
    <div className="epk-preview-frame-inner">
      <EpkRenderer site={draft.site} design={draft.design} tracks={draft.tracks} photos={draft.photos} />
    </div>
  );
}

export default EpkPreviewFrame;
