import React, { useRef, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';
import ManagerChat from '../manager/ManagerChat';
import EpkAnnotationLayer from './EpkAnnotationLayer';
import EpkPreviewFrame from './EpkPreviewFrame';
import { useEpkBuilder } from './useEpkBuilder';

function EpkBuilderStudio({ onError }) {
  const previewRef = useRef(null);
  const { apiClient } = useApiClient();
  const [annotateMode, setAnnotateMode] = useState(false);
  const [consent, setConsent] = useState(false);
  const builder = useEpkBuilder();

  const handleAfterChat = async ({ draftUpdated, reasoningSummary }) => {
    if (reasoningSummary) {
      builder.setReasoningSummary(reasoningSummary);
    }
    if (!draftUpdated) return;
    try {
      onError?.('');
      builder.setPhase('generating');
      await builder.loadDraft();
      builder.setPhase('preview');
    } catch (err) {
      onError?.(err?.response?.data?.detail || err.message || 'Failed to refresh EPK preview.');
      builder.setPhase('idle');
    }
  };

  const handleAnnotateSubmit = async (annotations) => {
    try {
      onError?.('');
      await builder.submitAnnotations(annotations);
      setAnnotateMode(false);
      await builder.refine(previewRef);
    } catch (err) {
      onError?.(err?.response?.data?.detail || err.message || 'Refine failed.');
    }
  };

  const handleAccept = async () => {
    try {
      onError?.('');
      await builder.accept(consent);
      if (consent) {
        await apiClient.patch('/manager/training/consent', { allow_training_contribution: true });
      }
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Accept failed.');
    }
  };

  const handlePublish = async () => {
    try {
      onError?.('');
      await builder.publish();
    } catch (err) {
      onError?.(err?.response?.data?.detail || 'Publish failed.');
    }
  };

  return (
    <section className="epk-builder-studio">
      <header className="epk-builder-header">
        <h2 className="portal-panel-title">EPK Builder</h2>
        <p className="epk-builder-lead">Design your press kit from workbench assets — chat, preview, annotate, publish.</p>
      </header>
      <div className="epk-builder-chat">
        <ManagerChat
          layout="horizontal"
          mode="epk_builder"
          threadId={builder.threadId}
          onThreadId={builder.setThreadId}
          onAfterReply={handleAfterChat}
          phase={builder.phase}
          reasoningSummary={builder.reasoningSummary}
        />
      </div>
      <div className="epk-builder-preview-wrap">
        <div className="epk-builder-toolbar">
          <button
            type="button"
            className={`portal-btn portal-btn--ghost${annotateMode ? ' portal-btn--active' : ''}`}
            onClick={() => setAnnotateMode((v) => !v)}
            disabled={!builder.currentIterationId}
          >
            Annotate
          </button>
          <button
            type="button"
            className="portal-btn portal-btn--ghost"
            disabled={!builder.currentIterationId}
            onClick={handleAccept}
          >
            Accept iteration
          </button>
          <label className="epk-consent-label">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            Contribute to training
          </label>
          <button type="button" className="portal-btn portal-btn--primary" onClick={handlePublish}>
            Publish EPK
          </button>
        </div>
        {builder.error ? <div className="error-message">{builder.error}</div> : null}
        <div className="epk-preview-container" ref={previewRef}>
          <EpkPreviewFrame draft={builder.draft} />
          <EpkAnnotationLayer
            containerRef={previewRef}
            enabled={annotateMode}
            onSubmit={handleAnnotateSubmit}
            onCancel={() => setAnnotateMode(false)}
          />
        </div>
      </div>
    </section>
  );
}

export default EpkBuilderStudio;
