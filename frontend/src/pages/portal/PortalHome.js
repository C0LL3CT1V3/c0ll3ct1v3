import React, { useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';
import ManagerChat from '../../features/manager/ManagerChat';
import MediaDropzone from '../../features/media/MediaDropzone';
import MediaInboxList from '../../features/media/MediaInboxList';

function PortalHome({ profile }) {
  const { apiClient, authReady } = useApiClient();
  const [mediaError, setMediaError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedId, setSelectedId] = useState(null);

  const tenantSlug = profile?.tenant_slug;

  return (
    <>
      <div className="portal-grid">
        <section className="portal-panel portal-panel--chat">
          <ManagerChat />
        </section>
        <section className="portal-panel portal-panel--media">
          <h2 className="portal-panel-title">Media</h2>
          <p className="portal-panel-hint">
            {tenantSlug
              ? `Upload and publish appear on your public EPK at ${tenantSlug}.`
              : 'Loading your artist workspace…'}
          </p>
          {mediaError ? <div className="error-message">{mediaError}</div> : null}
          <MediaDropzone
            apiClient={apiClient}
            tenantSlug={tenantSlug}
            onUploaded={() => setRefreshKey((k) => k + 1)}
            onError={setMediaError}
          />
          <MediaInboxList
            apiClient={apiClient}
            authReady={authReady}
            refreshKey={refreshKey}
            selectedId={selectedId}
            onSelect={(id) => {
              setSelectedId(id);
              if (id) sessionStorage.setItem('portal_selected_asset_id', id);
            }}
          />
        </section>
      </div>
    </>
  );
}

export default PortalHome;
