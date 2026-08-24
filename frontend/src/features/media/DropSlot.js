import React, { useState } from 'react';
import { getAssetDragId } from './mediaDrag';

function DropSlot({
  label,
  children,
  onDrop,
  onClear,
  className = '',
  acceptTypes,
  assets,
}) {
  const [over, setOver] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setOver(false);
    const assetId = getAssetDragId(e.dataTransfer);
    if (!assetId) return;
    const asset = assets.find((a) => a.id === assetId);
    if (!asset) return;
    if (acceptTypes && !acceptTypes.includes(asset.asset_type)) return;
    onDrop(assetId);
  };

  return (
    <div
      className={`epk-booker-slot${over ? ' epk-booker-slot--over' : ''} ${className}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={handleDrop}
    >
      <div className="epk-booker-slot-header">
        <span>{label}</span>
        {onClear ? (
          <button type="button" className="portal-btn portal-btn--ghost epk-booker-clear" onClick={onClear}>
            Remove
          </button>
        ) : null}
      </div>
      <div className="epk-booker-slot-body">{children}</div>
    </div>
  );
}

export default DropSlot;
