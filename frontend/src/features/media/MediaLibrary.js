import React, { useCallback, useEffect, useState } from 'react';

const TABS = [
  { id: 'workbench', label: 'Workbench', params: { region: 'workbench' } },
  { id: 'gallery', label: 'Gallery', params: { region: 'gallery' } },
];

function MediaLibrary({ apiClient, authReady = true, refreshKey, onSelect, selectedId }) {
  const [tab, setTab] = useState('workbench');
  const [assets, setAssets] = useState([]);
  const [error, setError] = useState('');
  const [thumbs, setThumbs] = useState({});

  const activeTab = TABS.find((t) => t.id === tab) || TABS[0];

  const loadAssets = useCallback(async () => {
    try {
      const res = await apiClient.get('/media/assets', { params: activeTab.params });
      setAssets(res.data);
      setError('');
    } catch (err) {
      if (err?.response?.status === 401) {
        setError('Not signed in or session expired. Log out and sign in again.');
      } else {
        setError(err?.response?.data?.detail || 'Failed to load media.');
      }
    }
  }, [apiClient, activeTab.params]);

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

  const promote = async (id, e) => {
    e.stopPropagation();
    const asset = assets.find((x) => x.id === id);
    if (asset?.status === 'processing') {
      setError('Wait until processing finishes before promoting.');
      return;
    }
    if (asset?.status === 'inbox') {
      setError('Upload is still completing. Refresh in a moment.');
      return;
    }
    try {
      await apiClient.post(`/media/assets/${id}/promote`, {});
      await loadAssets();
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Promote failed.');
    }
  };

  const canPromoteWorkbench = (a) => tab === 'workbench' && a.status === 'ready';

  return (
    <div className="media-inbox">
      <div className="media-library-tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? 'media-tab media-tab--active' : 'media-tab'}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <p className="media-inbox-hint">
        {tab === 'workbench'
          ? 'Upload masters here. Promote copies to Gallery without changing the original.'
          : 'Delivery copies live here (immutable revisions).'}
      </p>
      {error ? <div className="error-message">{error}</div> : null}
      {assets.length === 0 ? (
        <p className="media-inbox-empty">No items in {activeTab.label}.</p>
      ) : (
        <ul className="media-asset-list">
          {assets.map((a) => (
            <li key={a.id} className="media-asset-row">
              {thumbs[a.id] ? (
                <img src={thumbs[a.id]} alt="" className="media-thumb" />
              ) : (
                <span className="media-thumb media-thumb--placeholder" aria-hidden>
                  ·
                </span>
              )}
              <button
                type="button"
                className={
                  selectedId === a.id ? 'media-asset-item media-asset-item--active' : 'media-asset-item'
                }
                onClick={() => onSelect?.(a.id)}
              >
                <span className="media-asset-title">{a.title || a.id}</span>
              </button>
              {canPromoteWorkbench(a) ? (
                <button
                  type="button"
                  className="portal-btn portal-btn--small"
                  onClick={(e) => promote(a.id, e)}
                >
                  Promote
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

export default MediaLibrary;
