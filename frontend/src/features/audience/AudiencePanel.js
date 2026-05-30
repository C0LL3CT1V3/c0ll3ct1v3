import React, { useCallback, useEffect, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';

const TIER_LABELS = {
  aspiration: 'Established — reach goals',
  engagement: 'Up-and-coming — realistic engagement',
  peer: 'Peer league — collaborators',
};

function AudiencePanel({ selectedAssetId }) {
  const { apiClient, authReady } = useApiClient();
  const [profile, setProfile] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadProfile = useCallback(async () => {
    try {
      const res = await apiClient.get('/artists/me/audience-profile');
      setProfile(res.data?.audience_profile || null);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load audience profile.');
    }
  }, [apiClient]);

  useEffect(() => {
    if (!authReady) return;
    loadProfile();
  }, [loadProfile, authReady]);

  const analyzeSelected = async () => {
    if (!selectedAssetId) {
      setError('Select a track in the library first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await apiClient.post(
        `/music/media/assets/${selectedAssetId}/audience-map?persist=true`,
      );
      setReport(res.data);
      await loadProfile();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  const display = report || profile;
  const tiers = display?.tiers || {};

  return (
    <div className="audience-panel">
      <h2 className="portal-panel-title">Audience map</h2>
      <p className="portal-panel-hint">
        Classify your sound and find similar artists — established comps for direction, emerging comps for
        realistic engagement.
      </p>
      {error ? <div className="error-message">{error}</div> : null}
      <div className="audience-actions">
        <button
          type="button"
          className="portal-btn portal-btn--primary"
          onClick={analyzeSelected}
          disabled={loading || !selectedAssetId}
        >
          {loading ? 'Analyzing…' : 'Analyze selected track'}
        </button>
        {!selectedAssetId ? (
          <span className="audience-hint">Select a library item on the Studio tab first.</span>
        ) : null}
      </div>

      {display ? (
        <>
          <p className="audience-pitch">
            <strong>{display.primary_genre}</strong>
            {display.pitch_line ? ` — ${display.pitch_line}` : null}
          </p>
          {display.audio_features ? (
            <p className="portal-panel-hint">
              {display.audio_features.bpm} BPM · {display.audio_features.key}
              {display.mode ? ` · mode: ${display.mode}` : ''}
            </p>
          ) : null}
          <div className="audience-tiers">
            {Object.entries(TIER_LABELS).map(([key, label]) => (
              <div key={key} className="audience-tier-col">
                <h3>{label}</h3>
                <ul>
                  {(tiers[key] || []).map((a) => (
                    <li key={`${key}-${a.name}`}>
                      <span className="audience-artist-name">{a.name}</span>
                      {a.followers ? (
                        <span className="audience-artist-meta">
                          {(a.followers / 1000).toFixed(0)}k followers · pop {a.popularity}
                        </span>
                      ) : (
                        <span className="audience-artist-meta">{a.source || 'seed'}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          {display.actions?.length ? (
            <div className="audience-actions-list">
              <h3>Next steps</h3>
              <ul>
                {display.actions.map((act) => (
                  <li key={act}>{act}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : (
        <p className="portal-panel-hint">No audience map yet. Select a ready track and run analyze.</p>
      )}
    </div>
  );
}

export default AudiencePanel;
