export const DRAG_ASSET_MIME = 'application/x-c0-media-asset-id';

export function setAssetDragData(dataTransfer, assetId) {
  dataTransfer.setData(DRAG_ASSET_MIME, assetId);
  dataTransfer.effectAllowed = 'move';
}

export function getAssetDragId(dataTransfer) {
  return dataTransfer.getData(DRAG_ASSET_MIME);
}
