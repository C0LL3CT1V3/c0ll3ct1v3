/**
 * Official Dropbox Chooser + Google Picker (user signs in via Dropbox / Google UI).
 * @see https://www.dropbox.com/developers/chooser
 * @see https://developers.google.com/drive/picker
 */

import { dropboxAppKey, googlePickerConfig } from './cloudImportConfig';

/** @typedef {{ name: string, link: string, bytes?: number }} DropboxChooserEntry */
/** @typedef {{ id: string, name: string, mimeType?: string }} GooglePickerEntry */

const DROPBOX_SCRIPT = 'https://www.dropbox.com/static/api/2/dropins.js';
const GOOGLE_GSI = 'https://accounts.google.com/gsi/client';
const GOOGLE_API = 'https://apis.google.com/js/api.js';

const MEDIA_EXTENSIONS = [
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
  '.mp3',
  '.wav',
  '.flac',
  '.m4a',
  '.mp4',
  '.mov',
  '.webm',
  '.mkv',
  '.zip',
  '.pdf',
];

const GOOGLE_PICKER_MIMES =
  'image/png,image/jpeg,image/gif,image/webp,audio/mpeg,audio/wav,audio/flac,video/mp4,video/quicktime,application/zip,application/pdf';

function loadScript(src, id) {
  return new Promise((resolve, reject) => {
    const byId = id ? document.getElementById(id) : null;
    if (byId?.getAttribute('data-loaded') === 'true') {
      resolve();
      return;
    }
    const existing = byId || document.querySelector(`script[src="${src}"]`);
    if (existing) {
      if (existing.getAttribute('data-loaded') === 'true') {
        resolve();
        return;
      }
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), {
        once: true,
      });
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    if (id) script.id = id;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      script.setAttribute('data-loaded', 'true');
      resolve();
    };
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.body.appendChild(script);
  });
}

function ensureDropboxChooser() {
  if (!dropboxAppKey) {
    return Promise.reject(new Error('REACT_APP_DROPBOX_APP_KEY is missing.'));
  }
  return new Promise((resolve, reject) => {
    const existing = document.getElementById('dropboxjs');
    if (existing?.getAttribute('data-loaded') === 'true' && window.Dropbox) {
      resolve();
      return;
    }
    const script = existing || document.createElement('script');
    script.id = 'dropboxjs';
    script.type = 'text/javascript';
    script.async = true;
    // Dropbox requires data-app-key on the script tag before dropins.js loads.
    script.setAttribute('data-app-key', dropboxAppKey);
    if (existing?.getAttribute('data-loaded') === 'true') {
      if (window.Dropbox) {
        resolve();
        return;
      }
      existing.remove();
      return ensureDropboxChooser().then(resolve, reject);
    }
    script.onload = () => {
      script.setAttribute('data-loaded', 'true');
      if (!window.Dropbox) {
        reject(new Error('Dropbox Chooser failed to load.'));
        return;
      }
      resolve();
    };
    script.onerror = () => reject(new Error('Failed to load Dropbox Chooser script.'));
    script.src = DROPBOX_SCRIPT;
    if (!existing) {
      document.body.appendChild(script);
    }
  });
}

/** Opens Dropbox Chooser; returns metadata (name + direct link) for server import. */
export function pickDropboxChooserEntries() {
  return ensureDropboxChooser().then(
    () =>
      new Promise((resolve, reject) => {
        window.Dropbox.choose({
          linkType: 'direct',
          multiselect: true,
          extensions: MEDIA_EXTENSIONS,
          // Must be synchronous — async handlers can lose the download before links expire.
          success: (files) => {
            const entries = (files || []).map((f) => ({
              name: f.name,
              link: f.link,
              bytes: f.bytes,
            }));
            resolve(entries);
          },
          cancel: () => resolve([]),
          error: (message) => reject(new Error(message || 'Dropbox Chooser error')),
        });
      }),
  );
}

/** Server downloads Chooser direct links (avoids browser CORS) and ingests into workbench. */
export async function importDropboxChooserEntries(apiClient, entries, tenantSlug) {
  const items = (entries || []).map((e) => ({
    name: e.name,
    link: e.link,
    bytes: e.bytes ?? undefined,
  }));
  if (!items.length) return [];
  const res = await apiClient.post('/media/chooser/dropbox/import', {
    items,
    tenant_slug: tenantSlug || undefined,
  });
  return res.data?.imported || [];
}

/** @deprecated Use pickDropboxChooserEntries + importDropboxChooserEntries */
export function pickFilesFromDropboxChooser() {
  return pickDropboxChooserEntries();
}

function loadGooglePicker() {
  return loadScript(GOOGLE_GSI, 'google-gsi').then(
    () =>
      new Promise((resolve, reject) => {
        if (window.gapi?.picker) {
          resolve();
          return;
        }
        loadScript(GOOGLE_API, 'google-api')
          .then(() => {
            window.gapi.load('picker', { callback: resolve, onerror: reject });
          })
          .catch(reject);
      }),
  );
}

function requestGoogleAccessToken() {
  return new Promise((resolve, reject) => {
    if (!window.google?.accounts?.oauth2) {
      reject(new Error('Google Identity Services failed to load.'));
      return;
    }
    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: googlePickerConfig.clientId,
      scope: 'https://www.googleapis.com/auth/drive.readonly',
      callback: (response) => {
        if (response?.error) {
          reject(new Error(response.error));
          return;
        }
        resolve(response.access_token);
      },
    });
    client.requestAccessToken();
  });
}

function openGooglePicker(accessToken) {
  return new Promise((resolve) => {
    const view = new window.google.picker.DocsView(window.google.picker.ViewId.DOCS)
      .setIncludeFolders(true)
      .setMimeTypes(GOOGLE_PICKER_MIMES)
      .setSelectFolderEnabled(false);

    const picker = new window.google.picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(accessToken)
      .setDeveloperKey(googlePickerConfig.apiKey)
      .setAppId(googlePickerConfig.appId)
      .setOrigin(window.location.origin)
      .enableFeature(window.google.picker.Feature.MULTISELECT_ENABLED)
      .setCallback((data) => {
        // Callback fires on load, pick, cancel, etc. — only resolve on final user actions.
        if (data.action === window.google.picker.Action.PICKED) {
          resolve(data.docs || []);
        } else if (data.action === window.google.picker.Action.CANCEL) {
          resolve([]);
        }
      })
      .build();
    picker.setVisible(true);
  });
}

/** Google Picker + GIS OAuth; returns metadata for server import (avoids browser CORS). */
export async function pickGooglePickerEntries() {
  await loadGooglePicker();
  const accessToken = await requestGoogleAccessToken();
  const docs = await openGooglePicker(accessToken);
  const entries = (docs || []).map((doc) => ({
    id: doc.id,
    name: doc.name || 'drive-file',
    mimeType: doc.mimeType,
  }));
  return { entries, accessToken };
}

/** Server downloads Picker selections (avoids browser CORS) and ingests into workbench. */
export async function importGooglePickerEntries(apiClient, entries, accessToken, tenantSlug) {
  const items = (entries || []).map((e) => ({
    id: e.id,
    name: e.name,
    mime_type: e.mimeType || undefined,
  }));
  if (!items.length) return [];
  const res = await apiClient.post('/media/chooser/google/import', {
    access_token: accessToken,
    items,
    tenant_slug: tenantSlug || undefined,
  });
  return res.data?.imported || [];
}
