import React, { useState } from 'react';
import AssetListThumb from '../media/AssetListThumb';
import { getAssetDragId, setAssetDragData } from '../media/mediaDrag';

function VaultFolderBoard({
  visions,
  assets,
  assetsByVision,
  thumbs,
  selectedId,
  onSelect,
  error,
  onError,
  assignAssetToFolder,
  deleteAsset,
  createVision,
  renameVision,
  deleteVision,
}) {
  const [dragOverId, setDragOverId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const onDragOver = (e, folderId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverId(folderId);
  };

  const onDragLeave = () => setDragOverId(null);

  const onDrop = async (e, visionId) => {
    e.preventDefault();
    setDragOverId(null);
    const assetId = getAssetDragId(e.dataTransfer);
    if (!assetId) return;
    const asset = assets.find((a) => a.id === assetId);
    if (!asset || asset.vision_id === visionId) return;
    try {
      await assignAssetToFolder(assetId, visionId);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not move file.');
    }
  };

  const onDropUngrouped = async (e) => {
    e.preventDefault();
    setDragOverId(null);
    const assetId = getAssetDragId(e.dataTransfer);
    if (!assetId) return;
    try {
      await assignAssetToFolder(assetId, null);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not remove from folder.');
    }
  };

  const handleCreate = async () => {
    try {
      await createVision('New folder');
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not create folder.');
    }
  };

  const startRename = (vision) => {
    setEditingId(vision.id);
    setEditTitle(vision.title);
  };

  const commitRename = async (visionId) => {
    const trimmed = editTitle.trim();
    setEditingId(null);
    if (!trimmed) return;
    try {
      await renameVision(visionId, trimmed);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Rename failed.');
    }
  };

  const handleDeleteVision = async (visionId) => {
    if (!window.confirm('Delete this folder? Files will move back to ungrouped.')) return;
    try {
      await deleteVision(visionId);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Could not delete folder.');
    }
  };

  const handleDeleteAsset = async (assetId, e) => {
    e.stopPropagation();
    if (!window.confirm('Remove this file from the Vault?')) return;
    try {
      await deleteAsset(assetId);
      if (selectedId === assetId) onSelect?.(null);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Delete failed.');
    }
  };

  const renderAsset = (a) => (
    <div
      key={a.id}
      className={`vault-folder-asset${selectedId === a.id ? ' vault-folder-asset--selected' : ''}`}
      draggable
      onDragStart={(e) => setAssetDragData(e.dataTransfer, a.id)}
      onClick={() => onSelect?.(a.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onSelect?.(a.id);
      }}
    >
      <AssetListThumb asset={a} thumbUrl={thumbs[a.id]} />
      <span className="vault-folder-asset-title">{a.title || 'Untitled'}</span>
      <button
        type="button"
        className="vault-folder-asset-delete"
        onClick={(e) => handleDeleteAsset(a.id, e)}
        aria-label="Delete file"
      >
        ×
      </button>
    </div>
  );

  const ungrouped = assetsByVision.ungrouped || [];

  return (
    <section className="vault-folder-board">
      <div className="vault-folder-board-toolbar">
        <h2 className="portal-panel-title">Folders</h2>
        <button type="button" className="portal-btn portal-btn--ghost" onClick={handleCreate}>
          + New folder
        </button>
      </div>
      {error ? <div className="error-message">{error}</div> : null}
      <div className="vault-folder-grid">
        {visions.map((vision) => {
          const items = assetsByVision.grouped[vision.id] || [];
          const isOver = dragOverId === vision.id;
          return (
            <div
              key={vision.id}
              className={`vault-folder-card${isOver ? ' vault-folder-card--drag-over' : ''}`}
              onDragOver={(e) => onDragOver(e, vision.id)}
              onDragLeave={onDragLeave}
              onDrop={(e) => onDrop(e, vision.id)}
            >
              <header className="vault-folder-card-header">
                {editingId === vision.id ? (
                  <input
                    className="vault-folder-rename-input"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => commitRename(vision.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitRename(vision.id);
                      if (e.key === 'Escape') setEditingId(null);
                    }}
                    autoFocus
                  />
                ) : (
                  <button
                    type="button"
                    className="vault-folder-title"
                    onClick={() => startRename(vision)}
                  >
                    {vision.title}
                  </button>
                )}
                <span className="vault-folder-count">{items.length}</span>
                <button
                  type="button"
                  className="vault-folder-delete"
                  onClick={() => handleDeleteVision(vision.id)}
                  aria-label="Delete folder"
                >
                  ×
                </button>
              </header>
              <div className="vault-folder-dropzone">
                {items.length === 0 ? (
                  <p className="vault-folder-empty">Drop files here</p>
                ) : (
                  items.map(renderAsset)
                )}
              </div>
            </div>
          );
        })}
      </div>
      <div
        className={`vault-ungrouped${dragOverId === 'ungrouped' ? ' vault-ungrouped--drag-over' : ''}`}
        onDragOver={(e) => onDragOver(e, 'ungrouped')}
        onDragLeave={onDragLeave}
        onDrop={onDropUngrouped}
      >
        <h3 className="vault-ungrouped-title">Ungrouped ({ungrouped.length})</h3>
        <div className="vault-ungrouped-list">
          {ungrouped.length === 0 ? (
            <p className="vault-folder-empty">Files not in a folder appear here</p>
          ) : (
            ungrouped.map(renderAsset)
          )}
        </div>
      </div>
    </section>
  );
}

export default VaultFolderBoard;
