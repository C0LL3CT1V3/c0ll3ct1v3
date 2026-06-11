import React, { useRef, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';
import ManagerChat from '../manager/ManagerChat';
import EpkAnnotationLayer from './EpkAnnotationLayer';
import EpkDesignHistory from './EpkDesignHistory';
import EpkPreviewFrame from './EpkPreviewFrame';
import ProfileCodeEditor from './ProfileCodeEditor';

function EpkBuilderStudio({ builder, onError }) {
  const previewRef = useRef(null);
  const { apiClient } = useApiClient();
  const [annotateMode, setAnnotateMode] = useState(false);
  const [consent, setConsent] = useState(false);
  const [studioMode, setStudioMode] = useState('ai');

  const busy = builder.phase === 'generating' || builder.phase === 'refining';

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
      onError?.(err?.response?.data?.detail || err.message || 'Failed to refresh preview.');
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

  const handlePreviewHistory = async (iterationId) => {
    try {
      onError?.('');
      await builder.previewIteration(iterationId);
    } catch (err) {
      onError?.(err?.response?.data?.detail || err.message || 'Failed to load design.');
    }
  };

  const handleRestoreHistory = async (iterationId) => {
    try {
      onError?.('');
      await builder.restoreIteration(iterationId);
    } catch (err) {
      onError?.(err?.response?.data?.detail || err.message || 'Failed to restore design.');
    }
  };

  const handleSaveCustomHtml = async ({ html, css }) => {
    try {
      onError?.('');
      await builder.saveCustomHtml({ html, css });
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to save custom HTML.';
      onError?.(msg);
      throw err;
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

  const fontSummary = () => {
    const palette = builder.fontPalette;
    if (!palette) return null;
    const parts = [];
    if (palette.heading?.family) parts.push(`Headings: ${palette.heading.family}`);
    if (palette.body?.family) parts.push(`Body: ${palette.body.family}`);
    if (palette.accent?.family) parts.push(`Accent: ${palette.accent.family}`);
    return parts.length ? parts.join(' · ') : null;
  };

  return (
    <section className="epk-builder-studio">
      <div className="profile-studio-tabs">
        <button
          type="button"
          className={`portal-btn portal-btn--ghost${studioMode === 'ai' ? ' portal-btn--active' : ''}`}
          onClick={() => setStudioMode('ai')}
        >
          AI build
        </button>
        <button
          type="button"
          className={`portal-btn portal-btn--ghost${studioMode === 'code' ? ' portal-btn--active' : ''}`}
          onClick={() => setStudioMode('code')}
        >
          Paste HTML/CSS
        </button>
      </div>

      {studioMode === 'code' ? (
        <>
          <ProfileCodeEditor
            initialHtml={builder.draft?.html}
            initialCss={builder.draft?.css}
            googleFontsHref={builder.draft?.google_fonts_href}
            onSave={handleSaveCustomHtml}
            busy={busy}
            error={builder.error}
          />
          <div className="profile-code-footer">
            <button type="button" className="portal-btn portal-btn--primary" onClick={handlePublish}>
              Go live
            </button>
            <span className="profile-code-hint">Apply your code first, then go live on your subdomain.</span>
          </div>
        </>
      ) : null}

      {studioMode === 'ai' ? (
        <>
          {fontSummary() ? <p className="epk-builder-fonts">{fontSummary()}</p> : null}

          {builder.reasoningSummary || builder.critiqueSummary ? (
            <div className="epk-builder-meta">
              {builder.reasoningSummary ? (
                <p className="manager-reasoning-hint">{builder.reasoningSummary}</p>
              ) : null}
              {builder.critiqueSummary ? (
                <p className="epk-builder-critique">{builder.critiqueSummary}</p>
              ) : null}
              {builder.revisionCycles != null ? (
                <p className="epk-builder-cycles">
                  Agent cycles: {builder.revisionCycles}
                  {builder.matchScore != null ? ` · Match score: ${Math.round(builder.matchScore * 100)}%` : ''}
                </p>
              ) : null}
            </div>
          ) : null}

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
          <div className="epk-builder-main">
            <EpkDesignHistory
              iterations={builder.designHistory}
              selectedId={builder.currentIterationId}
              onSelect={handlePreviewHistory}
              onRestore={handleRestoreHistory}
              busy={busy}
            />
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
                  Go live
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
          </div>
        </>
      ) : null}
    </section>
  );
}

export default EpkBuilderStudio;
