import React, { useState } from 'react';
import {
  getDropboxDisabledReason,
  getDropboxMisconfiguredHint,
  getGoogleDisabledReason,
  isDropboxChooserEnabled,
  isGooglePickerEnabled,
} from './cloudImportConfig';
import {
  importDropboxChooserEntries,
  importGooglePickerEntries,
  pickDropboxChooserEntries,
  pickGooglePickerEntries,
} from './cloudChoosers';
import { guessAssetType, uploadFileToSpaces } from './mediaUpload';

function MediaDropzone({ apiClient, tenantSlug, onUploaded, onError }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');

  const dropboxEnabled = isDropboxChooserEnabled();
  const googleEnabled = isGooglePickerEnabled();
  const dropboxDisabledReason = getDropboxDisabledReason();
  const googleDisabledReason = getGoogleDisabledReason();

  const uploadFiles = async (files) => {
    const list = Array.from(files || []);
    if (!list.length) return;
    setUploading(true);
    onError?.('');
    try {
      for (let i = 0; i < list.length; i += 1) {
        const file = list[i];
        setUploadProgress(`Uploading ${file.name} (${i + 1}/${list.length})…`);
        await uploadFileToSpaces(apiClient, file, guessAssetType(file), tenantSlug);
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

  const handleDropbox = async () => {
    if (!dropboxEnabled || uploading) return;
    setUploading(true);
    onError?.('');
    try {
      setUploadProgress('Opening Dropbox…');
      const entries = await pickDropboxChooserEntries();
      if (!entries.length) {
        setUploadProgress('');
        return;
      }
      setUploadProgress(`Importing ${entries.length} file(s) from Dropbox…`);
      await importDropboxChooserEntries(apiClient, entries, tenantSlug);
      setUploadProgress('');
      onUploaded?.();
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Dropbox import failed.';
      const hint =
        /misconfigur|not configured properly/i.test(String(msg)) ? getDropboxMisconfiguredHint() : '';
      onError?.(hint ? `${msg} ${hint}` : msg);
      setUploadProgress('');
    } finally {
      setUploading(false);
    }
  };

  const handleGoogleDrive = async () => {
    if (!googleEnabled || uploading) return;
    setUploading(true);
    onError?.('');
    try {
      setUploadProgress('Opening Google Drive…');
      const { entries, accessToken } = await pickGooglePickerEntries();
      if (!entries.length) {
        setUploadProgress('');
        return;
      }
      setUploadProgress(`Importing ${entries.length} file(s) from Google Drive…`);
      await importGooglePickerEntries(apiClient, entries, accessToken, tenantSlug);
      setUploadProgress('');
      onUploaded?.();
    } catch (err) {
      onError?.(err?.response?.data?.detail || err.message || 'Google Drive import failed.');
      setUploadProgress('');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      className={`media-dropzone${dragOver ? ' media-dropzone--active' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        if (!uploading) uploadFiles(e.dataTransfer.files);
      }}
    >
      <div className="media-upload-actions">
        <label className="portal-btn portal-btn--ghost media-file-label">
          Choose files
          <input
            type="file"
            multiple
            disabled={uploading}
            onChange={(e) => {
              uploadFiles(e.target.files);
              e.target.value = '';
            }}
          />
        </label>
        <button
          type="button"
          className="portal-btn portal-btn--ghost media-cloud-btn"
          disabled={uploading || !dropboxEnabled}
          onClick={handleDropbox}
          title={dropboxEnabled ? 'Import from Dropbox (official Chooser)' : dropboxDisabledReason}
        >
          Dropbox
        </button>
        <button
          type="button"
          className="portal-btn portal-btn--ghost media-cloud-btn"
          disabled={uploading || !googleEnabled}
          onClick={handleGoogleDrive}
          title={googleEnabled ? 'Import from Google Drive (official Picker)' : googleDisabledReason}
        >
          Google Drive
        </button>
      </div>
      <p className="media-dropzone-hint">or drop files here</p>
      {!dropboxEnabled && dropboxDisabledReason ? (
        <p className="media-dropzone-config-hint media-dropzone-config-hint--warn">{dropboxDisabledReason}</p>
      ) : null}
      {!googleEnabled && googleDisabledReason ? (
        <p className="media-dropzone-config-hint media-dropzone-config-hint--warn">{googleDisabledReason}</p>
      ) : null}
      {uploadProgress ? <p className="upload-progress">{uploadProgress}</p> : null}
    </div>
  );
}

export default MediaDropzone;
