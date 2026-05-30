import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { useApiClient } from '../hooks/useApiClient';

function Dashboard() {
  const { user: auth0User, logout } = useAuth0();
  const { apiClient } = useApiClient();
  const [appUser, setAppUser] = useState(null);
  const [sessionError, setSessionError] = useState('');

  useEffect(() => {
    let isMounted = true;
    const loadSession = async () => {
      try {
        const response = await apiClient.get('/auth/session');
        if (isMounted) {
          setAppUser(response.data);
        }
      } catch (error) {
        if (isMounted) {
          setSessionError(error?.response?.data?.detail || 'Failed to load session profile.');
        }
      }
    };
    loadSession();
    return () => {
      isMounted = false;
    };
  }, [apiClient]);
  
  const handleLogout = () => {
    logout({
      logoutParams: {
        returnTo: window.location.origin,
      },
    });
  };

  return (
    <div className="retro-dashboard">
      <nav className="nav">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/accounts">Bank Accounts</Link>
        <Link to="/wallets">Crypto Wallets</Link>
        <Link to="/ledgers">Ledgers</Link>
        <Link to="/documents">Documents</Link>
        <Link to="/admin/media">Creative Media</Link>
        <div className="nav-user">
          <span>Welcome, {appUser?.name || auth0User?.name || auth0User?.email || 'User'}</span>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </nav>
      {sessionError ? <div className="error-message">{sessionError}</div> : null}
      
      <div className="tv-container">
        <div className="tv-console">
          <div className="tv-screen">
            <div className="screen-content">
              <h1 className="retro-title">C0ll3CT1V3 Business Management System</h1>
              <p className="retro-subtitle">Your Digital Command Center</p>
              <div className="screen-grid">
                <div className="screen-panel">
                  <h3>Bank Accounts</h3>
                  <p>Manage your business bank accounts and track balances.</p>
                  <Link to="/accounts" className="retro-btn">Manage Accounts</Link>
                </div>
                
                <div className="screen-panel">
                  <h3>Crypto Wallets</h3>
                  <p>Track your cryptocurrency holdings and wallets.</p>
                  <Link to="/wallets" className="retro-btn">Manage Wallets</Link>
                </div>
                
                <div className="screen-panel">
                  <h3>Ledgers</h3>
                  <p>Track assets and liabilities with detailed entries.</p>
                  <Link to="/ledgers" className="retro-btn">Manage Ledgers</Link>
                </div>
                
                <div className="screen-panel">
                  <h3>Documents</h3>
                  <p>Store and manage your business documents.</p>
                  <Link to="/documents" className="retro-btn">Manage Documents</Link>
                </div>

                <div className="screen-panel">
                  <h3>Creative Media</h3>
                  <p>Upload masters, tag assets, and publish to the Phillip James EPK.</p>
                  <Link to="/admin/media" className="retro-btn">Media Library</Link>
                </div>
              </div>
            </div>
          </div>
          <div className="vertical-grill"></div>
          <div className="spectra-logo">Collective</div>
          <div className="panel-row">
            <div className="panel"></div>
            <div className="panel"></div>
            <div className="panel"></div>
          </div>
          <div className="controls-section">
            <div className="slider-group"><span className="slider-label"></span><span className="slider"><span className="slider-knob"></span></span></div>
            <div className="slider-group"><span className="slider-label"></span><span className="slider"><span className="slider-knob"></span></span></div>
            <div className="slider-group"><span className="slider-label"></span><span className="slider"><span className="slider-knob"></span></span></div>
            <div className="slider-group"><span className="slider-label"></span><span className="slider"><span className="slider-knob"></span></span></div>
            <div className="slider-group"><span className="slider-label"></span><span className="slider"><span className="slider-knob"></span></span></div>
            <div className="slider-group"><span className="slider-label"></span><span className="slider"><span className="slider-knob"></span></span></div>
          </div>
        </div>
        <div className="tv-stand"></div>
      </div>
    </div>
  );
}

export default Dashboard;
