import React, { useState } from 'react';
import { getAssetDragId } from './mediaDrag';

function visionRole(asset) {
  return asset?.tags?.vision_role || 'media';
}

function partitionVisionAssets(items) {
  const wireframe = items.find((a) => visionRole(a) === 'wireframe') || null;
  const references = items.filter((a) => visionRole(a) === 'reference');
  const media = items.filter((a) => visionRole(a) === 'media');
  return { wireframe, references, media };
}

function MediaVisionBoard({
  visions,
  assets,
  assetsByVision,
  thumbs,
  selectedId,
  onSelect,
  error,
  onError,
  assignAssetToVisionRole,
  deleteAsset,
  createVision,
  renameVision,
  deleteVision,
}) {
  const [dragOverZone, setDragOverZone] = useState(null);

  const onDragOverZone = (e, zoneId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverZone(zoneId);
  };

  const onDragLeaveZone = () => {
    setDragOverZone(null);
  };

  const onDropZone = async (e, visionId, role) => {
    e.preventDefault();
    setDragOverZone(null);
    const assetId = getAssetDragId(e.dataTransfer);
    if (!assetId) return;
    const asset = assets.find((a) => a.id === assetId);
    if (!asset) return;
    if (asset.vision_id === visionId && visionRole(asset) === role) return;
    try {
      await assignAssetToVisionRole(assetId, visionId, role);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not move item.');
    }
  };

  const handleDeleteAsset = async (assetId, e) => {
    e.stopPropagation();
    if (!window.confirm('Remove this file from the workbench?')) return;
    try {
      await deleteAsset(assetId);
      if (selectedId === assetId) onSelect?.(null);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Delete failed.');
    }
  };

  const handleDeleteVision = async (visionId, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this vision? Files stay in the list on the left until you add them to another vision.')) return;
    try {
      await deleteVision(visionId);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not delete vision.');
    }
  };

  const handleCreateVision = async () => {
    try {
      await createVision();
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not create vision.');
    }
  };

  const renderAssetCard = (a) => (
    <div
      key={a.id}
      className={`workbench-asset${selectedId === a.id ? ' workbench-asset--selected' : ''}`}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('application/x-c0-media-asset', a.id);
        e.dataTransfer.effectAllowed = 'move';
      }}
      onClick={() => onSelect?.(a.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onSelect?.(a.id);
      }}
    >
      {thumbs[a.id] ? (
        <img src={thumbs[a.id]} alt="" className="workbench-asset-thumb" />
      ) : (
        <span className="workbench-asset-thumb workbench-asset-thumb--placeholder" aria-hidden>
          ·
        </span>
      )}
      <span className="workbench-asset-title">{a.title || 'Untitled'}</span>
      <button
        type="button"
        className="workbench-asset-delete"
        title="Delete"
        onClick={(e) => handleDeleteAsset(a.id, e)}
      >
        ×
      </button>
    </div>
  );

  const renderDropSlot = (visionId, role, label, slotAsset, slotKey) => {
    const zoneId = `${visionId}-${role}-${slotKey}`;
    const active = dragOverZone === zoneId;
    return (
      <div
        key={zoneId}
        className={`workbench-vision-slot workbench-vision-slot--${role}${active ? ' workbench-vision-slot--drag-over' : ''}${slotAsset ? ' workbench-vision-slot--filled' : ''}`}
        onDragOver={(e) => onDragOverZone(e, zoneId)}
        onDragLeave={onDragLeaveZone}
        onDrop={(e) => onDropZone(e, visionId, role)}
      >
        <span className="workbench-vision-slot-label">{label}</span>
        {slotAsset ? renderAssetCard(slotAsset) : <p className="workbench-vision-slot-empty">Drop here</p>}
      </div>
    );
  };

  const renderVisionCluster = (vision) => {
    const items = assetsByVision.grouped[vision.id] || [];
    const { wireframe, references, media } = partitionVisionAssets(items);
    const refSlots = [0, 1, 2].map((i) => references[i] || null);

    return (
      <section key={vision.id} className="workbench-vision">
        <header className="workbench-vision-header">
          <input
            type="text"
            className="workbench-vision-title"
            defaultValue={vision.title}
            onBlur={async (e) => {
              try {
                await renameVision(vision.id, e.target.value);
              } catch (err) {
                onError?.(err?.response?.data?.detail || 'Could not rename vision.');
              }
            }}
            onClick={(e) => e.stopPropagation()}
          />
          <span className="workbench-vision-count">{items.length}</span>
          <button
            type="button"
            className="workbench-vision-delete"
            title="Delete vision"
            onClick={(e) => handleDeleteVision(vision.id, e)}
          >
            ×
          </button>
        </header>

        <div className="workbench-vision-partitions">
          {renderDropSlot(vision.id, 'wireframe', 'Wireframe', wireframe, '0')}
          <div className="workbench-vision-ref-row">
            {refSlots.map((ref, i) =>
              renderDropSlot(vision.id, 'reference', `Reference ${i + 1}`, ref, String(i)),
            )}
          </div>
          <div
            className={`workbench-vision-media${dragOverZone === `${vision.id}-media` ? ' workbench-vision-media--drag-over' : ''}`}
            onDragOver={(e) => onDragOverZone(e, `${vision.id}-media`)}
            onDragLeave={onDragLeaveZone}
            onDrop={(e) => onDropZone(e, vision.id, 'media')}
          >
            <span className="workbench-vision-slot-label">Media</span>
            <div className="workbench-vision-grid">
              {media.length === 0 ? (
                <p className="workbench-vision-empty">Drop files here</p>
              ) : (
                media.map(renderAssetCard)
              )}
            </div>
          </div>
        </div>
      </section>
    );
  };

  return (
    <div className="portal-workbench-panel">
      <header className="portal-workbench-header">
        <h2 className="portal-workbench-title">Workbench</h2>
        <button type="button" className="portal-btn portal-btn--small" onClick={handleCreateVision}>
          + New vision
        </button>
      </header>
      {error ? <div className="error-message">{error}</div> : null}

      {visions.length === 0 ? (
        <p className="workbench-board-empty">
          Create a vision, then drag files from the left into wireframe, references, or media.
        </p>
      ) : (
        visions.map(renderVisionCluster)
      )}
    </div>
  );
}

export default MediaVisionBoard;
