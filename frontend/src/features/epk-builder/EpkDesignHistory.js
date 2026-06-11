import React from 'react';

function formatWhen(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function labelFor(item) {
  if (item.is_seed) {
    const spec = item.spec_snapshot || item.user_prompt || 'Profile seed';
    return spec.length > 64 ? `${spec.slice(0, 64)}…` : spec;
  }
  const text = item.reasoning_summary || item.spec_snapshot || item.user_prompt || 'Iteration';
  return text.length > 64 ? `${text.slice(0, 64)}…` : text;
}

function EpkDesignHistory({
  iterations,
  selectedId,
  onSelect,
  onRestore,
  busy,
}) {
  if (!iterations?.length) {
    return (
      <aside className="epk-design-history epk-design-history--empty">
        <h3 className="epk-design-history-title">Design history</h3>
        <p className="epk-design-history-empty">
          Profile seeds and iterations appear here with screenshots. Add a seed above, then annotate and refine.
          Restore any layout if you wander off course.
        </p>
      </aside>
    );
  }

  return (
    <aside className="epk-design-history">
      <h3 className="epk-design-history-title">Design history</h3>
      <p className="epk-design-history-hint">
        Seeds are original layouts from vision + spec. Click a screenshot to preview; restore to jump back.
      </p>
      <ul className="epk-design-history-list">
        {iterations.map((item) => {
          const active = item.id === selectedId;
          const isSeed = Boolean(item.is_seed);
          return (
            <li
              key={item.id}
              className={`epk-design-history-item${active ? ' epk-design-history-item--active' : ''}${isSeed ? ' epk-design-history-item--seed' : ''}`}
            >
              <button
                type="button"
                className="epk-design-history-select"
                onClick={() => onSelect(item.id)}
                disabled={busy}
              >
                {item.screenshot_url ? (
                  <img src={item.screenshot_url} alt="" className="epk-design-history-thumb" />
                ) : (
                  <span className="epk-design-history-thumb epk-design-history-thumb--placeholder">
                    {isSeed ? 'Seed' : item.format === 'html_v1' ? 'HTML' : 'EPK'}
                  </span>
                )}
                <span className="epk-design-history-copy">
                  {isSeed ? <span className="epk-design-history-badge">Seed</span> : null}
                  <span className="epk-design-history-label">{labelFor(item)}</span>
                  <span className="epk-design-history-meta">
                    {formatWhen(item.created_at)}
                    {item.match_score != null ? ` · ${Math.round(item.match_score * 100)}%` : ''}
                    {item.artist_accepted ? ' · accepted' : ''}
                  </span>
                </span>
              </button>
              {active ? (
                <button
                  type="button"
                  className="portal-btn portal-btn--ghost epk-design-history-restore"
                  onClick={() => onRestore(item.id)}
                  disabled={busy}
                >
                  Restore this layout
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

export default EpkDesignHistory;
