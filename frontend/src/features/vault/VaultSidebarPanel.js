import React, { useState } from 'react';
import AssetListThumb from '../media/AssetListThumb';
import { setAssetDragData } from '../media/mediaDrag';

function VaultSidebarPanel({
  assets,
  thumbs,
  filterType,
  onError,
  onDeleteAsset,
  title = 'Vault',
  hint = 'Drag files into slots.',
}) {
  const [open, setOpen] = useState(true);

  const filtered = filterType
    ? assets.filter((a) => a.asset_type === filterType)
    : assets;

  const handleDelete = async (assetId, e) => {
    e.stopPropagation();
    if (!onDeleteAsset) return;
    if (!window.confirm('Remove this file from the Vault?')) return;
    try {
      await onDeleteAsset(assetId);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Delete failed.');
    }
  };

  return (
    <aside className={`portal-sidebar vault-sidebar-panel${open ? ' portal-sidebar--open' : ''}`}>
      <button
        type="button"
        className="portal-sidebar-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="portal-sidebar-toggle-label">{title}</span>
        <span className="portal-sidebar-toggle-chevron" aria-hidden>
          {open ? '◀' : '▶'}
        </span>
      </button>
      {open ? (
        <div className="portal-sidebar-body">
          <p className="portal-sidebar-hint">{hint}</p>
          <ul className="portal-file-list">
            {filtered.length === 0 ? (
              <li className="portal-file-list-empty">No matching files in Vault.</li>
            ) : (
              filtered.map((a) => (
                <li key={a.id}>
                  <div
                    className="portal-file-item"
                    draggable
                    onDragStart={(e) => setAssetDragData(e.dataTransfer, a.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <AssetListThumb asset={a} thumbUrl={thumbs[a.id]} />
                    <div className="portal-file-meta">
                      <span className="portal-file-title">{a.title || 'Untitled'}</span>
                      <span className="portal-file-type">{a.asset_type}</span>
                    </div>
                    {onDeleteAsset ? (
                      <button
                        type="button"
                        className="portal-file-delete"
                        title="Remove from Vault"
                        onClick={(e) => handleDelete(a.id, e)}
                      >
                        ×
                      </button>
                    ) : null}
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>
      ) : null}
    </aside>
  );
}

export default VaultSidebarPanel;
