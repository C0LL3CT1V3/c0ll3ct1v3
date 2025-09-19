import React from 'react';
import { Link } from 'react-router-dom';

function Documents() {
  return (
    <div className="container">
      <nav className="nav">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/accounts">Bank Accounts</Link>
        <Link to="/wallets">Crypto Wallets</Link>
        <Link to="/ledgers">Ledgers</Link>
        <Link to="/documents">Documents</Link>
      </nav>

      <h1>Documents</h1>
      <p>Business document management coming soon...</p>
    </div>
  );
}

export default Documents;
