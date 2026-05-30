import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import MarketingLayout from '../../layouts/MarketingLayout';

function MarketingLanding() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  const [loginError, setLoginError] = useState('');

  const startLogin = useCallback(
    async (screenHint) => {
      setLoginError('');
      try {
        await loginWithRedirect({
          appState: { returnTo: '/portal' },
          authorizationParams: {
            redirect_uri: window.location.origin,
            ...(screenHint ? { screen_hint: screenHint } : {}),
          },
        });
      } catch (error) {
        console.error('Auth0 login failed:', error);
        setLoginError(error?.message || 'Login failed. Check Auth0 settings and try again.');
      }
    },
    [loginWithRedirect],
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const error = params.get('error');
    const description = params.get('error_description');
    if (error) {
      setLoginError(
        description
          ? decodeURIComponent(description.replace(/\+/g, ' '))
          : `Auth0 error: ${error}`,
      );
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/portal');
    }
  }, [isLoading, isAuthenticated, navigate]);

  return (
    <MarketingLayout>
      <section className="marketing-hero">
        <h1>Your music career, one stack you own.</h1>
        <p className="marketing-lead">
          c0ll3ct1v3 gives independent artists a minimal studio: AI manager, media library, and a
          public EPK at your own subdomain.
        </p>
        <div className="marketing-actions">
          <button type="button" className="portal-btn portal-btn--primary" onClick={() => startLogin()}>
            Artist login
          </button>
          <button
            type="button"
            className="portal-btn portal-btn--ghost"
            onClick={() => startLogin('signup')}
          >
            Create account
          </button>
        </div>
        {loginError ? <div className="error-message">{loginError}</div> : null}
      </section>
    </MarketingLayout>
  );
}

export default MarketingLanding;
