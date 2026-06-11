import React from 'react';
import MediaFileSidebar from '../../features/media/MediaFileSidebar';
import VaultFolderBoard from '../../features/vault/VaultFolderBoard';
import { usePortalWorkbench } from '../../features/media/PortalWorkbenchProvider';

function PortalVaultPage({ profile }) {
  const {
    apiClient,
    bumpRefresh,
    selectedId,
    setSelectedId,
    mediaError,
    setMediaError,
    workbench,
  } = usePortalWorkbench();

  const tenantSlug = profile?.tenant_slug;

  const handleMediaError = (msg) => {
    setMediaError(msg);
    if (msg) workbench.setError('');
  };

  return (
    <div className="portal-studio">
      <header className="portal-section-header">
        <h1 className="portal-section-title">Vault</h1>
        <p className="portal-section-lead">
          All your IP in one place — upload files and organize them into folders.
        </p>
      </header>
      <div className="portal-studio-panels">
        <MediaFileSidebar
          apiClient={apiClient}
          tenantSlug={tenantSlug}
          onUploaded={bumpRefresh}
          onError={handleMediaError}
          mediaError={mediaError}
          assets={workbench.assets}
          thumbs={workbench.thumbs}
          visionTitleById={workbench.visionTitleById}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onDeleteAsset={workbench.deleteAsset}
          hint="Drag files into a folder on the right."
        />
        <div className="portal-workbench-main">
          <VaultFolderBoard
            visions={workbench.visions}
            assets={workbench.assets}
            assetsByVision={workbench.assetsByVision}
            thumbs={workbench.thumbs}
            selectedId={selectedId}
            onSelect={setSelectedId}
            error={workbench.error}
            onError={(msg) => workbench.setError(msg)}
            assignAssetToFolder={workbench.assignAssetToFolder}
            deleteAsset={workbench.deleteAsset}
            createVision={workbench.createVision}
            renameVision={workbench.renameVision}
            deleteVision={workbench.deleteVision}
          />
        </div>
      </div>
    </div>
  );
}

export default PortalVaultPage;
