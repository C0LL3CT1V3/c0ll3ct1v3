import React, { useCallback, useRef, useState } from 'react';

function normalizeRect(container, rect) {
  const w = container.clientWidth || 1;
  const h = container.clientHeight || 1;
  return {
    x: rect.x / w,
    y: rect.y / h,
    w: rect.w / w,
    h: rect.h / h,
  };
}

function componentsInRect(container, rect) {
  const ids = new Set();
  const els = container.querySelectorAll('[data-epk-id]');
  els.forEach((el) => {
    const r = el.getBoundingClientRect();
    const cr = container.getBoundingClientRect();
    const ex = r.left - cr.left;
    const ey = r.top - cr.top;
    const overlap =
      ex < rect.x + rect.w && ex + r.width > rect.x && ey < rect.y + rect.h && ey + r.height > rect.y;
    if (overlap) ids.add(el.getAttribute('data-epk-id'));
  });
  return [...ids];
}

function EpkAnnotationLayer({ containerRef, enabled, onSubmit, onCancel }) {
  const [drawing, setDrawing] = useState(false);
  const [start, setStart] = useState(null);
  const [current, setCurrent] = useState(null);
  const [annotations, setAnnotations] = useState([]);
  const [note, setNote] = useState('');
  const pendingRect = useRef(null);

  const onPointerDown = (e) => {
    if (!enabled || !containerRef?.current) return;
    const cr = containerRef.current.getBoundingClientRect();
    const x = e.clientX - cr.left;
    const y = e.clientY - cr.top;
    setDrawing(true);
    setStart({ x, y });
    setCurrent({ x, y });
  };

  const onPointerMove = (e) => {
    if (!drawing || !containerRef?.current) return;
    const cr = containerRef.current.getBoundingClientRect();
    setCurrent({ x: e.clientX - cr.left, y: e.clientY - cr.top });
  };

  const onPointerUp = () => {
    if (!drawing || !start || !current || !containerRef?.current) return;
    setDrawing(false);
    const x = Math.min(start.x, current.x);
    const y = Math.min(start.y, current.y);
    const w = Math.abs(current.x - start.x);
    const h = Math.abs(current.y - start.y);
    if (w < 8 && h < 8) return;
    pendingRect.current = { x, y, w, h };
  };

  const addAnnotation = () => {
    if (!pendingRect.current || !note.trim() || !containerRef?.current) return;
    const rect = pendingRect.current;
    const componentIds = componentsInRect(containerRef.current, rect);
    setAnnotations((prev) => [
      ...prev,
      {
        note: note.trim(),
        bbox_norm: normalizeRect(containerRef.current, rect),
        component_ids: componentIds,
      },
    ]);
    setNote('');
    pendingRect.current = null;
    setStart(null);
    setCurrent(null);
  };

  const handleSubmit = () => {
    if (annotations.length) onSubmit?.(annotations);
  };

  const overlayRect =
    drawing && start && current
      ? {
          left: Math.min(start.x, current.x),
          top: Math.min(start.y, current.y),
          width: Math.abs(current.x - start.x),
          height: Math.abs(current.y - start.y),
        }
      : pendingRect.current
        ? {
            left: pendingRect.current.x,
            top: pendingRect.current.y,
            width: pendingRect.current.w,
            height: pendingRect.current.h,
          }
        : null;

  if (!enabled) return null;

  return (
    <div className="epk-annotate-panel">
      <div
        className="epk-annotate-overlay"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        {overlayRect ? (
          <div
            className="epk-annotate-rect"
            style={{
              left: overlayRect.left,
              top: overlayRect.top,
              width: overlayRect.width,
              height: overlayRect.height,
            }}
          />
        ) : null}
        {annotations.map((a, i) => (
          <div
            key={`ann-${i}`}
            className="epk-annotate-rect epk-annotate-rect--saved"
            style={{
              left: `${(a.bbox_norm?.x || 0) * 100}%`,
              top: `${(a.bbox_norm?.y || 0) * 100}%`,
              width: `${(a.bbox_norm?.w || 0) * 100}%`,
              height: `${(a.bbox_norm?.h || 0) * 100}%`,
            }}
            title={a.note}
          />
        ))}
      </div>
      <div className="epk-annotate-controls">
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Note for selected region…"
        />
        <button type="button" className="portal-btn portal-btn--ghost" onClick={addAnnotation}>
          Add note
        </button>
        <button
          type="button"
          className="portal-btn portal-btn--primary"
          disabled={!annotations.length}
          onClick={handleSubmit}
        >
          Apply feedback ({annotations.length})
        </button>
        <button type="button" className="portal-btn portal-btn--ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default EpkAnnotationLayer;
