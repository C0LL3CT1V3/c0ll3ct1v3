import React from 'react';
import ReactDOM from 'react-dom/client';
import { Auth0Provider } from '@auth0/auth0-react';
import './index.css';
import App from './App';

function readEnv(name) {
  return (process.env[name] || '').trim();
}

function isPlaceholder(value) {
  return value.includes('<') || value.includes('>') || value.toLowerCase().includes('your-');
}

const auth0Domain = readEnv('REACT_APP_AUTH0_DOMAIN');
const auth0ClientId = readEnv('REACT_APP_AUTH0_CLIENT_ID');
const auth0Audience = readEnv('REACT_APP_AUTH0_AUDIENCE');

const authErrors = [];
if (!auth0Domain || isPlaceholder(auth0Domain)) {
  authErrors.push('REACT_APP_AUTH0_DOMAIN is missing or placeholder.');
}
if (!auth0ClientId || isPlaceholder(auth0ClientId)) {
  authErrors.push('REACT_APP_AUTH0_CLIENT_ID is missing or placeholder.');
}
if (!auth0Audience || isPlaceholder(auth0Audience)) {
  authErrors.push('REACT_APP_AUTH0_AUDIENCE is missing or placeholder.');
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {authErrors.length > 0 ? (
      <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
        <h2>Auth0 configuration error</h2>
        <p>Fix these frontend environment variables and restart the app:</p>
        <ul>
          {authErrors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      </div>
    ) : (
      <Auth0Provider
        domain={auth0Domain}
        clientId={auth0ClientId}
        authorizationParams={{
          redirect_uri: window.location.origin,
          audience: auth0Audience,
          scope: process.env.REACT_APP_AUTH0_SCOPE || 'openid profile email',
        }}
        cacheLocation="memory"
        useRefreshTokens={true}
      >
        <App />
      </Auth0Provider>
    )}
  </React.StrictMode>
);
