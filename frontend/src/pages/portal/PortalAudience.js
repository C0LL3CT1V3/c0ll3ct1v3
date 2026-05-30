import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import AudiencePanel from '../../features/audience/AudiencePanel';

function PortalAudience() {
  const [selectedId, setSelectedId] = useState(
    () => sessionStorage.getItem('portal_selected_asset_id') || null,
  );

  return (
    <div className="portal-audience-page">
      <p className="portal-panel-hint">
        Tip: pick a track on the{' '}
        <Link to="/portal">Studio</Link> tab — your selection is remembered here.
      </p>
      <label htmlFor="audience-asset-id">Asset ID (from library)</label>
      <input
        id="audience-asset-id"
        type="text"
        value={selectedId || ''}
        onChange={(e) => {
          setSelectedId(e.target.value || null);
          if (e.target.value) {
            sessionStorage.setItem('portal_selected_asset_id', e.target.value);
          } else {
            sessionStorage.removeItem('portal_selected_asset_id');
          }
        }}
        placeholder="Paste UUID from library row"
      />
      <AudiencePanel selectedAssetId={selectedId} />
    </div>
  );
}

export default PortalAudience;
