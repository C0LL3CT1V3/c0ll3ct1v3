import React from 'react';

function MarketingLayout({ children }) {
  return (
    <div className="marketing-layout">
      <header className="marketing-header">
        <span className="marketing-logo">c0ll3ct1v3</span>
      </header>
      <main className="marketing-main">{children}</main>
      <footer className="marketing-footer">
        <small>Independent artists, owned stack.</small>
      </footer>
    </div>
  );
}

export default MarketingLayout;
