import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { useApiClient } from '../hooks/useApiClient';
import { useArtistProfile } from '../hooks/useArtistProfile';
import MediaDropzone from '../features/media/MediaDropzone';
function AdminMedia() {
  const { logout } = useAuth0();
  const { apiClient, authReady } = useApiClient();
  const { profile } = useArtistProfile();
  const [assets, setAssets] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [editTags, setEditTags] = useState('{}');
  const [refreshKey, setRefreshKey] = useState(0);

  const tenantSlug =
    profile?.tenant_slug ||
    (process.env.REACT_APP_DEFAULT_TENANT || 'phillipjames').trim();

  const loadAssets = useCallback(async () => {
    try {
      const res = await apiClient.get('/media/assets');
      setAssets(res.data);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load media library.');
    }
  }, [apiClient]);

  useEffect(() => {
    if (!authReady) return;
    loadAssets();
  }, [loadAssets, refreshKey, authReady]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await apiClient.get(`/media/assets/${selectedId}`);
        if (!cancelled) {
          setSelected(res.data);
          setEditTitle(res.data.title || '');
          setEditTags(JSON.stringify(res.data.tags || {}, null, 2));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.detail || 'Failed to load asset.');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId, apiClient]);

  const saveMetadata = async () => {
    if (!selectedId) return;
    let tags;
    try {
      tags = JSON.parse(editTags);
    } catch {
      setError('Tags must be valid JSON.');
      return;
    }
    try {
      await apiClient.patch(`/media/assets/${selectedId}`, {
        title: editTitle,
        tags,
      });
      await loadAssets();
      const res = await apiClient.get(`/media/assets/${selectedId}`);
      setSelected(res.data);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Save failed.');
    }
  };

  const publishAsset = async () => {
    if (!selectedId) return;
    try {
      await apiClient.post(`/media/assets/${selectedId}/publish`);
      await loadAssets();
      const res = await apiClient.get(`/media/assets/${selectedId}`);
      setSelected(res.data);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Publish failed.');
    }
  };

  const deleteAsset = async () => {
    if (!selectedId || !window.confirm('Remove this asset from the library?')) return;
    try {
      await apiClient.delete(`/media/assets/${selectedId}`);
      setSelectedId(null);
      await loadAssets();
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Delete failed.');
    }
  };

  return (
    <div className="container admin-media">
      <nav className="nav">
        <Link to="/portal">Portal</Link>
        <div className="nav-user">
          <button
            type="button"
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
            className="logout-btn"
          >
            Logout
          </button>
        </div>
      </nav>

      <h1>Creative Media (legacy route)</h1>
      <p className="admin-media-subtitle">Prefer the artist portal at /portal.</p>

      {error ? <div className="error-message">{String(error)}</div> : null}

      <div className="admin-media-grid">
        <section className="admin-media-upload">
          <MediaDropzone
            apiClient={apiClient}
            tenantSlug={tenantSlug}
            onUploaded={() => setRefreshKey((k) => k + 1)}
            onError={setError}
          />
        </section>

        <section className="admin-media-list">
          <h2>Library</h2>
          {assets.length === 0 ? (
            <p>No assets yet.</p>
          ) : (
            <ul className="media-asset-list">
              {assets.map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    className={
                      selectedId === a.id ? 'media-asset-item media-asset-item--active' : 'media-asset-item'
                    }
                    onClick={() => setSelectedId(a.id)}
                  >
                    <span className="media-asset-title">{a.title || a.id}</span>
                    <span className={`media-status media-status--${a.status}`}>{a.status}</span>
                    <span className="media-type">{a.asset_type}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="admin-media-detail">
          <h2>Details</h2>
          {!selected ? (
            <p>Select an asset to edit metadata or publish.</p>
          ) : (
            <>
              <p>
                <strong>Status:</strong> {selected.status} · <strong>Type:</strong>{' '}
                {selected.asset_type}
              </p>
              <label htmlFor="edit-title">Title</label>
              <input
                id="edit-title"
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
              />
              <label htmlFor="edit-tags">Tags (JSON)</label>
              <textarea
                id="edit-tags"
                rows={6}
                value={editTags}
                onChange={(e) => setEditTags(e.target.value)}
              />
              <div className="admin-media-actions">
                <button type="button" className="retro-btn" onClick={saveMetadata}>
                  Save
                </button>
                <button type="button" className="retro-btn" onClick={publishAsset}>
                  Publish to EPK
                </button>
                <button type="button" className="retro-btn retro-btn--danger" onClick={deleteAsset}>
                  Delete
                </button>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

export default AdminMedia;
