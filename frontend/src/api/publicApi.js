import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

export function publicProfileUrl(tenantSlug) {
  return `${API_BASE_URL}/artists/public/${tenantSlug}`;
}

export function publicPageUrl(tenantSlug) {
  return `${API_BASE_URL}/artists/public/${tenantSlug}/page`;
}

export async function fetchPublicProfile(tenantSlug) {
  const res = await axios.get(publicProfileUrl(tenantSlug));
  return res.data;
}
