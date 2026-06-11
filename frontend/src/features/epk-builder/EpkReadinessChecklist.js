import React, { useState } from 'react';

const CATEGORY_LABELS = {
  vibe: 'Your page',
  sound: 'Music',
  about: 'About',
  look: 'Look',
  connect: 'Connect',
  non_negotiable: 'Essentials',
  credibility: 'Credibility',
  practical: 'Practical',
};

const STATUS_ICON = {
  ready: '✓',
  partial: '◐',
  missing: '○',
};

function EpkReadinessChecklist({ completeness, onAskManager, busy }) {
  const [expandedId, setExpandedId] = useState(null);

  if (!completeness?.items?.length) {
    return null;
  }

  const essentialsPct = Math.round((completeness.required_score || 0) * 100);

  const grouped = completeness.items.reduce((acc, item) => {
    const key = item.category || 'practical';
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  return (
    <section className="epk-readiness">
      <header className="epk-readiness-header">
        <h3 className="epk-readiness-title">Profile readiness</h3>
        <span className="epk-readiness-score">{essentialsPct}% ready</span>
      </header>
      {completeness.summary ? (
        <p className="epk-readiness-summary">{completeness.summary}</p>
      ) : null}

      {Object.entries(grouped).map(([category, items]) => (
        <div key={category} className="epk-readiness-group">
          <h4 className="epk-readiness-group-title">{CATEGORY_LABELS[category] || category}</h4>
          <ul className="epk-readiness-list">
            {items.map((item) => {
              const open = expandedId === item.id;
              return (
                <li
                  key={item.id}
                  className={`epk-readiness-item epk-readiness-item--${item.status}`}
                >
                  <button
                    type="button"
                    className="epk-readiness-item-head"
                    onClick={() => setExpandedId(open ? null : item.id)}
                    disabled={busy}
                  >
                    <span className="epk-readiness-status" aria-hidden>
                      {STATUS_ICON[item.status] || '○'}
                    </span>
                    <span className="epk-readiness-label">{item.label}</span>
                  </button>
                  {open ? (
                    <div className="epk-readiness-detail">
                      <p>{item.detail}</p>
                      <p className="epk-readiness-suggestion">{item.suggestion}</p>
                      {onAskManager ? (
                        <button
                          type="button"
                          className="portal-btn portal-btn--ghost epk-readiness-ask"
                          disabled={busy}
                          onClick={() => onAskManager(item)}
                        >
                          Ask manager how to fix this
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </section>
  );
}

export default EpkReadinessChecklist;
