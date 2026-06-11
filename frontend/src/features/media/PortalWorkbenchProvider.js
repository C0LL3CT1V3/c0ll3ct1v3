import React, { createContext, useContext, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';
import { useWorkbench } from './useWorkbench';

const PortalWorkbenchContext = createContext(null);

export function PortalWorkbenchProvider({ children }) {
  const { apiClient, authReady } = useApiClient();
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedId, setSelectedId] = useState(
    () => sessionStorage.getItem('portal_selected_asset_id') || null,
  );
  const [mediaError, setMediaError] = useState('');

  const workbench = useWorkbench(apiClient, authReady, refreshKey);

  const handleSelect = (id) => {
    setSelectedId(id);
    if (id) sessionStorage.setItem('portal_selected_asset_id', id);
    else sessionStorage.removeItem('portal_selected_asset_id');
  };

  const bumpRefresh = () => setRefreshKey((k) => k + 1);

  const value = {
    apiClient,
    authReady,
    refreshKey,
    bumpRefresh,
    selectedId,
    setSelectedId: handleSelect,
    mediaError,
    setMediaError,
    workbench,
  };

  return (
    <PortalWorkbenchContext.Provider value={value}>
      {children}
    </PortalWorkbenchContext.Provider>
  );
}

export function usePortalWorkbench() {
  const ctx = useContext(PortalWorkbenchContext);
  if (!ctx) {
    throw new Error('usePortalWorkbench must be used within PortalWorkbenchProvider');
  }
  return ctx;
}

export default PortalWorkbenchProvider;
