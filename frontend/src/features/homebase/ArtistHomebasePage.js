import React, { useEffect, useMemo, useRef, useState } from 'react';
import { getSubdomain } from '../../hooks/useTenantSlug';

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function apiUrl(path) {
  const apiBase = (process.env.REACT_APP_API_URL || '/api').replace(/\/$/, '');
  return apiBase.startsWith('http')
    ? `${apiBase}${path}`
    : `${window.location.origin}${apiBase}${path}`;
}

/** Rewrite backend media URLs (prod origin or /api prefix) onto the API host this SPA uses. */
function resolveMediaUrl(url) {
  if (!url) return '';
  try {
    const parsed = new URL(url, window.location.origin);
    const homebase = parsed.pathname.match(/\/artists\/public\/[^/]+\/homebase\/media\/[^/]+$/);
    if (homebase) return apiUrl(homebase[0]);
    const withApi = parsed.pathname.match(/\/api(\/artists\/public\/[^/]+\/homebase\/media\/[^/]+)$/);
    if (withApi) return apiUrl(withApi[1]);
    return url;
  } catch {
    return url;
  }
}

function parseEventDate(start) {
  if (!start) return null;
  const d = new Date(start);
  return Number.isNaN(d.getTime()) ? null : d;
}

function eventDateKey(start) {
  const d = parseEventDate(start);
  if (!d) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function formatShowDate(start) {
  const d = parseEventDate(start);
  if (!d) return start || '';
  return d.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatDayHeading(key) {
  const [y, m, d] = key.split('-').map((n) => parseInt(n, 10));
  if (!y || !m || !d) return key;
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

function monthCells(year, month) {
  const firstDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstDow; i += 1) cells.push(null);
  for (let d = 1; d <= daysInMonth; d += 1) cells.push(d);
  return cells;
}

function FlyerImage({ src, title }) {
  const resolved = resolveMediaUrl(src);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [resolved]);
  if (!resolved || failed) return null;
  return (
    <img
      className="homebase-show-flyer"
      src={resolved}
      alt={title ? `${title} flyer` : 'Event flyer'}
      onError={() => setFailed(true)}
    />
  );
}

function ShowCard({ ev, past }) {
  const started = parseEventDate(ev.start);
  const isPast = past || (started && started.getTime() < Date.now());
  return (
    <li className={`homebase-show${isPast ? ' homebase-show--past' : ''}`}>
      <FlyerImage src={ev.image_url} title={ev.title} />
      <div className="homebase-show-body">
        <div className="homebase-show-title">{ev.title || 'Show'}</div>
        <div className="homebase-show-meta">{formatShowDate(ev.start)}</div>
        {ev.venue || ev.city ? (
          <div className="homebase-show-meta">{[ev.venue, ev.city].filter(Boolean).join(' · ')}</div>
        ) : null}
        {ev.notes ? <p className="homebase-show-notes">{ev.notes}</p> : null}
        {!isPast && ev.ticket_url ? (
          <a className="homebase-ticket" href={ev.ticket_url} target="_blank" rel="noreferrer">
            Tickets
          </a>
        ) : null}
      </div>
    </li>
  );
}

function ArtistHomebasePage() {
  const tenantSlug = getSubdomain();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });
  const [selectedDay, setSelectedDay] = useState(null);
  const [selectedAmount, setSelectedAmount] = useState(null);
  const [pastOpen, setPastOpen] = useState(false);
  const [payBusy, setPayBusy] = useState(false);
  const [payError, setPayError] = useState('');
  const didInitCal = useRef(false);

  useEffect(() => {
    if (!tenantSlug) {
      setError('No artist subdomain.');
      setLoading(false);
      return;
    }
    fetch(apiUrl(`/artists/public/${tenantSlug}/homebase`))
      .then((res) => {
        if (!res.ok) throw new Error('Homebase not found or not published.');
        return res.json();
      })
      .then((json) => {
        setData(json);
        setError('');
        const amounts = json?.pay?.amounts;
        if (Array.isArray(amounts) && amounts.length) {
          setSelectedAmount(amounts[0]);
        }
      })
      .catch((err) => setError(err.message || 'Failed to load Homebase.'))
      .finally(() => setLoading(false));
  }, [tenantSlug]);

  const events = useMemo(() => (Array.isArray(data?.events) ? data.events : []), [data]);
  const now = Date.now();
  const upcoming = events.filter((ev) => {
    const d = parseEventDate(ev.start);
    return !d || d.getTime() >= now;
  });
  const past = events.filter((ev) => {
    const d = parseEventDate(ev.start);
    return d && d.getTime() < now;
  });

  const eventsByDay = useMemo(() => {
    const map = new Map();
    events.forEach((ev) => {
      const key = eventDateKey(ev.start);
      if (!key) return;
      const list = map.get(key) || [];
      list.push(ev);
      map.set(key, list);
    });
    return map;
  }, [events]);

  useEffect(() => {
    if (didInitCal.current || !events.length) return;
    const firstUpcoming =
      events.find((ev) => {
        const d = parseEventDate(ev.start);
        return !d || d.getTime() >= Date.now();
      }) || events[0];
    const key = eventDateKey(firstUpcoming?.start);
    if (!key) return;
    setSelectedDay(key);
    const d = parseEventDate(firstUpcoming.start);
    if (d) setCursor({ year: d.getFullYear(), month: d.getMonth() });
    didInitCal.current = true;
  }, [events]);

  const pay = data?.pay;
  const showPay = Boolean(pay?.enabled && data?.checkout_available);
  const amounts = pay?.amounts || [];

  const startCheckout = async () => {
    if (!tenantSlug || !selectedAmount) return;
    setPayBusy(true);
    setPayError('');
    try {
      const res = await fetch(apiUrl(`/artists/public/${tenantSlug}/checkout`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'tip', amount_cents: selectedAmount * 100 }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok || !body.checkout_url) {
        throw new Error(body.detail || 'Checkout is unavailable.');
      }
      window.location.href = body.checkout_url;
    } catch (err) {
      setPayError(err.message || 'Checkout is unavailable.');
      setPayBusy(false);
    }
  };

  if (loading) return <p className="portal-loading">Loading homebase…</p>;
  if (error) return <div className="error-message">{error}</div>;
  if (!data) return null;

  const { year, month } = cursor;
  const cells = monthCells(year, month);
  const monthLabel = new Date(year, month, 1).toLocaleString(undefined, {
    month: 'long',
    year: 'numeric',
  });
  const selectedEvents = selectedDay ? eventsByDay.get(selectedDay) || [] : [];

  const shiftMonth = (delta) => {
    setCursor((c) => {
      const d = new Date(c.year, c.month + delta, 1);
      return { year: d.getFullYear(), month: d.getMonth() };
    });
  };

  return (
    <div className="homebase-page">
      <header className="homebase-hero">
        <p className="homebase-kicker">Homebase</p>
        <h1 className="homebase-name">{data.display_name}</h1>
        {data.headline ? <p className="homebase-headline">{data.headline}</p> : null}
      </header>

      <section className="homebase-section" aria-labelledby="homebase-calendar-title">
        <h2 id="homebase-calendar-title" className="homebase-section-title">
          Calendar
        </h2>
        <div className="homebase-cal-nav">
          <button type="button" className="homebase-cal-nav-btn" onClick={() => shiftMonth(-1)}>
            Previous
          </button>
          <h3 className="homebase-cal-month">{monthLabel}</h3>
          <button type="button" className="homebase-cal-nav-btn" onClick={() => shiftMonth(1)}>
            Next
          </button>
        </div>
        <div className="homebase-cal-grid" role="grid" aria-label={monthLabel}>
          {WEEKDAYS.map((d) => (
            <div key={d} className="homebase-cal-dow" role="columnheader">
              {d}
            </div>
          ))}
          {cells.map((day, idx) => {
            if (!day) {
              return <div key={`e-${idx}`} className="homebase-cal-cell homebase-cal-cell--empty" />;
            }
            const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const dayEvents = eventsByDay.get(key) || [];
            const hasEvent = dayEvents.length > 0;
            const selected = selectedDay === key;
            const countLabel = hasEvent
              ? `${dayEvents.length} event${dayEvents.length === 1 ? '' : 's'}`
              : 'no events';
            if (!hasEvent) {
              return (
                <div key={key} className="homebase-cal-cell">
                  <span>{day}</span>
                </div>
              );
            }
            return (
              <button
                key={key}
                type="button"
                className={`homebase-cal-cell homebase-cal-cell--event${selected ? ' homebase-cal-cell--selected' : ''}`}
                aria-pressed={selected}
                aria-expanded={selected}
                aria-controls="homebase-cal-detail"
                aria-label={`${monthLabel} ${day}, ${countLabel}`}
                onClick={() => setSelectedDay((cur) => (cur === key ? null : key))}
              >
                <span>{day}</span>
                <span className="homebase-cal-dot" aria-hidden="true" />
              </button>
            );
          })}
        </div>

        {selectedEvents.length > 0 ? (
          <div className="homebase-cal-detail" id="homebase-cal-detail">
            <h3 className="homebase-list-title">{formatDayHeading(selectedDay)}</h3>
            <ul className="homebase-show-list">
              {selectedEvents.map((ev) => (
                <ShowCard key={ev.id || ev.start} ev={ev} />
              ))}
            </ul>
          </div>
        ) : (
          <p className="homebase-cal-hint">Select a highlighted day to see the flyer, details, and tickets.</p>
        )}

        <h3 className="homebase-list-title">Upcoming shows</h3>
        {upcoming.length === 0 ? (
          <p className="homebase-empty">No upcoming shows yet.</p>
        ) : (
          <ul className="homebase-show-list">
            {upcoming.map((ev) => (
              <ShowCard key={ev.id || ev.start} ev={ev} />
            ))}
          </ul>
        )}

        {past.length > 0 ? (
          <div className="homebase-past">
            <button
              type="button"
              className="homebase-past-toggle"
              onClick={() => setPastOpen((open) => !open)}
              aria-expanded={pastOpen}
            >
              {pastOpen ? 'Hide past shows' : `Past shows (${past.length})`}
            </button>
            {pastOpen ? (
              <ul className="homebase-show-list">
                {past.map((ev) => (
                  <ShowCard key={ev.id || ev.start} ev={ev} past />
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </section>

      {showPay ? (
        <section className="homebase-section homebase-pay" aria-labelledby="homebase-pay-title">
          <h2 id="homebase-pay-title" className="homebase-section-title">
            Pay
          </h2>
          {pay.blurb ? <p className="homebase-tips-blurb">{pay.blurb}</p> : null}
          {amounts.length > 0 ? (
            <div className="homebase-amount-row" role="group" aria-label="Pay amounts">
              {amounts.map((n) => (
                <button
                  key={n}
                  type="button"
                  className={`homebase-amount${selectedAmount === n ? ' homebase-amount--on' : ''}`}
                  onClick={() => setSelectedAmount(n)}
                >
                  ${n}
                </button>
              ))}
            </div>
          ) : null}
          {payError ? <div className="error-message">{payError}</div> : null}
          <button
            type="button"
            className="homebase-tip-btn"
            disabled={payBusy || !selectedAmount}
            onClick={startCheckout}
          >
            {payBusy ? 'Opening checkout…' : pay.button_label || 'Pay'}
          </button>
        </section>
      ) : null}
    </div>
  );
}

export default ArtistHomebasePage;
