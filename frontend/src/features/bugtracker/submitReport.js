import { getConsoleErrors } from './consoleBuffer';

export const FIXTURE_JPEG =
  'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBwgHBgkIBwgKCgkLDRYPDQwMDRsUFRAWIB0iIiAdHx8kKDQsJCYxJx8fLT0tMTU3Ojo6Iys/RD84QzQ5OjcBCgoKDQwNGg8PGjclHyU3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3N//AABEIAAEAAQMBEQACEQEDEQH/xAAXAAADAQAAAAAAAAAAAAAAAAABAgME/8QAFhABAQEAAAAAAAAAAAAAAAAAABEB/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAGfP//Z';

export function configuredReportUrl() {
  return (process.env.REACT_APP_BUGTRACKER_URL || '').trim();
}

export function bugtrackerQueryEnabled() {
  if (typeof window === 'undefined') return false;
  return new URLSearchParams(window.location.search).get('bugtracker') === '1';
}

export function reportEndpoint() {
  return configuredReportUrl() || (bugtrackerQueryEnabled() ? '/__bugtracker-reports' : '');
}

export function widgetEnabled() {
  return Boolean(configuredReportUrl() || bugtrackerQueryEnabled());
}

export function buildReportPayload({ imageDataUrl, summary, type }) {
  return {
    image_data_url: imageDataUrl,
    summary: String(summary || '').trim(),
    type: type === 'feature' ? 'feature' : 'bug',
    page_url: typeof window !== 'undefined' ? window.location.href : '',
    viewport:
      typeof window !== 'undefined'
        ? {
            w: window.innerWidth,
            h: window.innerHeight,
            dpr: window.devicePixelRatio || 1,
          }
        : { w: 0, h: 0, dpr: 1 },
    user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
    console_errors: getConsoleErrors(),
  };
}

export async function submitReport(payload, endpoint = reportEndpoint()) {
  if (!endpoint) {
    throw new Error('Bugtracker URL is not configured');
  }
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text };
  }
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || text || `Report failed (${res.status})`);
  }
  return data;
}
