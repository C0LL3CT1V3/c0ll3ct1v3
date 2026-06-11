import React, { useEffect, useMemo, useState } from 'react';
import {
  DEFAULT_PROFILE_CSS,
  DEFAULT_PROFILE_HTML,
  buildPreviewDocument,
} from './buildPreviewDocument';

function ProfileCodeEditor({
  initialHtml,
  initialCss,
  googleFontsHref,
  onSave,
  busy,
  error,
}) {
  const [html, setHtml] = useState(initialHtml || DEFAULT_PROFILE_HTML);
  const [css, setCss] = useState(initialCss || DEFAULT_PROFILE_CSS);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (initialHtml != null) setHtml(initialHtml);
  }, [initialHtml]);

  useEffect(() => {
    if (initialCss != null) setCss(initialCss);
  }, [initialCss]);

  const previewDoc = useMemo(
    () => buildPreviewDocument({ html, css, googleFontsHref }),
    [html, css, googleFontsHref],
  );

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({ html, css });
      setDirty(false);
    } finally {
      setSaving(false);
    }
  };

  const handleHtmlChange = (e) => {
    setHtml(e.target.value);
    setDirty(true);
  };

  const handleCssChange = (e) => {
    setCss(e.target.value);
    setDirty(true);
  };

  const handleReset = () => {
    setHtml(DEFAULT_PROFILE_HTML);
    setCss(DEFAULT_PROFILE_CSS);
    setDirty(true);
  };

  return (
    <div className="profile-code-editor">
      <div className="profile-code-editor-panes">
        <div className="profile-code-editor-inputs">
          <label className="profile-code-field">
            <span className="profile-code-field-label">HTML</span>
            <textarea
              className="profile-code-textarea"
              value={html}
              onChange={handleHtmlChange}
              spellCheck={false}
              disabled={busy || saving}
              rows={14}
            />
          </label>
          <label className="profile-code-field">
            <span className="profile-code-field-label">CSS</span>
            <textarea
              className="profile-code-textarea profile-code-textarea--css"
              value={css}
              onChange={handleCssChange}
              spellCheck={false}
              disabled={busy || saving}
              rows={14}
            />
          </label>
          <div className="profile-code-actions">
            <button
              type="button"
              className="portal-btn portal-btn--primary"
              onClick={handleSave}
              disabled={busy || saving || !dirty}
            >
              {saving ? 'Saving…' : 'Apply to profile'}
            </button>
            <button
              type="button"
              className="portal-btn portal-btn--ghost"
              onClick={handleReset}
              disabled={busy || saving}
            >
              Reset template
            </button>
            <span className="profile-code-hint">
              Preview updates as you type. Use <code>{'{{asset_key}}'}</code> for workbench media after save.
            </span>
          </div>
          {error ? <div className="error-message">{error}</div> : null}
        </div>
        <div className="profile-code-editor-preview">
          <span className="profile-code-field-label">Preview</span>
          <div className="profile-code-preview-frame">
            <iframe
              title="Profile code preview"
              className="profile-code-preview-iframe"
              srcDoc={previewDoc}
              sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfileCodeEditor;
