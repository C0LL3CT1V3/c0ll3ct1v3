import React, { useCallback, useEffect, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';
import { profilePublicUrl } from '../../hooks/useTenantSlug';
import DropSlot from '../media/DropSlot';
import AssetListThumb from '../media/AssetListThumb';
import { usePortalWorkbench } from '../media/PortalWorkbenchProvider';
import VaultSidebarPanel from '../vault/VaultSidebarPanel';

function newEvent() {
  const id = typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `ev-${Date.now()}`;
  return {
    id,
    title: '',
    start: '',
    end: '',
    venue: '',
    city: '',
    ticket_url: '',
    notes: '',
    image_asset_id: null,
  };
}

function toLocalInput(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInput(value) {
  if (!value) return '';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toISOString();
}

function emptyPay() {
  return {
    enabled: true,
    blurb: '',
    amounts: [5, 10, 20],
    button_label: 'Pay',
  };
}

function HomebaseStudio({ profile, onProfileRefresh }) {
  const { apiClient } = useApiClient();
  const { workbench, setMediaError } = usePortalWorkbench();
  const [headline, setHeadline] = useState('');
  const [events, setEvents] = useState([]);
  const [pay, setPay] = useState(emptyPay());
  const [amountsText, setAmountsText] = useState('5, 10, 20');
  const [published, setPublished] = useState(false);
  const [checkoutAvailable, setCheckoutAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    const res = await apiClient.get('/artists/me/homebase');
    const cfg = res.data?.config || {};
    setHeadline(cfg.headline || '');
    setEvents(Array.isArray(cfg.events) ? cfg.events : []);
    const nextPay = { ...emptyPay(), ...(cfg.pay || {}) };
    setPay(nextPay);
    setAmountsText((nextPay.amounts || [5, 10, 20]).join(', '));
    setPublished(Boolean(cfg.published));
    setCheckoutAvailable(Boolean(res.data?.checkout_available));
  }, [apiClient]);

  useEffect(() => {
    load().catch((err) => {
      setError(err?.response?.data?.detail || 'Failed to load Homebase.');
    });
  }, [load]);

  const parseAmounts = () =>
    amountsText
      .split(/[,\s]+/)
      .map((s) => parseInt(s, 10))
      .filter((n) => n > 0);

  const payload = () => ({
    headline,
    events: events.map((ev) => ({
      ...ev,
      start: fromLocalInput(ev.start),
      end: ev.end ? fromLocalInput(ev.end) : null,
      image_asset_id: ev.image_asset_id || null,
    })),
    pay: {
      ...pay,
      amounts: parseAmounts(),
    },
  });

  const save = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const res = await apiClient.patch('/artists/me/homebase', payload());
      const cfg = res.data?.config || {};
      setPublished(Boolean(cfg.published));
      setCheckoutAvailable(Boolean(res.data?.checkout_available));
      setMessage('Homebase saved.');
      return res.data;
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to save Homebase.');
      throw err;
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await apiClient.patch('/artists/me/homebase', payload());
      const res = await apiClient.post('/artists/me/homebase/publish');
      const cfg = res.data?.config || {};
      setPublished(Boolean(cfg.published));
      setCheckoutAvailable(Boolean(res.data?.checkout_available));
      setMessage('Homebase published.');
      if (onProfileRefresh) await onProfileRefresh();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to publish Homebase.');
    } finally {
      setBusy(false);
    }
  };

  const updateEvent = (id, field, value) => {
    setEvents((rows) => rows.map((row) => (row.id === id ? { ...row, [field]: value } : row)));
  };

  const viewUrl = profile?.tenant_slug
    ? `${profilePublicUrl(profile.tenant_slug)}/homebase`
    : null;

  return (
    <div className="portal-studio-panels portal-studio-panels--homebase">
      <VaultSidebarPanel
        assets={workbench.assets}
        thumbs={workbench.thumbs}
        filterType="image"
        onDeleteAsset={workbench.deleteAsset}
        onError={setMediaError}
        title="Vault"
        hint="Drag an image onto an event flyer slot."
      />
      <div className="homebase-studio">
        {message ? <div className="portal-success-message">{message}</div> : null}
        {error ? <div className="error-message">{error}</div> : null}

        <div className="epk-booker-actions">
          <button type="button" className="portal-btn portal-btn--ghost" disabled={busy} onClick={save}>
            Save draft
          </button>
          <button type="button" className="portal-btn portal-btn--primary" disabled={busy} onClick={publish}>
            Publish Homebase
          </button>
          {published && viewUrl ? (
            <a href={viewUrl} target="_blank" rel="noreferrer" className="portal-btn portal-btn--ghost">
              View live
            </a>
          ) : null}
        </div>

        <label className="epk-booker-field">
          Headline
          <input
            className="epk-booker-input"
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
            placeholder="See you out there"
          />
        </label>

        <h2 className="homebase-studio-subtitle">Events</h2>
        {events.map((ev) => {
          const flyer = workbench.assets.find((a) => a.id === ev.image_asset_id);
          return (
            <div key={ev.id} className="homebase-event-row">
              <label className="epk-booker-field">
                Title
                <input
                  className="epk-booker-input"
                  value={ev.title}
                  onChange={(e) => updateEvent(ev.id, 'title', e.target.value)}
                />
              </label>
              <label className="epk-booker-field">
                Start
                <input
                  className="epk-booker-input"
                  type="datetime-local"
                  value={toLocalInput(ev.start)}
                  onChange={(e) => updateEvent(ev.id, 'start', e.target.value)}
                />
              </label>
              <label className="epk-booker-field">
                Venue
                <input
                  className="epk-booker-input"
                  value={ev.venue || ''}
                  onChange={(e) => updateEvent(ev.id, 'venue', e.target.value)}
                />
              </label>
              <label className="epk-booker-field">
                City
                <input
                  className="epk-booker-input"
                  value={ev.city || ''}
                  onChange={(e) => updateEvent(ev.id, 'city', e.target.value)}
                />
              </label>
              <label className="epk-booker-field">
                Ticket URL
                <input
                  className="epk-booker-input"
                  value={ev.ticket_url || ''}
                  onChange={(e) => updateEvent(ev.id, 'ticket_url', e.target.value)}
                  placeholder="https://"
                />
              </label>
              <label className="epk-booker-field">
                Notes
                <input
                  className="epk-booker-input"
                  value={ev.notes || ''}
                  onChange={(e) => updateEvent(ev.id, 'notes', e.target.value)}
                />
              </label>
              <DropSlot
                label="Flyer"
                onDrop={(id) => updateEvent(ev.id, 'image_asset_id', id)}
                onClear={ev.image_asset_id ? () => updateEvent(ev.id, 'image_asset_id', null) : null}
                assets={workbench.assets}
                acceptTypes={['image']}
              >
                {flyer ? (
                  <p className="epk-booker-filled">
                    <AssetListThumb asset={flyer} thumbUrl={workbench.thumbs[flyer.id]} />
                    {flyer.title || 'Flyer'}
                  </p>
                ) : (
                  <p className="epk-booker-hint">Drop an image from Vault</p>
                )}
              </DropSlot>
              <button
                type="button"
                className="portal-btn portal-btn--ghost portal-btn--small"
                onClick={() => setEvents((rows) => rows.filter((row) => row.id !== ev.id))}
              >
                Remove
              </button>
            </div>
          );
        })}
        <button type="button" className="portal-btn portal-btn--ghost" onClick={() => setEvents((rows) => [...rows, newEvent()])}>
          Add event
        </button>

        <h2 className="homebase-studio-subtitle">Pay</h2>
        {!checkoutAvailable ? (
          <p className="portal-panel-hint">
            Square checkout is not configured on this server yet (needs SQUARE_ACCESS_TOKEN and SQUARE_LOCATION_ID).
            Fans will not see the Pay button until it is.
          </p>
        ) : null}
        <label className="epk-booker-field">
          <input
            type="checkbox"
            checked={Boolean(pay.enabled)}
            onChange={(e) => setPay((t) => ({ ...t, enabled: e.target.checked }))}
          />{' '}
          Show Pay button
        </label>
        <label className="epk-booker-field">
          Blurb
          <input
            className="epk-booker-input"
            value={pay.blurb || ''}
            onChange={(e) => setPay((t) => ({ ...t, blurb: e.target.value }))}
            placeholder="Fuel the van"
          />
        </label>
        <label className="epk-booker-field">
          Amounts
          <input
            className="epk-booker-input"
            value={amountsText}
            onChange={(e) => setAmountsText(e.target.value)}
            placeholder="5, 10, 20"
          />
        </label>
        <label className="epk-booker-field">
          Button label
          <input
            className="epk-booker-input"
            value={pay.button_label || 'Pay'}
            onChange={(e) => setPay((t) => ({ ...t, button_label: e.target.value }))}
            placeholder="Pay"
          />
        </label>
      </div>
    </div>
  );
}

export default HomebaseStudio;
