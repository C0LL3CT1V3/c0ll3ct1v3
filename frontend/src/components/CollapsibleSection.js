import React, { useState } from 'react';

function CollapsibleSection({
  title,
  defaultOpen = true,
  actions,
  children,
  className = '',
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={`portal-collapsible${open ? ' portal-collapsible--open' : ''} ${className}`.trim()}>
      <div className="portal-collapsible-header">
        <button
          type="button"
          className="portal-collapsible-toggle"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          <span className="portal-collapsible-title">{title}</span>
          <span className="portal-collapsible-chevron" aria-hidden>
            {open ? '▲' : '▼'}
          </span>
        </button>
        {actions ? <div className="portal-collapsible-actions">{actions}</div> : null}
      </div>
      {open ? <div className="portal-collapsible-body">{children}</div> : null}
    </section>
  );
}

export default CollapsibleSection;
