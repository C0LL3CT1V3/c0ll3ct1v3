import React from 'react';
import { Link } from 'react-router-dom';

function Wallets() {
  return (
    <div className="container">
      <nav className="nav">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/accounts">Bank Accounts</Link>
        <Link to="/wallets">Crypto Wallets</Link>
        <Link to="/ledgers">Ledgers</Link>
        <Link to="/documents">Documents</Link>
      </nav>

      <h1>Crypto Wallets</h1>
      <p>Crypto wallet management coming soon...</p>
    </div>
  );
}

export default Wallets;
