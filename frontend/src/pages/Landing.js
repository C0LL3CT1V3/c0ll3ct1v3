import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';

function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isLoading, isAuthenticated, navigate]);

  return (
    <div className="landing-page">
      <div className="landing-container">
        {/* Header */}
        <div className="landing-header">
          <h1 className="landing-title">C0ll3CT1V3 Business Management System</h1>
          <p className="landing-subtitle">Your Digital Command Center</p>
        </div>

        {/* Auth Card */}
        <div className="auth-card">
          <div className="auth-form">
            <button
              type="button"
              className="auth-btn"
              onClick={() => loginWithRedirect()}
            >
              Login with Auth0
            </button>
            <button
              type="button"
              className="auth-btn"
              onClick={() => loginWithRedirect({ authorizationParams: { screen_hint: 'signup' } })}
              style={{ marginTop: '1rem' }}
            >
              Create Account
            </button>
          </div>

          <div className="auth-footer">
            <p>Welcome to your business management system</p>
            <div className="feature-highlights">
              <span>🏦 Bank Accounts</span>
              <span>₿ Crypto Wallets</span>
              <span>📊 Ledgers</span>
              <span>📄 Documents</span>
            </div>
          </div>
        </div>

        {/* Demo Link */}
        <div className="demo-section">
          <p>Want to see the interface first?</p>
          <button
            type="button"
            className="demo-btn"
            onClick={() =>
              loginWithRedirect({
                authorizationParams: {
                  redirect_uri: `${window.location.origin}/dashboard`,
                },
              })
            }
          >
            Enter Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}

export default Landing;
