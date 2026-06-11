import React from 'react';

function statusClass(status) {
  if (status === 'ready') return 'epk-readiness-item--ready';
  if (status === 'partial') return 'epk-readiness-item--partial';
  return 'epk-readiness-item--missing';
}

function EpkBookerReadiness({ completeness }) {
  if (!completeness?.items?.length) return null;

  return (
    <section className="epk-readiness epk-readiness--booker">
      <header className="epk-readiness-header">
        <h3>Booker readiness</h3>
        <span className="epk-readiness-score">
          {Math.round((completeness.required_score || 0) * 100)}% essentials
        </span>
      </header>
      <p className="epk-readiness-summary">{completeness.summary}</p>
      <ul className="epk-readiness-list">
        {completeness.items.map((item) => (
          <li key={item.id} className={`epk-readiness-item ${statusClass(item.status)}`}>
            <span className="epk-readiness-label">{item.label}</span>
            <span className="epk-readiness-detail">{item.detail}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default EpkBookerReadiness;
