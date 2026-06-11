import { useCallback, useEffect, useMemo, useState } from 'react';
import { externalUrlForAsset, isLikelyImageUrl } from './mediaUrlDrop';

export function useWorkbench(apiClient, authReady, refreshKey) {
  const [visions, setVisions] = useState([]);
  const [assets, setAssets] = useState([]);
  const [error, setError] = useState('');
  const [thumbs, setThumbs] = useState({});

  const loadWorkbench = useCallback(async () => {
    try {
      const res = await apiClient.get('/media/workbench');
      setVisions(res.data.visions || []);
      setAssets(res.data.assets || []);
      setError('');
    } catch (err) {
      if (err?.response?.status === 401) {
        setError('Not signed in or session expired. Log out and sign in again.');
      } else {
        setError(err?.response?.data?.detail || 'Failed to load workbench.');
      }
    }
  }, [apiClient]);

  useEffect(() => {
    if (!authReady) return;
    loadWorkbench();
  }, [loadWorkbench, refreshKey, authReady]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = {};
      for (const a of assets) {
        const external = externalUrlForAsset(a);
        if (external) {
          if (isLikelyImageUrl(external)) next[a.id] = external;
          continue;
        }
        if (a.asset_type !== 'image') continue;
        try {
          const res = await apiClient.get(`/media/assets/${a.id}/preview-url`);
          if (res.data?.url) next[a.id] = res.data.url;
        } catch {
          /* ignore */
        }
      }
      if (!cancelled) setThumbs(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [assets, apiClient]);

  const visionTitleById = useMemo(() => {
    const map = {};
    for (const v of visions) {
      map[v.id] = v.title;
    }
    return map;
  }, [visions]);

  const assetsByVision = useMemo(() => {
    const grouped = {};
    for (const v of visions) {
      grouped[v.id] = [];
    }
    const ungrouped = [];
    for (const a of assets) {
      if (a.vision_id && grouped[a.vision_id]) {
        grouped[a.vision_id].push(a);
      } else {
        ungrouped.push(a);
      }
    }
    return { grouped, ungrouped };
  }, [visions, assets]);

  const createReferenceFromUrl = async (visionId, url) => {
    await apiClient.post('/media/reference-urls', { vision_id: visionId, url });
    await loadWorkbench();
  };

  const assignAssetToVisionRole = async (assetId, visionId, role) => {
    await apiClient.patch(`/media/assets/${assetId}`, {
      vision_id: visionId,
      vision_role: role,
    });
    await loadWorkbench();
  };

  const assignAsset = async (assetId, visionId) => {
    await assignAssetToVisionRole(assetId, visionId, 'media');
  };

  const assignAssetToFolder = async (assetId, visionId) => {
    await apiClient.patch(`/media/assets/${assetId}`, { vision_id: visionId });
    await loadWorkbench();
  };

  const deleteAsset = async (assetId) => {
    await apiClient.delete(`/media/assets/${assetId}`);
    await loadWorkbench();
  };

  const createVision = async (title = 'New folder') => {
    await apiClient.post('/media/visions', { title });
    await loadWorkbench();
  };

  const renameVision = async (visionId, title) => {
    const trimmed = title.trim();
    if (!trimmed) return;
    await apiClient.patch(`/media/visions/${visionId}`, { title: trimmed });
    setVisions((prev) => prev.map((v) => (v.id === visionId ? { ...v, title: trimmed } : v)));
  };

  const deleteVision = async (visionId) => {
    await apiClient.delete(`/media/visions/${visionId}`);
    await loadWorkbench();
  };

  return {
    visions,
    assets,
    thumbs,
    error,
    setError,
    loadWorkbench,
    visionTitleById,
    assetsByVision,
    assignAsset,
    assignAssetToFolder,
    assignAssetToVisionRole,
    createReferenceFromUrl,
    deleteAsset,
    createVision,
    renameVision,
    deleteVision,
  };
}
