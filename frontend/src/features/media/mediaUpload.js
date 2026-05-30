const EXTENSION_TYPES = {
  '.jpg': 'image',
  '.jpeg': 'image',
  '.png': 'image',
  '.gif': 'image',
  '.webp': 'image',
  '.avif': 'image',
  '.heic': 'image',
  '.heif': 'image',
  '.bmp': 'image',
  '.tif': 'image',
  '.tiff': 'image',
  '.svg': 'image',
  '.mp3': 'audio',
  '.wav': 'audio',
  '.flac': 'audio',
  '.aac': 'audio',
  '.m4a': 'audio',
  '.ogg': 'audio',
  '.opus': 'audio',
  '.wma': 'audio',
  '.mp4': 'video',
  '.mov': 'video',
  '.webm': 'video',
  '.mkv': 'video',
  '.m4v': 'video',
  '.zip': 'archive',
};

/**
 * Detect media category from MIME type and file extension.
 * Extension wins when MIME is missing or generic (common on drag-drop).
 */
export function guessAssetType(file) {
  const name = (file?.name || '').toLowerCase();
  const dot = name.lastIndexOf('.');
  const ext = dot >= 0 ? name.slice(dot) : '';

  if (ext && EXTENSION_TYPES[ext]) {
    return EXTENSION_TYPES[ext];
  }

  const mime = (file?.type || '').toLowerCase();
  if (mime.startsWith('image/')) return 'image';
  if (mime.startsWith('audio/')) return 'audio';
  if (mime.startsWith('video/')) return 'video';
  if (mime === 'application/zip' || mime === 'application/x-zip-compressed') return 'archive';

  return 'document';
}

export async function uploadFileToSpaces(apiClient, file, assetType, tenantSlug) {
  const resolvedType = assetType === 'auto' || !assetType ? guessAssetType(file) : assetType;
  const mime =
    file.type && file.type !== 'application/octet-stream'
      ? file.type
      : mimeFromExtension(file.name) || 'application/octet-stream';

  const initRes = await apiClient.post('/media/uploads/init', {
    filename: file.name,
    mime_type: mime,
    byte_size: file.size,
    asset_type: resolvedType,
    title: file.name.replace(/\.[^.]+$/, ''),
    tenant_slug: tenantSlug || undefined,
  });

  const { upload_row_id, parts, chunk_size_bytes } = initRes.data;
  const uploadedParts = [];

  for (const part of parts) {
    const start = (part.part_number - 1) * chunk_size_bytes;
    const end = Math.min(start + chunk_size_bytes, file.size);
    const blob = file.slice(start, end);

    const putRes = await fetch(part.url, {
      method: 'PUT',
      body: blob,
      headers: { 'Content-Type': mime },
    });
    if (!putRes.ok) {
      throw new Error(`Part ${part.part_number} upload failed (${putRes.status})`);
    }
    const etag = putRes.headers.get('ETag') || putRes.headers.get('etag');
    if (!etag) {
      throw new Error(`Part ${part.part_number} missing ETag header`);
    }
    uploadedParts.push({ part_number: part.part_number, etag });
  }

  const completeRes = await apiClient.post('/media/uploads/complete', {
    upload_row_id,
    parts: uploadedParts,
  });
  return completeRes.data;
}

function mimeFromExtension(filename) {
  const name = (filename || '').toLowerCase();
  const dot = name.lastIndexOf('.');
  const ext = dot >= 0 ? name.slice(dot) : '';
  const map = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.zip': 'application/zip',
  };
  return map[ext] || null;
}
