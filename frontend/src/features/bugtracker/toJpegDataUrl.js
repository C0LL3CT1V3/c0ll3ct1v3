export const MAX_EDGE = 1920;
export const JPEG_QUALITY = 0.72;

export function scaledSize(width, height, maxEdge = MAX_EDGE) {
  const w = Number(width) || 0;
  const h = Number(height) || 0;
  const longest = Math.max(w, h);
  if (!w || !h || longest <= maxEdge) return { width: w, height: h };
  const scale = maxEdge / longest;
  return { width: Math.round(w * scale), height: Math.round(h * scale) };
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Could not read screenshot'));
    img.src = src;
  });
}

/**
 * Normalize Shotmark (or any) image output to a JPEG data URL under MAX_EDGE.
 * @param {string | Blob} image
 */
export async function toJpegDataUrl(image, { maxEdge = MAX_EDGE, quality = JPEG_QUALITY } = {}) {
  let src = '';
  if (typeof image === 'string' && image.startsWith('data:image/')) {
    src = image;
  } else if (typeof Blob !== 'undefined' && image instanceof Blob) {
    src = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('Could not read screenshot'));
      reader.readAsDataURL(image);
    });
  } else {
    throw new Error('Screenshot is empty');
  }

  const img = await loadImage(src);
  const { width, height } = scaledSize(img.naturalWidth || img.width, img.naturalHeight || img.height, maxEdge);
  if (!width || !height) throw new Error('Empty screenshot frame');

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas is unavailable');
  ctx.drawImage(img, 0, 0, width, height);
  return canvas.toDataURL('image/jpeg', quality);
}
