import React from 'react';
import CollapsibleSection from '../../components/CollapsibleSection';
import EpkBuilderStudio from '../../features/epk-builder/EpkBuilderStudio';
import ProfileSeedForm from '../../features/epk-builder/ProfileSeedForm';
import { useEpkBuilder } from '../../features/epk-builder/useEpkBuilder';
import MediaVisionBoard from '../../features/media/MediaVisionBoard';
import { usePortalWorkbench } from '../../features/media/PortalWorkbenchProvider';

function PortalProfilePage() {
  const {
    selectedId,
    setSelectedId,
    setMediaError,
    workbench,
  } = usePortalWorkbench();
  const builder = useEpkBuilder();
  const busy = builder.phase === 'generating' || builder.phase === 'refining';

  const handleError = (msg) => {
    if (msg) setMediaError(msg);
    workbench.setError(msg);
  };

  return (
    <div className="portal-studio portal-studio--profile">
      <header className="portal-section-header">
        <h1 className="portal-section-title">Profile Studio</h1>
        <p className="portal-section-lead">
          Vision board + design spec create a new profile seed — annotate and iterate with the AI until it feels right.
        </p>
      </header>

      <CollapsibleSection
        title="Profile seed setup"
        className="profile-seed-setup-collapsible"
        defaultOpen
      >
        <p className="profile-seed-setup-lead">
          Wireframe, references, and media from your vision board combine with your design spec to generate a seed page.
          Collapse this when you are ready to annotate and iterate.
        </p>
        <MediaVisionBoard
          visions={workbench.visions}
          assets={workbench.assets}
          assetsByVision={workbench.assetsByVision}
          thumbs={workbench.thumbs}
          selectedId={selectedId}
          onSelect={setSelectedId}
          error={workbench.error}
          onError={(msg) => workbench.setError(msg)}
          assignAsset={workbench.assignAsset}
          assignAssetToVisionRole={workbench.assignAssetToVisionRole}
          createReferenceFromUrl={workbench.createReferenceFromUrl}
          deleteAsset={workbench.deleteAsset}
          createVision={workbench.createVision}
          renameVision={workbench.renameVision}
          deleteVision={workbench.deleteVision}
          embedded
        />
        <ProfileSeedForm
          builder={builder}
          visions={workbench.visions}
          onError={handleError}
          busy={busy}
        />
      </CollapsibleSection>

      <EpkBuilderStudio builder={builder} onError={setMediaError} />
    </div>
  );
}

export default PortalProfilePage;
