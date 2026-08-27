import React, { useCallback, useEffect, useRef, useState } from 'react';
import Shotmark from 'shotmark';
import BugReportModal from './BugReportModal';
import { toJpegDataUrl } from './toJpegDataUrl';
import {
  FIXTURE_JPEG,
  bugtrackerQueryEnabled,
  buildReportPayload,
  submitReport,
  widgetEnabled,
} from './submitReport';
import './bugtracker.css';

function SnipHint({ onCancel }) {
  const hintRef = useRef(null);
  const dragRef = useRef(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const onPointerDown = (event) => {
    if (event.button !== 0) return;
    if (event.target.closest('[data-testid="bugtracker-snip-cancel"]')) return;
    event.preventDefault();
    event.stopPropagation();
    const node = hintRef.current;
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origX: offset.x,
      origY: offset.y,
      width: node ? node.offsetWidth : 0,
      height: node ? node.offsetHeight : 0,
      left: node ? node.getBoundingClientRect().left : 0,
      top: node ? node.getBoundingClientRect().top : 0,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.preventDefault();
    event.stopPropagation();
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    const maxX = Math.max(8, window.innerWidth - drag.width - 8);
    const maxY = Math.max(8, window.innerHeight - drag.height - 8);
    const nextLeft = Math.min(maxX, Math.max(8, drag.left + dx));
    const nextTop = Math.min(maxY, Math.max(8, drag.top + dy));
    setOffset({
      x: drag.origX + (nextLeft - drag.left),
      y: drag.origY + (nextTop - drag.top),
    });
  };

  const endDrag = (event) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.stopPropagation();
    dragRef.current = null;
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      /* already released */
    }
  };

  return (
    <div
      ref={hintRef}
      className="bugtracker-snip-hint"
      data-testid="bugtracker-snip-hint"
      data-html2canvas-ignore="true"
      role="status"
      style={{ transform: `translate(calc(-50% + ${offset.x}px), ${offset.y}px)` }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
    >
      <p className="bugtracker-snip-hint-text">Drag to select the UI you want to report.</p>
      <button
        type="button"
        className="bugtracker-snip-hint-close"
        data-testid="bugtracker-snip-cancel"
        aria-label="Cancel screenshot"
        onClick={onCancel}
        onPointerDown={(event) => event.stopPropagation()}
      >
        ×
      </button>
    </div>
  );
}

export default function BugReportWidget() {
  const enabled = widgetEnabled();
  const triggerRef = useRef(null);
  const [hiddenForCapture, setHiddenForCapture] = useState(false);
  const [imageDataUrl, setImageDataUrl] = useState('');
  const [summary, setSummary] = useState('');
  const [reportType, setReportType] = useState('bug');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const closeModal = useCallback(() => {
    setImageDataUrl('');
    setSummary('');
    setReportType('bug');
    setError('');
    setSubmitting(false);
  }, []);

  const dismissSnip = useCallback((event) => {
    event?.preventDefault();
    event?.stopPropagation();
    Shotmark.close();
    setHiddenForCapture(false);
  }, []);

  const onTrigger = () => {
    setToast('');
    setError('');
    setHiddenForCapture(true);
    Shotmark.start({
      trigger: triggerRef.current || undefined,
      locale: 'en-US',
      theme: 'dark',
      format: 'jpeg',
      zIndex: 12500,
      actions: ['cancel', 'confirm'],
      onShot: async (res) => {
        try {
          const jpeg = await toJpegDataUrl(res?.image);
          setImageDataUrl(jpeg);
        } catch (err) {
          setToast(err.message || 'Screenshot failed');
        } finally {
          setHiddenForCapture(false);
        }
      },
      onCancel: () => {
        setHiddenForCapture(false);
      },
    });
  };

  useEffect(() => {
    if (!enabled || !bugtrackerQueryEnabled()) return;
    setImageDataUrl(FIXTURE_JPEG);
  }, [enabled]);

  const onSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const payload = buildReportPayload({
        imageDataUrl,
        summary,
        type: reportType,
      });
      const result = await submitReport(payload);
      closeModal();
      setToast(result.issue_url ? `Filed ${result.issue_url}` : 'Report sent');
    } catch (err) {
      setError(err.message || 'Submit failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (!enabled) return null;

  const showTrigger = !hiddenForCapture && !imageDataUrl;
  const showSnipHint = hiddenForCapture && !imageDataUrl;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="bugtracker-trigger"
        data-testid="bugtracker-trigger"
        onClick={onTrigger}
        hidden={!showTrigger}
        aria-hidden={!showTrigger}
      >
        Report
      </button>
      {showSnipHint ? <SnipHint onCancel={dismissSnip} /> : null}
      {imageDataUrl ? (
        <BugReportModal
          imageDataUrl={imageDataUrl}
          summary={summary}
          reportType={reportType}
          submitting={submitting}
          error={error}
          onSummaryChange={setSummary}
          onTypeChange={setReportType}
          onSubmit={onSubmit}
          onCancel={closeModal}
        />
      ) : null}
      {toast ? (
        <div className="bugtracker-toast" role="status">
          {toast}
        </div>
      ) : null}
    </>
  );
}
