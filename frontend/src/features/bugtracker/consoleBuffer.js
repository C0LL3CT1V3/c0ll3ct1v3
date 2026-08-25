const MAX = 25;
const buffer = [];

function push(entry) {
  buffer.push(entry);
  while (buffer.length > MAX) buffer.shift();
}

function serialize(value) {
  if (value instanceof Error) return value.message || String(value);
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function installConsoleBuffer() {
  if (typeof window === 'undefined') return;
  if (window.__bugtrackerBufferInstalled) return;
  window.__bugtrackerBufferInstalled = true;

  const originalError = console.error.bind(console);
  console.error = (...args) => {
    push({ t: Date.now(), msg: args.map(serialize).join(' ') });
    originalError(...args);
  };

  window.addEventListener('error', (event) => {
    push({ t: Date.now(), msg: event.message || serialize(event.error) || 'window.error' });
  });

  window.addEventListener('unhandledrejection', (event) => {
    push({ t: Date.now(), msg: serialize(event.reason) || 'unhandledrejection' });
  });
}

export function getConsoleErrors() {
  return buffer.map((entry) => ({ ...entry }));
}

export function resetConsoleBufferForTests() {
  buffer.length = 0;
}
