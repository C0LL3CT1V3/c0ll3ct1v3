import { useCallback, useEffect, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';
export function useEpkBooker(tenantSlug) {
  const { apiClient, authReady } = useApiClient();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.get('/artists/me/epk-public');
      setData(res.data);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load EPK.');
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    if (!authReady) return;
    load();
  }, [load, authReady]);

  const patch = async (payload) => {
    setBusy(true);
    try {
      const res = await apiClient.patch('/artists/me/epk-public', payload);
      setData(res.data);
      setError('');
      return res.data;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Save failed.';
      setError(msg);
      throw err;
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    setBusy(true);
    try {
      const res = await apiClient.post('/artists/me/epk-public/publish');
      setData(res.data);
      setError('');
      return res.data;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Publish failed.';
      setError(msg);
      throw err;
    } finally {
      setBusy(false);
    }
  };

  const downloadPdf = async () => {
    setBusy(true);
    try {
      const res = await apiClient.get('/artists/me/epk-public/pdf', { responseType: 'blob' });
      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tenantSlug || 'epk'}-press-kit.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'PDF export failed.';
      setError(msg);
      throw err;
    } finally {
      setBusy(false);
    }
  };

  const previewDraft = async () => {
    setBusy(true);
    setError('');
    try {
      const res = await apiClient.post('/artists/me/epk-public/preview-link');
      const url = res.data?.preview_url;
      if (!url) throw new Error('No preview URL returned.');
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Preview failed.';
      setError(msg);
      throw err;
    } finally {
      setBusy(false);
    }
  };

  return {
    data,
    config: data?.config,
    resolved: data?.resolved,
    completeness: data?.completeness,
    loading,
    error,
    busy,
    patch,
    publish,
    downloadPdf,
    previewDraft,
    reload: load,
  };
}
