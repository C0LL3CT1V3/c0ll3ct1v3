import React, { useCallback, useEffect, useState } from 'react';

function MediaInboxList({ apiClient, authReady = true, refreshKey, onSelect, selectedId }) {
  const [assets, setAssets] = useState([]);
  const [error, setError] = useState('');
  const [thumbs, setThumbs] = useState({});

  const loadAssets = useCallback(async () => {
    try {
      const res = await apiClient.get('/media/assets');
      setAssets(res.data);
      setError('');
    } catch (err) {
      if (err?.response?.status === 401) {
        setError('Not signed in or session expired. Log out and sign in again.');
      } else {
        setError(err?.response?.data?.detail || 'Failed to load media.');
      }
    }
  }, [apiClient]);

  useEffect(() => {
    if (!authReady) return;
    loadAssets();
  }, [loadAssets, refreshKey, authReady]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = {};
      for (const a of assets) {
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

  const publish = async (id, e) => {
    e.stopPropagation();
    const asset = assets.find((x) => x.id === id);
    if (asset && asset.status === 'processing') {
      setError('Wait until processing finishes before publishing.');
      return;
    }
    if (asset && asset.status === 'inbox') {
      setError('Upload is still completing. Refresh in a moment.');
      return;
    }
    try {
      await apiClient.post(`/media/assets/${id}/publish`);
      await loadAssets();
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Publish failed.');
    }
  };

  const canPublish = (status) => status === 'ready' || status === 'published';

  return (
    <div className="media-inbox">
      <h3>Library</h3>
      <p className="media-inbox-hint">Publish moves media to your public EPK.</p>
      {error ? <div className="error-message">{error}</div> : null}
      {assets.length === 0 ? (
        <p className="media-inbox-empty">No uploads yet.</p>
      ) : (
        <ul className="media-asset-list">
          {assets.map((a) => (
            <li key={a.id} className="media-asset-row">
              {thumbs[a.id] ? (
                <img src={thumbs[a.id]} alt="" className="media-thumb" />
              ) : (
                <span className="media-thumb media-thumb--placeholder">{a.asset_type[0]}</span>
              )}
              <button
                type="button"
                className={
                  selectedId === a.id ? 'media-asset-item media-asset-item--active' : 'media-asset-item'
                }
                onClick={() => onSelect?.(a.id)}
              >
                <span className="media-asset-title">{a.title || a.id}</span>
                <span className="media-type">{a.asset_type}</span>
                <span className={`media-status media-status--${a.status}`}>{a.status}</span>
              </button>
              {canPublish(a.status) && a.status !== 'published' ? (
                <button type="button" className="portal-btn portal-btn--small" onClick={(e) => publish(a.id, e)}>
                  Publish
                </button>
              ) : null}
              {a.status === 'processing' ? (
                <span className="media-status-hint">Processing…</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default MediaInboxList;
