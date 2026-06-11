export function isUrlReferenceAsset(asset) {
  return asset?.tags?.source === 'url' && Boolean(asset?.tags?.external_url);
}

export function externalUrlForAsset(asset) {
  if (!isUrlReferenceAsset(asset)) return null;
  return asset.tags.external_url;
}

export function isLikelyImageUrl(url) {
  try {
    const path = new URL(url).pathname.toLowerCase();
    return /\.(png|jpe?g|gif|webp|svg|avif|bmp)(\?|$)/i.test(path);
  } catch {
    return false;
  }
}
