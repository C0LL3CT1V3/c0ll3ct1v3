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
