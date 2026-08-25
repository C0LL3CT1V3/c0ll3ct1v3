import React, { useCallback, useEffect, useState } from 'react';
import BugReportModal from './BugReportModal';
import { captureScreenshot } from './captureScreenshot';
import { openAnnotator } from './openAnnotator';
import {
  FIXTURE_JPEG,
  bugtrackerQueryEnabled,
  buildReportPayload,
  submitReport,
  widgetEnabled,
} from './submitReport';
import './bugtracker.css';

export default function BugReportWidget() {
  const enabled = widgetEnabled();
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

  const onTrigger = async () => {
    setToast('');
    setHiddenForCapture(true);
    try {
      const raw = await captureScreenshot();
      const annotated = await openAnnotator(raw);
      setImageDataUrl(annotated);
    } catch (err) {
      if (!err?.cancelled) {
        setToast(err.message || 'Screenshot cancelled');
      }
    } finally {
      setHiddenForCapture(false);
    }
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

  return (
    <>
      {!hiddenForCapture && !imageDataUrl ? (
        <button
          type="button"
          className="bugtracker-trigger"
          data-testid="bugtracker-trigger"
          onClick={onTrigger}
        >
          Report
        </button>
      ) : null}
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
