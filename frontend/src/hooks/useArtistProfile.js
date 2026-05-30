import { useCallback, useEffect, useState } from 'react';
import { useApiClient } from './useApiClient';

export function useArtistProfile() {
  const { apiClient, authReady } = useApiClient();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/artists/me');
      setProfile(res.data);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load artist profile.');
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    if (!authReady) return;
    refresh();
  }, [refresh, authReady]);

  const updateProfile = useCallback(
    async (payload) => {
      const res = await apiClient.patch('/artists/me', payload);
      setProfile(res.data);
      return res.data;
    },
    [apiClient],
  );

  return { profile, loading, error, refresh, updateProfile };
}
