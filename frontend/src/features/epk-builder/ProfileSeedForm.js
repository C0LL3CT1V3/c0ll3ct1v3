import React from 'react';

function ProfileSeedForm({ builder, visions, onError, busy }) {
  const handleAddSeed = async () => {
    if (!builder.selectedVisionId || !builder.spec.trim()) {
      onError?.('Select a vision group and write a design spec first.');
      return;
    }
    try {
      onError?.('');
      await builder.buildFromVision(builder.selectedVisionId, builder.spec.trim());
    } catch (err) {
      onError?.(err?.response?.data?.detail || err.message || 'Failed to add profile seed.');
    }
  };

  return (
    <div className="profile-seed-form">
      <label className="epk-builder-field">
        <span className="epk-builder-field-label">Vision group</span>
        <select
          value={builder.selectedVisionId}
          onChange={(e) => builder.setSelectedVisionId(e.target.value)}
          disabled={busy}
        >
          <option value="">Select vision…</option>
          {visions.map((v) => (
            <option key={v.id} value={v.id}>
              {v.title}
            </option>
          ))}
        </select>
      </label>
      <label className="epk-builder-field epk-builder-field--spec">
        <span className="epk-builder-field-label">Design spec</span>
        <textarea
          value={builder.spec}
          onChange={(e) => builder.setSpec(e.target.value)}
          placeholder="Describe your page vibe: colors, layout, glitter energy, sections…"
          rows={3}
          disabled={busy}
        />
      </label>
      <button
        type="button"
        className="portal-btn portal-btn--primary profile-seed-form-btn"
        disabled={busy || !builder.selectedVisionId || !builder.spec.trim()}
        onClick={handleAddSeed}
      >
        {busy ? 'Creating seed…' : 'Add new profile seed'}
      </button>
    </div>
  );
}

export default ProfileSeedForm;
