import React from 'react';

export default function BugReportModal({
  imageDataUrl,
  summary,
  reportType,
  submitting,
  error,
  onSummaryChange,
  onTypeChange,
  onSubmit,
  onCancel,
}) {
  return (
    <div className="bugtracker-backdrop" role="presentation">
      <form
        className="bugtracker-modal"
        data-testid="bugtracker-modal"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <h2>Send a report</h2>
        <p className="bugtracker-lead">Annotated screenshot plus a short note. Context (URL, browser, console) is attached automatically.</p>
        {imageDataUrl ? (
          <img className="bugtracker-preview" src={imageDataUrl} alt="Annotated screenshot preview" />
        ) : null}
        <fieldset className="bugtracker-types">
          <legend>Type</legend>
          <label>
            <input
              type="radio"
              name="bugtracker-type"
              value="bug"
              checked={reportType === 'bug'}
              onChange={() => onTypeChange('bug')}
            />
            Bug
          </label>
          <label>
            <input
              type="radio"
              name="bugtracker-type"
              value="feature"
              checked={reportType === 'feature'}
              onChange={() => onTypeChange('feature')}
            />
            Feature request
          </label>
        </fieldset>
        <label className="bugtracker-summary">
          What went wrong / what do you want?
          <textarea
            data-testid="bugtracker-summary"
            value={summary}
            onChange={(event) => onSummaryChange(event.target.value)}
            rows={4}
            required
            maxLength={4000}
            placeholder="Be specific: what you tapped, what you expected, what happened."
          />
        </label>
        {error ? (
          <p className="bugtracker-error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="bugtracker-actions">
          <button type="button" className="bugtracker-secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" className="bugtracker-primary" data-testid="bugtracker-submit" disabled={submitting}>
            {submitting ? 'Sending…' : 'Submit'}
          </button>
        </div>
      </form>
    </div>
  );
}
