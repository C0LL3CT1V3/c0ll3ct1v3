/** Resolve layout blocks by stable id (falls back to type for legacy layouts). */

export function blockById(layout, id, typeFallback) {
  if (!Array.isArray(layout)) return {};
  const byId = layout.find((b) => b.id === id);
  if (byId) return byId;
  if (typeFallback) {
    return layout.find((b) => b.type === typeFallback) || {};
  }
  return {};
}

export function blockByType(layout, type) {
  if (!Array.isArray(layout)) return {};
  return layout.find((b) => b.type === type) || {};
}

export function collectAssetIds(layout, type) {
  const block = blockByType(layout, type);
  return block.asset_ids || [];
}
