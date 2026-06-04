/** Public app identifiers for official Dropbox Chooser / Google Picker (not server secrets). */

function readEnv(key) {
  const v = process.env[key];
  if (!v || v.startsWith('your-') || v === 'undefined') return '';
  return v.trim();
}

export const dropboxAppKey = readEnv('REACT_APP_DROPBOX_APP_KEY');

export const googlePickerConfig = {
  clientId: readEnv('REACT_APP_GOOGLE_CLIENT_ID'),
  apiKey: readEnv('REACT_APP_GOOGLE_API_KEY'),
  appId: readEnv('REACT_APP_GOOGLE_APP_ID'),
};

/** Google Picker needs the numeric Cloud project number, not the project id string. */
export function isValidGoogleAppId(appId) {
  return /^\d+$/.test(appId);
}

/** API keys start with AIza; GOCSPX- is an OAuth client secret (wrong field). */
export function isLikelyGoogleApiKey(apiKey) {
  return apiKey.startsWith('AIza');
}

export function isDropboxChooserEnabled() {
  return Boolean(dropboxAppKey);
}

export function getDropboxDisabledReason() {
  if (dropboxAppKey) return null;
  return 'REACT_APP_DROPBOX_APP_KEY is missing. Restart the frontend after editing .env (Docker must mount frontend/.env).';
}

export function isGooglePickerEnabled() {
  const { clientId, apiKey, appId } = googlePickerConfig;
  if (!clientId || !apiKey || !appId) return false;
  if (!isValidGoogleAppId(appId)) return false;
  if (!isLikelyGoogleApiKey(apiKey)) return false;
  return true;
}

export function getGoogleDisabledReason() {
  const { clientId, apiKey, appId } = googlePickerConfig;
  if (!clientId) {
    return 'REACT_APP_GOOGLE_CLIENT_ID is missing.';
  }
  if (!apiKey) {
    return 'REACT_APP_GOOGLE_API_KEY is missing.';
  }
  if (apiKey && !isLikelyGoogleApiKey(apiKey)) {
    return 'REACT_APP_GOOGLE_API_KEY looks like an OAuth client secret (GOCSPX-…). Create an API key (starts with AIza…) in Google Cloud Console → Credentials.';
  }
  if (!appId) {
    return 'REACT_APP_GOOGLE_APP_ID is missing.';
  }
  if (appId && !isValidGoogleAppId(appId)) {
    return 'REACT_APP_GOOGLE_APP_ID must be your numeric Google Cloud project number (e.g. 1078777420877), not the project id string.';
  }
  return 'Restart the frontend after editing .env (Docker must mount frontend/.env).';
}
