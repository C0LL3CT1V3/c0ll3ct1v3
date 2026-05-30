import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { epkPublicUrl } from '../hooks/useTenantSlug';

function PortalLayout({ profile, children }) {
  const { logout } = useAuth0();
  const tenantSlug = profile?.tenant_slug;
  const epkUrl = tenantSlug ? epkPublicUrl(tenantSlug) : null;

  return (
    <div className="portal-layout">
      <header className="portal-header">
        <div className="portal-header-left">
          <span className="portal-logo">c0ll3ct1v3</span>
          <div className="portal-header-meta">
            <span className="portal-artist-name">{profile?.display_name || 'Artist portal'}</span>
            {tenantSlug ? (
              <span className="portal-tenant-slug">
                EPK: <code>{tenantSlug}</code>
              </span>
            ) : null}
          </div>
        </div>
        <div className="portal-header-right">
          {epkUrl ? (
            <a href={epkUrl} target="_blank" rel="noreferrer" className="portal-link">
              View your EPK
            </a>
          ) : null}
          <button
            type="button"
            className="portal-btn portal-btn--ghost"
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
          >
            Logout
          </button>
        </div>
      </header>
      <main className="portal-main">{children}</main>
    </div>
  );
}

export default PortalLayout;
