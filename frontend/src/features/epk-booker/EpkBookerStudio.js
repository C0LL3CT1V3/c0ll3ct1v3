import React, { useState } from 'react';
import AssetListThumb from '../media/AssetListThumb';
import { getAssetDragId } from '../media/mediaDrag';
import VaultSidebarPanel from '../vault/VaultSidebarPanel';
import { usePortalWorkbench } from '../media/PortalWorkbenchProvider';
import EpkBookerReadiness from './EpkBookerReadiness';
import { useEpkBooker } from './useEpkBooker';

const MAX_PHOTOS = 6;
const MAX_AUDIO = 3;

const STREAMING_FIELDS = [
  { key: 'spotify', label: 'Spotify', placeholder: 'https://open.spotify.com/artist/...' },
  { key: 'soundcloud', label: 'SoundCloud', placeholder: 'https://soundcloud.com/...' },
  { key: 'bandcamp', label: 'Bandcamp', placeholder: 'https://bandcamp.com/...' },
  { key: 'youtube', label: 'YouTube', placeholder: 'https://youtube.com/@...' },
];

const SOCIAL_FIELDS = [
  { key: 'instagram', label: 'Instagram', placeholder: 'https://instagram.com/...' },
  { key: 'tiktok', label: 'TikTok', placeholder: 'https://tiktok.com/@...' },
  { key: 'twitter', label: 'X / Twitter', placeholder: 'https://x.com/...' },
];

function DropSlot({
  label,
  children,
  onDrop,
  onClear,
  className = '',
  acceptTypes,
  assets,
}) {
  const [over, setOver] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setOver(false);
    const assetId = getAssetDragId(e.dataTransfer);
    if (!assetId) return;
    const asset = assets.find((a) => a.id === assetId);
    if (!asset) return;
    if (acceptTypes && !acceptTypes.includes(asset.asset_type)) return;
    onDrop(assetId);
  };

  return (
    <div
      className={`epk-booker-slot${over ? ' epk-booker-slot--over' : ''} ${className}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={handleDrop}
    >
      <div className="epk-booker-slot-header">
        <span>{label}</span>
        {onClear ? (
          <button type="button" className="portal-btn portal-btn--ghost epk-booker-clear" onClick={onClear}>
            Remove
          </button>
        ) : null}
      </div>
      <div className="epk-booker-slot-body">{children}</div>
    </div>
  );
}

function EpkBookerStudio({ profile }) {
  const { workbench, setMediaError } = usePortalWorkbench();
  const booker = useEpkBooker(profile?.tenant_slug);
  const [heroUrl, setHeroUrl] = useState('');
  const [bio, setBio] = useState('');
  const [bookingEmail, setBookingEmail] = useState('');
  const [social, setSocial] = useState({});

  React.useEffect(() => {
    if (!booker.config) return;
    setHeroUrl(booker.config.hero_video?.url || '');
    setBio(booker.config.bio || '');
    setBookingEmail(booker.config.booking_email || profile?.epk_config?.booking_email || '');
    setSocial({
      ...(profile?.epk_config?.social || {}),
      ...(booker.config.social || {}),
    });
  }, [booker.config, profile]);

  const saveTextFields = async () => {
    const currentHero = booker.config?.hero_video || {};
    const hasAssetHero = currentHero.type === 'asset' && currentHero.asset_id;
    await booker.patch({
      bio,
      booking_email: bookingEmail,
      hero_video: {
        type: heroUrl.trim() ? 'youtube' : hasAssetHero ? 'asset' : currentHero.type || 'youtube',
        url: heroUrl.trim() ? heroUrl : hasAssetHero ? '' : currentHero.url || '',
        asset_id: hasAssetHero ? currentHero.asset_id : null,
      },
    });
  };

  const saveSocial = async (nextSocial) => {
    const cleaned = Object.fromEntries(
      Object.entries(nextSocial).filter(([, v]) => (v || '').trim()),
    );
    await booker.patch({ social: cleaned });
  };

  const updateSocialField = (key, value) => {
    setSocial((prev) => ({ ...prev, [key]: value }));
  };

  const handleSocialBlur = () => {
    saveSocial(social).catch(() => {});
  };

  const addPhoto = async (assetId) => {
    const photos = [...(booker.config?.photos || [])];
    if (photos.length >= MAX_PHOTOS) return;
    if (photos.some((p) => p.asset_id === assetId)) return;
    photos.push({ asset_id: assetId, caption: '' });
    await booker.patch({ photos });
  };

  const removePhoto = async (assetId) => {
    const photos = (booker.config?.photos || []).filter((p) => p.asset_id !== assetId);
    await booker.patch({ photos });
  };

  const addAudio = async (assetId) => {
    const audio_samples = [...(booker.config?.audio_samples || [])];
    if (audio_samples.length >= MAX_AUDIO) return;
    if (audio_samples.some((a) => a.asset_id === assetId)) return;
    const asset = workbench.assets.find((a) => a.id === assetId);
    audio_samples.push({ asset_id: assetId, title: asset?.title || '' });
    await booker.patch({ audio_samples });
  };

  const removeAudio = async (assetId) => {
    const audio_samples = (booker.config?.audio_samples || []).filter((a) => a.asset_id !== assetId);
    await booker.patch({ audio_samples });
  };

  const setHeroAsset = async (assetId) => {
    await booker.patch({
      hero_video: { type: 'asset', asset_id: assetId, url: '' },
    });
    setHeroUrl('');
  };

  const clearHero = async () => {
    await booker.patch({
      hero_video: { type: 'youtube', url: '', asset_id: null },
    });
    setHeroUrl('');
  };

  const setRider = async (assetId) => {
    await booker.patch({ tech_rider: { asset_id: assetId } });
  };

  const clearRider = async () => {
    await booker.patch({ tech_rider: { asset_id: null } });
  };

  if (booker.loading) {
    return <p className="portal-loading">Loading EPK…</p>;
  }

  const resolvedPhotos = booker.resolved?.photos || [];
  const resolvedAudio = booker.resolved?.audio_samples || [];
  const heroResolved = booker.resolved?.hero_video;

  return (
    <div className="epk-booker-studio">
      <EpkBookerReadiness completeness={booker.completeness} />
      {booker.error ? <div className="error-message">{booker.error}</div> : null}
      <div className="portal-studio-panels portal-studio-panels--epk">
        <VaultSidebarPanel
          assets={workbench.assets}
          thumbs={workbench.thumbs}
          onDeleteAsset={workbench.deleteAsset}
          onError={setMediaError}
          title="Vault"
          hint="Drag images, audio, or video into EPK slots."
        />
        <div className="epk-booker-main">
          <div className="epk-booker-actions">
            <button
              type="button"
              className="portal-btn portal-btn--ghost"
              disabled={booker.busy}
              onClick={() => booker.previewDraft()}
            >
              Preview EPK
            </button>
            <button
              type="button"
              className="portal-btn portal-btn--primary"
              disabled={booker.busy}
              onClick={() => booker.publish()}
            >
              Publish EPK
            </button>
            <button
              type="button"
              className="portal-btn portal-btn--ghost"
              disabled={booker.busy}
              onClick={() => booker.downloadPdf()}
            >
              Download PDF
            </button>
          </div>

          <DropSlot
            label="Hero video"
            onDrop={(id) => {
              const asset = workbench.assets.find((a) => a.id === id);
              if (asset?.asset_type === 'video' || asset?.asset_type === 'audio') {
                setHeroAsset(id);
              }
            }}
            onClear={heroResolved ? clearHero : null}
            assets={workbench.assets}
            acceptTypes={['video', 'audio']}
          >
            {heroResolved ? (
              <p className="epk-booker-filled">
                {heroResolved.title || heroResolved.type}
                {heroResolved.embed_url ? ` — ${heroResolved.embed_url}` : ''}
              </p>
            ) : (
              <>
                <p className="epk-booker-hint">Drop a video from Vault or paste YouTube URL:</p>
                <input
                  className="epk-booker-input"
                  value={heroUrl}
                  onChange={(e) => setHeroUrl(e.target.value)}
                  onBlur={saveTextFields}
                  placeholder="https://youtube.com/watch?v=..."
                />
              </>
            )}
          </DropSlot>

          <div className="epk-booker-photo-grid">
            {Array.from({ length: MAX_PHOTOS }).map((_, i) => {
              const slot = (booker.config?.photos || [])[i];
              const resolved = slot
                ? resolvedPhotos.find((p) => p.asset_id === slot.asset_id)
                : null;
              return (
                <DropSlot
                  key={i}
                  label={`Photo ${i + 1}`}
                  onDrop={addPhoto}
                  onClear={slot ? () => removePhoto(slot.asset_id) : null}
                  assets={workbench.assets}
                  acceptTypes={['image']}
                  className="epk-booker-slot--photo"
                >
                  {resolved?.url ? (
                    <img src={resolved.url} alt="" className="epk-booker-thumb" />
                  ) : (
                    <span className="epk-booker-empty">Drop image</span>
                  )}
                </DropSlot>
              );
            })}
          </div>

          <label className="epk-booker-field">
            <span>Bio</span>
            <textarea
              rows={5}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              onBlur={saveTextFields}
              placeholder="Booker-ready bio — sound, scene, notable shows…"
            />
          </label>

          <label className="epk-booker-field">
            <span>Booking email</span>
            <input
              type="email"
              value={bookingEmail}
              onChange={(e) => setBookingEmail(e.target.value)}
              onBlur={saveTextFields}
            />
          </label>

          <section className="epk-booker-links">
            <h3 className="epk-booker-links-title">Streaming</h3>
            <div className="epk-booker-links-grid">
              {STREAMING_FIELDS.map((field) => (
                <label key={field.key} className="epk-booker-field">
                  <span>{field.label}</span>
                  <input
                    type="url"
                    value={social[field.key] || ''}
                    onChange={(e) => updateSocialField(field.key, e.target.value)}
                    onBlur={handleSocialBlur}
                    placeholder={field.placeholder}
                  />
                </label>
              ))}
            </div>
            <h3 className="epk-booker-links-title">Social</h3>
            <div className="epk-booker-links-grid">
              {SOCIAL_FIELDS.map((field) => (
                <label key={field.key} className="epk-booker-field">
                  <span>{field.label}</span>
                  <input
                    type="url"
                    value={social[field.key] || ''}
                    onChange={(e) => updateSocialField(field.key, e.target.value)}
                    onBlur={handleSocialBlur}
                    placeholder={field.placeholder}
                  />
                </label>
              ))}
            </div>
          </section>

          <div className="epk-booker-audio-row">
            {Array.from({ length: MAX_AUDIO }).map((_, i) => {
              const slot = (booker.config?.audio_samples || [])[i];
              const resolved = slot
                ? resolvedAudio.find((a) => a.asset_id === slot.asset_id)
                : null;
              const asset = slot
                ? workbench.assets.find((a) => a.id === slot.asset_id)
                : null;
              return (
                <DropSlot
                  key={i}
                  label={`Track ${i + 1}`}
                  onDrop={addAudio}
                  onClear={slot ? () => removeAudio(slot.asset_id) : null}
                  assets={workbench.assets}
                  acceptTypes={['audio']}
                >
                  {resolved ? (
                    <div className="epk-booker-audio-slot">
                      <AssetListThumb asset={asset || { asset_type: 'audio' }} thumbUrl={null} />
                      <span>{resolved.title || 'Track'}</span>
                    </div>
                  ) : (
                    <span className="epk-booker-empty">Drop audio</span>
                  )}
                </DropSlot>
              );
            })}
          </div>

          <DropSlot
            label="Tech rider (optional)"
            onDrop={setRider}
            onClear={booker.config?.tech_rider?.asset_id ? clearRider : null}
            assets={workbench.assets}
          >
            {booker.resolved?.tech_rider ? (
              <span>{booker.resolved.tech_rider.title || 'Rider attached'}</span>
            ) : (
              <span className="epk-booker-empty">Drop PDF or doc from Vault</span>
            )}
          </DropSlot>
        </div>
      </div>
    </div>
  );
}

export default EpkBookerStudio;
