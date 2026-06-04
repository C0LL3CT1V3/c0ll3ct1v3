import React, { useState } from 'react';
import ManagerChat from './ManagerChat';

function CollapsibleManagerChat() {
  const [open, setOpen] = useState(false);

  return (
    <section className={`portal-manager-bar${open ? ' portal-manager-bar--open' : ''}`}>
      <button
        type="button"
        className="portal-manager-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="portal-manager-toggle-label">Manager</span>
        <span className="portal-manager-toggle-chevron" aria-hidden>
          {open ? '▲' : '▼'}
        </span>
      </button>
      {open ? (
        <div className="portal-manager-body">
          <ManagerChat layout="horizontal" />
        </div>
      ) : null}
    </section>
  );
}

export default CollapsibleManagerChat;
