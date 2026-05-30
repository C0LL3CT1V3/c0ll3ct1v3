import React, { useState } from 'react';
import { guessAssetType, uploadFileToSpaces } from './mediaUpload';

const ASSET_TYPES = [
  { value: 'auto', label: 'Auto-detect from file' },
  { value: 'audio', label: 'Audio' },
  { value: 'image', label: 'Image' },
  { value: 'video', label: 'Video' },
  { value: 'document', label: 'Document' },
  { value: 'archive', label: 'Archive (ZIP)' },
];

function MediaDropzone({ apiClient, tenantSlug, onUploaded, onError }) {
  const [typeOverride, setTypeOverride] = useState('auto');
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    setUploading(true);
    onError?.('');
    try {
      for (let i = 0; i < files.length; i += 1) {
        const file = files[i];
        const type = typeOverride === 'auto' ? guessAssetType(file) : typeOverride;
        setUploadProgress(
          `Uploading ${file.name} as ${type} (${i + 1}/${files.length})…`,
        );
        await uploadFileToSpaces(apiClient, file, type, tenantSlug);
      }
      setUploadProgress('');
      onUploaded?.();
    } catch (err) {
      onError?.(err?.response?.data?.detail || err.message || 'Upload failed.');
      setUploadProgress('');
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (!uploading) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div className="media-dropzone-panel">
      <label htmlFor="portal-asset-type">Upload as</label>
      <select
        id="portal-asset-type"
        value={typeOverride}
        onChange={(e) => setTypeOverride(e.target.value)}
        disabled={uploading}
      >
        {ASSET_TYPES.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>

      <div
        className={`media-dropzone${dragOver ? ' media-dropzone--active' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <p>Drop files here or choose — type is detected from extension and MIME type.</p>
        <label className="portal-btn portal-btn--ghost media-file-label">
          Choose files
          <input
            type="file"
            multiple
            disabled={uploading}
            onChange={(e) => {
              handleFiles(e.target.files);
              e.target.value = '';
            }}
          />
        </label>
        {uploadProgress ? <p className="upload-progress">{uploadProgress}</p> : null}
      </div>
    </div>
  );
}

export default MediaDropzone;
