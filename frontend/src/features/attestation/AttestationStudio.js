import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { usePortalWorkbench } from '../media/PortalWorkbenchProvider';

const CLAIM_LABELS = {
  credit: 'Credit',
  split: 'Split',
  consent_train: 'Train consent',
  consent_sync: 'Sync consent',
  consent_cite: 'Cite consent',
  canonical_version: 'Canonical version',
  identifiers: 'Identifiers',
};

function statusClass(status) {
  if (status === 'active') return 'attest-status attest-status--active';
  if (status === 'draft') return 'attest-status attest-status--draft';
  if (status === 'rejected') return 'attest-status attest-status--rejected';
  return 'attest-status';
}

function ClaimCard({ claim, onConfirm, onReject, busyId }) {
  const [editing, setEditing] = useState(false);
  const [draftValue, setDraftValue] = useState(() => JSON.stringify(claim.value || {}, null, 2));
  const busy = busyId === claim.id;

  useEffect(() => {
    setDraftValue(JSON.stringify(claim.value || {}, null, 2));
    setEditing(false);
  }, [claim.id, claim.value]);

  const saveConfirm = async () => {
    let parsed = claim.value;
    if (editing) {
      try {
        parsed = JSON.parse(draftValue);
      } catch {
        return;
      }
    }
    await onConfirm(claim.id, parsed);
  };

  return (
    <article className="attest-card">
      <header className="attest-card-header">
        <strong>{CLAIM_LABELS[claim.claim_type] || claim.claim_type}</strong>
        <span className={statusClass(claim.status)}>{claim.status}</span>
        <span className="attest-source">{claim.source}</span>
      </header>
      {editing ? (
        <textarea
          className="attest-json"
          value={draftValue}
          onChange={(e) => setDraftValue(e.target.value)}
          rows={8}
        />
      ) : (
        <pre className="attest-json-view">{JSON.stringify(claim.value, null, 2)}</pre>
      )}
      {claim.signature ? (
        <p className="attest-sig">
          signed {claim.key_fingerprint?.slice(0, 12)}…
        </p>
      ) : null}
      {claim.status === 'draft' ? (
        <div className="attest-card-actions">
          <button type="button" className="portal-btn portal-btn--primary" disabled={busy} onClick={saveConfirm}>
            Confirm
          </button>
          <button
            type="button"
            className="portal-btn portal-btn--ghost"
            disabled={busy}
            onClick={() => setEditing((v) => !v)}
          >
            {editing ? 'Cancel edit' : 'Edit'}
          </button>
          <button type="button" className="portal-btn portal-btn--ghost" disabled={busy} onClick={() => onReject(claim.id)}>
            Reject
          </button>
        </div>
      ) : null}
    </article>
  );
}

function AttestationStudio() {
  const { apiClient, selectedId, setSelectedId, workbench } = usePortalWorkbench();
  const [claims, setClaims] = useState([]);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [ingesting, setIngesting] = useState(false);
  const [csvName, setCsvName] = useState('');

  const audioAssets = useMemo(
    () => (workbench.assets || []).filter((a) => a.asset_type === 'audio'),
    [workbench.assets],
  );

  const loadClaims = useCallback(
    async (assetId) => {
      if (!apiClient || !assetId) {
        setClaims([]);
        return;
      }
      try {
        const res = await apiClient.get('/manager/attestations', { params: { asset_id: assetId } });
        setClaims(res.data.claims || []);
        setError('');
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'Failed to load claims.');
      }
    },
    [apiClient],
  );

  useEffect(() => {
    loadClaims(selectedId);
  }, [selectedId, loadClaims]);

  const ingest = async () => {
    if (!selectedId) return;
    setIngesting(true);
    setError('');
    try {
      await apiClient.post(`/manager/ingest/${selectedId}`, { sources: ['mlc', 'musicbrainz', 'consent_flag'] });
      await loadClaims(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Ingest failed.');
    } finally {
      setIngesting(false);
    }
  };

  const uploadCsv = async (file) => {
    if (!selectedId || !file) return;
    setIngesting(true);
    setCsvName(file.name);
    setError('');
    try {
      const text = await file.text();
      await apiClient.post(`/manager/ingest/${selectedId}`, {
        sources: ['distributor_export'],
        csv_text: text,
      });
      await loadClaims(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'CSV ingest failed.');
    } finally {
      setIngesting(false);
    }
  };

  const onConfirm = async (id, value) => {
    setBusyId(id);
    try {
      await apiClient.post(`/manager/attestations/${id}/confirm`, { value });
      await loadClaims(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Confirm failed.');
    } finally {
      setBusyId(null);
    }
  };

  const onReject = async (id) => {
    setBusyId(id);
    try {
      await apiClient.post(`/manager/attestations/${id}/reject`);
      await loadClaims(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Reject failed.');
    } finally {
      setBusyId(null);
    }
  };

  const drafts = claims.filter((c) => c.status === 'draft');
  const actives = claims.filter((c) => c.status === 'active');
  const others = claims.filter((c) => c.status !== 'draft' && c.status !== 'active');

  return (
    <div className="portal-studio-panels attest-layout">
      <aside className="attest-asset-list">
        <h2 className="attest-aside-title">Audio in Vault</h2>
        {audioAssets.length === 0 ? (
          <p className="portal-section-lead">Upload a track in Vault first.</p>
        ) : (
          <ul>
            {audioAssets.map((asset) => (
              <li key={asset.id}>
                <button
                  type="button"
                  className={`attest-asset-btn${selectedId === asset.id ? ' is-selected' : ''}`}
                  onClick={() => setSelectedId(asset.id)}
                >
                  {asset.title || asset.id}
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
      <div className="portal-workbench-main attest-main">
        {!selectedId ? (
          <p className="portal-section-lead">Select a track to review ingested claims.</p>
        ) : (
          <>
            <div className="attest-toolbar">
              <button type="button" className="portal-btn portal-btn--primary" disabled={ingesting} onClick={ingest}>
                {ingesting ? 'Looking up…' : 'Find what we can'}
              </button>
              <label className="portal-btn portal-btn--ghost attest-file-label">
                Upload distributor CSV
                <input
                  type="file"
                  accept=".csv"
                  hidden
                  onChange={(e) => uploadCsv(e.target.files?.[0])}
                />
              </label>
              {csvName ? <span className="attest-source">{csvName}</span> : null}
            </div>
            {error ? <div className="error-message">{error}</div> : null}
            <section>
              <h2 className="attest-group-title">Review drafts</h2>
              {drafts.length === 0 ? (
                <p className="portal-section-lead">No drafts yet. Run a lookup or add a CSV.</p>
              ) : (
                drafts.map((claim) => (
                  <ClaimCard
                    key={claim.id}
                    claim={claim}
                    onConfirm={onConfirm}
                    onReject={onReject}
                    busyId={busyId}
                  />
                ))
              )}
            </section>
            <section>
              <h2 className="attest-group-title">Signed</h2>
              {actives.length === 0 ? (
                <p className="portal-section-lead">Confirmed claims appear here.</p>
              ) : (
                actives.map((claim) => (
                  <ClaimCard key={claim.id} claim={claim} onConfirm={onConfirm} onReject={onReject} busyId={busyId} />
                ))
              )}
            </section>
            {others.length ? (
              <section>
                <h2 className="attest-group-title">History</h2>
                {others.map((claim) => (
                  <ClaimCard key={claim.id} claim={claim} onConfirm={onConfirm} onReject={onReject} busyId={busyId} />
                ))}
              </section>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

export default AttestationStudio;
