import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';

function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  const [loginError, setLoginError] = useState('');

  const startLogin = useCallback(
    async (returnTo = '/dashboard', screenHint) => {
      setLoginError('');
      try {
        await loginWithRedirect({
          appState: { returnTo },
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
      navigate('/dashboard');
    }
  }, [isLoading, isAuthenticated, navigate]);

  return (
    <div className="landing-page">
      <div className="landing-container">
        <div className="landing-header">
          <h1 className="landing-title">C0ll3CT1V3 Business Management System</h1>
          <p className="landing-subtitle">Your Digital Command Center</p>
        </div>

        <div className="auth-card">
          <div className="auth-form">
            <button type="button" className="auth-btn" onClick={() => startLogin('/dashboard')}>
              Login with Auth0
            </button>
            <button
              type="button"
              className="auth-btn"
              onClick={() => startLogin('/dashboard', 'signup')}
              style={{ marginTop: '1rem' }}
            >
              Create Account
            </button>
          </div>

          {loginError ? <div className="error-message">{loginError}</div> : null}

          <div className="auth-footer">
            <p>Welcome to your business management system</p>
            <div className="feature-highlights">
              <span>Bank Accounts</span>
              <span>Crypto Wallets</span>
              <span>Ledgers</span>
              <span>Documents</span>
            </div>
          </div>
        </div>

        <div className="demo-section">
          <p>Want to see the interface first?</p>
          <button type="button" className="demo-btn" onClick={() => startLogin('/dashboard')}>
            Enter Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}

export default Landing;
