import React, { useState } from 'react';
import { getAssetDragId } from './mediaDrag';

function MediaVisionBoard({
  visions,
  assets,
  assetsByVision,
  thumbs,
  selectedId,
  onSelect,
  error,
  onError,
  assignAsset,
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

  const onDropZone = async (e, visionId) => {
    e.preventDefault();
    setDragOverZone(null);
    const assetId = getAssetDragId(e.dataTransfer);
    if (!assetId) return;
    const asset = assets.find((a) => a.id === assetId);
    if (!asset || asset.vision_id === visionId) return;
    try {
      await assignAsset(assetId, visionId);
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
      {a.status === 'processing' ? (
        <span className="workbench-asset-meta">Processing…</span>
      ) : null}
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

  const renderVisionCluster = (vision) => {
    const zoneId = `vision-${vision.id}`;
    const items = assetsByVision.grouped[vision.id] || [];
    return (
      <section
        key={vision.id}
        className={`workbench-vision${dragOverZone === zoneId ? ' workbench-vision--drag-over' : ''}`}
        onDragOver={(e) => onDragOverZone(e, zoneId)}
        onDragLeave={onDragLeaveZone}
        onDrop={(e) => onDropZone(e, vision.id)}
      >
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
        <div className="workbench-vision-grid">
          {items.length === 0 ? (
            <p className="workbench-vision-empty">Drop files here</p>
          ) : (
            items.map(renderAssetCard)
          )}
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
          Create a vision, then drag files from the left into it.
        </p>
      ) : (
        visions.map(renderVisionCluster)
      )}
    </div>
  );
}

export default MediaVisionBoard;
