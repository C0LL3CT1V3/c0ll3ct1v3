import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { epkPublicUrl } from '../hooks/useTenantSlug';

/** Profile Studio and Data are shelved until the next release. */
const SECTIONS = [
  { to: '/portal/vault', label: 'Vault' },
  { to: '/portal/epk', label: 'EPK' },
];

function PortalLayout({ profile, children }) {
  const { logout } = useAuth0();
  const tenantSlug = profile?.tenant_slug;
  const epkUrl = tenantSlug ? `${epkPublicUrl(tenantSlug)}/epk` : null;
  const epkPublished = profile?.epk_public_published;

  return (
    <div className="portal-layout">
      <header className="portal-header">
        <div className="portal-header-left">
          <span className="portal-logo">c0ll3ct1v3</span>
          <div className="portal-header-meta">
            <span className="portal-artist-name">{profile?.display_name || 'Artist portal'}</span>
            {tenantSlug ? (
              <span className="portal-tenant-slug">
                Page: <code>{tenantSlug}</code>
              </span>
            ) : null}
          </div>
        </div>
        <div className="portal-header-right">
          {epkUrl && epkPublished ? (
            <a href={epkUrl} target="_blank" rel="noreferrer" className="portal-link">
              View EPK
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
      <nav className="portal-studio-mode-tabs" aria-label="Portal sections">
        {SECTIONS.map((section) => (
          <NavLink
            key={section.to}
            to={section.to}
            className={({ isActive }) =>
              `portal-btn portal-btn--ghost${isActive ? ' portal-btn--active' : ''}`
            }
          >
            {section.label}
          </NavLink>
        ))}
      </nav>
      <main className="portal-main portal-main--studio">{children}</main>
    </div>
  );
}

export default PortalLayout;
