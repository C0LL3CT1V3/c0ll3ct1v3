import React, { useState } from 'react';
import { getAssetDragId, setAssetDragData } from './mediaDrag';
import { externalUrlForAsset, isUrlReferenceAsset } from './mediaUrlDrop';

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
  createReferenceFromUrl,
  deleteAsset,
  createVision,
  renameVision,
  deleteVision,
  embedded = false,
}) {
  const [dragOverZone, setDragOverZone] = useState(null);
  const [referenceUrls, setReferenceUrls] = useState({});
  const [referenceSaving, setReferenceSaving] = useState(null);

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

  const renderAssetCard = (a) => {
    const urlRef = isUrlReferenceAsset(a);
    const externalUrl = externalUrlForAsset(a);
    return (
    <div
      key={a.id}
      className={`workbench-asset${selectedId === a.id ? ' workbench-asset--selected' : ''}${urlRef ? ' workbench-asset--url' : ''}`}
      draggable={!urlRef}
      onDragStart={urlRef ? undefined : (e) => setAssetDragData(e.dataTransfer, a.id)}
      onClick={() => onSelect?.(a.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onSelect?.(a.id);
      }}
    >
      {thumbs[a.id] ? (
        <img src={thumbs[a.id]} alt="" className="workbench-asset-thumb" />
      ) : urlRef ? (
        <span className="workbench-asset-thumb workbench-asset-thumb--link" aria-hidden title={externalUrl || ''}>
          ↗
        </span>
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
  };

  const submitReferenceUrl = async (visionId, slotKey) => {
    const draftKey = `${visionId}-${slotKey}`;
    const url = (referenceUrls[draftKey] || '').trim();
    if (!url) return;
    setReferenceSaving(draftKey);
    onError?.('');
    try {
      await createReferenceFromUrl(visionId, url);
      setReferenceUrls((prev) => {
        const next = { ...prev };
        delete next[draftKey];
        return next;
      });
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not add URL reference.');
    } finally {
      setReferenceSaving(null);
    }
  };

  const renderReferenceUrlForm = (visionId, slotKey) => {
    const draftKey = `${visionId}-${slotKey}`;
    const saving = referenceSaving === draftKey;
    return (
      <form
        className="workbench-reference-url-form"
        onSubmit={(e) => {
          e.preventDefault();
          submitReferenceUrl(visionId, slotKey);
        }}
      >
        <input
          type="url"
          className="workbench-reference-url-input"
          placeholder="https://..."
          value={referenceUrls[draftKey] || ''}
          disabled={saving}
          onChange={(e) =>
            setReferenceUrls((prev) => ({ ...prev, [draftKey]: e.target.value }))
          }
          onClick={(e) => e.stopPropagation()}
        />
        <button
          type="submit"
          className="portal-btn portal-btn--small workbench-reference-url-add"
          disabled={saving || !(referenceUrls[draftKey] || '').trim()}
        >
          {saving ? 'Adding…' : 'Add'}
        </button>
        <p className="workbench-vision-slot-empty">or drop a file</p>
      </form>
    );
  };

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
        {slotAsset ? (
          renderAssetCard(slotAsset)
        ) : role === 'reference' ? (
          renderReferenceUrlForm(visionId, slotKey)
        ) : (
          <p className="workbench-vision-slot-empty">Drop here</p>
        )}
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

  const boardBody = (
    <>
      {error ? <div className="error-message">{error}</div> : null}
      {visions.length === 0 ? (
        <p className="workbench-board-empty">
          Create a vision, paste reference URLs or drag files into wireframe, references, and media.
        </p>
      ) : (
        visions.map(renderVisionCluster)
      )}
    </>
  );

  if (embedded) {
    return (
      <div className="profile-vision-board-embedded">
        <div className="profile-vision-board-toolbar">
          <h3 className="profile-vision-board-label">Vision board</h3>
          <button type="button" className="portal-btn portal-btn--small" onClick={handleCreateVision}>
            + New vision
          </button>
        </div>
        {boardBody}
      </div>
    );
  }

  return (
    <div className="portal-workbench-panel media-vision-board">
      <header className="portal-workbench-header">
        <h2 className="portal-workbench-title">Vision board</h2>
        <button type="button" className="portal-btn portal-btn--small" onClick={handleCreateVision}>
          + New vision
        </button>
      </header>
      {boardBody}
    </div>
  );
}

export default MediaVisionBoard;
