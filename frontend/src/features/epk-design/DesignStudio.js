import React, { useCallback, useEffect, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';
import { useArtistProfile } from '../../hooks/useArtistProfile';
import { epkPublicUrl } from '../../hooks/useTenantSlug';
import EpkRenderer from '../epk/EpkRenderer';
import MediaDropzone from '../media/MediaDropzone';
import MediaInboxList from '../media/MediaInboxList';

function DesignStudio() {
  const { apiClient, authReady } = useApiClient();
  const { profile, updateProfile } = useArtistProfile();
  const [displayName, setDisplayName] = useState('');
  const [brief, setBrief] = useState('');
  const [preview, setPreview] = useState(null);
  const [designMeta, setDesignMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mediaRefresh, setMediaRefresh] = useState(0);
  const [templateId, setTemplateId] = useState('editorial');
  const [polishCopy, setPolishCopy] = useState(false);
  const [wireframeId, setWireframeId] = useState('');
  const [styleId, setStyleId] = useState('');
  const [audioId, setAudioId] = useState('');

  const tenantSlug = profile?.tenant_slug;
  const epkUrl = tenantSlug ? epkPublicUrl(tenantSlug) : null;

  const loadPreview = useCallback(async () => {
    try {
      const res = await apiClient.get('/epk/design/preview');
      setPreview(res.data);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load preview.');
    }
  }, [apiClient]);

  const loadMeta = useCallback(async () => {
    try {
      const res = await apiClient.get('/epk/design/draft');
      setDesignMeta(res.data);
    } catch {
      /* ignore */
    }
  }, [apiClient]);

  useEffect(() => {
    if (!authReady) return;
    loadPreview();
    loadMeta();
  }, [loadPreview, loadMeta, authReady]);

  useEffect(() => {
    if (profile?.display_name) {
      setDisplayName(profile.display_name);
    }
  }, [profile?.display_name]);

  const initDefault = async () => {
    setLoading(true);
    setError('');
    try {
      await apiClient.post('/epk/design/init-default');
      await loadPreview();
      await loadMeta();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not create default design.');
    } finally {
      setLoading(false);
    }
  };

  const generatePreview = async () => {
    setLoading(true);
    setError('');
    try {
      await apiClient.post('/epk/design/generate', {
        brief,
        template_id: templateId,
        wireframe_asset_id: wireframeId || null,
        style_asset_id: styleId || null,
        audio_asset_id: audioId || null,
        polish_copy: polishCopy,
      });
      await loadPreview();
      await loadMeta();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Generate failed.');
    } finally {
      setLoading(false);
    }
  };

  const publishDesign = async () => {
    setLoading(true);
    setError('');
    try {
      await apiClient.post('/epk/design/publish');
      await loadMeta();
      setError('');
      alert('Design published to your live EPK. Ensure media items are also published.');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Publish design failed.');
    } finally {
      setLoading(false);
    }
  };

  const siteForRenderer = preview
    ? {
        display_name: preview.display_name,
        tagline: preview.tagline,
        bio: preview.bio,
        booking_email: preview.booking_email,
        social: preview.social,
        sections: preview.sections,
      }
    : null;

  const designForRenderer = preview?.design
    ? { ...preview.design, template_id: templateId || preview.design.template_id }
    : null;

  return (
    <div className="design-studio">
      <div className="design-studio-inputs">
        <h2>Design studio</h2>
        <p className="portal-panel-hint">
          Describe your artist corner, optionally upload wireframe and style reference as images in Media,
          then generate a preview. Publish design + publish each media file for the live EPK.
        </p>
        {error ? <div className="error-message">{error}</div> : null}
        {designMeta?.design_published_at ? (
          <p className="design-published-badge">
            Live design published: {new Date(designMeta.design_published_at).toLocaleString()}
          </p>
        ) : null}

        <label htmlFor="artist-display-name">Artist name (EPK headline)</label>
        <input
          id="artist-display-name"
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          onBlur={async () => {
            if (!displayName.trim() || displayName === profile?.display_name) return;
            try {
              await updateProfile({ display_name: displayName.trim() });
              await loadPreview();
            } catch (err) {
              setError(err?.response?.data?.detail || 'Could not save artist name.');
            }
          }}
        />

        <label htmlFor="design-brief">Brief</label>
        <textarea
          id="design-brief"
          rows={5}
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          placeholder="Vibe, section order, headline ideas…"
        />

        <label htmlFor="design-template">Template</label>
        <select id="design-template" value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
          <option value="editorial">Editorial</option>
          <option value="gallery">Gallery</option>
          <option value="minimal">Minimal</option>
        </select>

        <label htmlFor="wireframe-id">Wireframe asset ID (from Media library)</label>
        <input
          id="wireframe-id"
          type="text"
          value={wireframeId}
          onChange={(e) => setWireframeId(e.target.value)}
          placeholder="uuid of uploaded sketch"
        />
        <label htmlFor="style-id">Style reference asset ID</label>
        <input
          id="style-id"
          type="text"
          value={styleId}
          onChange={(e) => setStyleId(e.target.value)}
          placeholder="uuid of style image"
        />
        <label htmlFor="audio-id">Audio brief asset ID</label>
        <input
          id="audio-id"
          type="text"
          value={audioId}
          onChange={(e) => setAudioId(e.target.value)}
          placeholder="uuid of audio file (Whisper)"
        />

        <label className="design-checkbox">
          <input type="checkbox" checked={polishCopy} onChange={(e) => setPolishCopy(e.target.checked)} />
          Polish copy (extra LLM pass)
        </label>

        <div className="design-studio-actions">
          <button type="button" className="portal-btn portal-btn--ghost" onClick={initDefault} disabled={loading}>
            Use template only
          </button>
          <button type="button" className="portal-btn portal-btn--primary" onClick={generatePreview} disabled={loading}>
            {loading ? 'Working…' : 'Generate preview'}
          </button>
          <button type="button" className="portal-btn portal-btn--primary" onClick={publishDesign} disabled={loading}>
            Publish design to EPK
          </button>
        </div>

        {epkUrl ? (
          <a href={epkUrl} target="_blank" rel="noreferrer" className="portal-link">
            Open live EPK
          </a>
        ) : null}

        <section className="design-ref-uploads">
          <h3>Reference uploads</h3>
          <p className="portal-panel-hint">Tag wireframe/style in filename or use for LLM context after upload.</p>
          <MediaDropzone
            apiClient={apiClient}
            tenantSlug={tenantSlug}
            onUploaded={() => {
              setMediaRefresh((k) => k + 1);
              loadPreview();
            }}
            onError={setError}
          />
          <MediaInboxList
            apiClient={apiClient}
            authReady={authReady}
            refreshKey={mediaRefresh}
            onSelect={(id) => {
              setWireframeId(id);
            }}
          />
          <p className="portal-panel-hint">
            Click a library item to copy its ID into the wireframe field. Publish each file before it appears on the
            live EPK; preview shows ready and published media.
          </p>
        </section>
      </div>

      <div className="design-studio-preview">
        <h3>Preview</h3>
        <div className="design-preview-frame">
          {siteForRenderer && designForRenderer ? (
            <EpkRenderer
              site={siteForRenderer}
              design={designForRenderer}
              tracks={preview.tracks || []}
              photos={preview.photos || []}
            />
          ) : (
            <p className="portal-panel-hint">Click “Use template only” or “Generate preview”.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default DesignStudio;
