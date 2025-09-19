import React from 'react';
import { Link } from 'react-router-dom';
import { authService } from '../services/authService';

function Dashboard() {
  const user = authService.getStoredUser();
  
  const handleLogout = () => {
    authService.logout();
  };

  return (
    <div className="retro-dashboard">
      <nav className="nav">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/accounts">Bank Accounts</Link>
        <Link to="/wallets">Crypto Wallets</Link>
        <Link to="/ledgers">Ledgers</Link>
        <Link to="/documents">Documents</Link>
        <div className="nav-user">
          <span>Welcome, {user?.name}</span>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </nav>
      
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
