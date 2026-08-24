import fs from 'node:fs';
import path from 'node:path';

/** Load e2e/.env into process.env without overriding existing vars. */
export function loadE2eEnv() {
  const file = path.resolve(process.cwd(), 'e2e/.env');
  if (!fs.existsSync(file)) return;
  for (const raw of fs.readFileSync(file, 'utf8').split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq < 1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

export function authEmail() {
  return (process.env.E2E_AUTH_EMAIL || '').trim();
}

export function authPassword() {
  return process.env.E2E_AUTH_PASSWORD || '';
}

export function hasAuthCreds() {
  return Boolean(authEmail() && authPassword());
}

export function authAllowedOn(env: 'local' | 'production' | 'unknown') {
  if (!hasAuthCreds()) return false;
  if (env === 'production') return process.env.E2E_AUTH_ALLOW_PROD === '1';
  return env === 'local';
}
