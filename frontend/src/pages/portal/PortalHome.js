import React, { useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';
import CollapsibleManagerChat from '../../features/manager/CollapsibleManagerChat';
import EpkBuilderStudio from '../../features/epk-builder/EpkBuilderStudio';
import MediaFileSidebar from '../../features/media/MediaFileSidebar';
import MediaVisionBoard from '../../features/media/MediaVisionBoard';
import { useWorkbench } from '../../features/media/useWorkbench';

function PortalHome({ profile }) {
  const { apiClient, authReady } = useApiClient();
  const [mediaError, setMediaError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedId, setSelectedId] = useState(
    () => sessionStorage.getItem('portal_selected_asset_id') || null,
  );

  const tenantSlug = profile?.tenant_slug;

  const workbench = useWorkbench(apiClient, authReady, refreshKey);

  const handleSelect = (id) => {
    setSelectedId(id);
    if (id) sessionStorage.setItem('portal_selected_asset_id', id);
    else sessionStorage.removeItem('portal_selected_asset_id');
  };

  const handleMediaError = (msg) => {
    setMediaError(msg);
    if (msg) workbench.setError('');
  };

  return (
    <div className="portal-studio">
      <CollapsibleManagerChat />
      <div className="portal-studio-panels">
        <MediaFileSidebar
          apiClient={apiClient}
          tenantSlug={tenantSlug}
          onUploaded={() => setRefreshKey((k) => k + 1)}
          onError={handleMediaError}
          mediaError={mediaError}
          assets={workbench.assets}
          thumbs={workbench.thumbs}
          visionTitleById={workbench.visionTitleById}
          selectedId={selectedId}
          onSelect={handleSelect}
          onDeleteAsset={workbench.deleteAsset}
        />
        <div className="portal-workbench-main">
          <MediaVisionBoard
            visions={workbench.visions}
            assets={workbench.assets}
            assetsByVision={workbench.assetsByVision}
            thumbs={workbench.thumbs}
            selectedId={selectedId}
            onSelect={handleSelect}
            error={workbench.error}
            onError={(msg) => workbench.setError(msg)}
            assignAsset={workbench.assignAsset}
            deleteAsset={workbench.deleteAsset}
            createVision={workbench.createVision}
            renameVision={workbench.renameVision}
            deleteVision={workbench.deleteVision}
          />
          <EpkBuilderStudio onError={handleMediaError} />
        </div>
      </div>
    </div>
  );
}

export default PortalHome;
