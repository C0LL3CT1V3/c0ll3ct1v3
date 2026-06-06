import React, { useState } from 'react';
import MediaDropzone from './MediaDropzone';
import { setAssetDragData } from './mediaDrag';

function MediaFileSidebar({
  apiClient,
  tenantSlug,
  onUploaded,
  onError,
  mediaError,
  assets,
  thumbs,
  visionTitleById,
  selectedId,
  onSelect,
  onDeleteAsset,
}) {
  const [open, setOpen] = useState(true);

  const handleDelete = async (assetId, e) => {
    e.stopPropagation();
    if (!window.confirm('Remove this file from the workbench?')) return;
    try {
      await onDeleteAsset(assetId);
      if (selectedId === assetId) onSelect?.(null);
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Delete failed.');
    }
  };

  return (
    <aside className={`portal-sidebar${open ? ' portal-sidebar--open' : ''}`}>
      <button
        type="button"
        className="portal-sidebar-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="portal-sidebar-toggle-label">Files</span>
        <span className="portal-sidebar-toggle-chevron" aria-hidden>
          {open ? '◀' : '▶'}
        </span>
      </button>
      {open ? (
        <div className="portal-sidebar-body">
          {mediaError ? <div className="error-message">{mediaError}</div> : null}
          <MediaDropzone
            apiClient={apiClient}
            tenantSlug={tenantSlug}
            onUploaded={onUploaded}
            onError={onError}
          />
          <p className="portal-sidebar-hint">Drag files into a vision on the right.</p>
          <ul className="portal-file-list">
            {assets.length === 0 ? (
              <li className="portal-file-list-empty">No files yet.</li>
            ) : (
              assets.map((a) => (
                <li key={a.id}>
                  <div
                    className={`portal-file-item${selectedId === a.id ? ' portal-file-item--selected' : ''}`}
                    draggable
                    onDragStart={(e) => setAssetDragData(e.dataTransfer, a.id)}
                    onClick={() => onSelect?.(a.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') onSelect?.(a.id);
                    }}
                  >
                    {thumbs[a.id] ? (
                      <img src={thumbs[a.id]} alt="" className="portal-file-thumb" />
                    ) : (
                      <span className="portal-file-thumb portal-file-thumb--placeholder" aria-hidden>
                        ·
                      </span>
                    )}
                    <div className="portal-file-meta">
                      <span className="portal-file-title">{a.title || 'Untitled'}</span>
                      {a.vision_id && visionTitleById[a.vision_id] ? (
                        <span className="portal-file-vision">{visionTitleById[a.vision_id]}</span>
                      ) : null}
                      {a.tags?.vision_role && a.tags.vision_role !== 'media' ? (
                        <span className="portal-file-role">{a.tags.vision_role}</span>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      className="portal-file-delete"
                      title="Delete"
                      onClick={(e) => handleDelete(a.id, e)}
                    >
                      ×
                    </button>
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

export default MediaFileSidebar;
