import { useMemo } from 'react';
import axios from 'axios';
import { useAuth0 } from '@auth0/auth0-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';
const AUTH0_AUDIENCE = process.env.REACT_APP_AUTH0_AUDIENCE;
const AUTH0_SCOPE = process.env.REACT_APP_AUTH0_SCOPE || 'openid profile email';
const AUTH0_MFA_ACR = process.env.REACT_APP_AUTH0_MFA_ACR || 'http://schemas.openid.net/pape/policies/2007/06/multi-factor';

function isMfaError(error) {
  return error?.response?.status === 403
    && ['mfa_required', 'mfa_reauthentication_required'].includes(error?.response?.data?.detail);
}

async function attachAccessToken(getAccessTokenSilently, config) {
  const token = await getAccessTokenSilently({
    authorizationParams: {
      audience: AUTH0_AUDIENCE,
      scope: AUTH0_SCOPE,
    },
  });
  config.headers = config.headers || {};
  config.headers.Authorization = `Bearer ${token}`;
  return config;
}

/**
 * Axios client with Auth0 bearer tokens.
 * Interceptors are registered in useMemo so the first request after login includes auth
 * (useEffect-based interceptors race child components that fetch on mount).
 */
export function useApiClient() {
  const { getAccessTokenSilently, loginWithPopup, isAuthenticated, isLoading } = useAuth0();

  const apiClient = useMemo(() => {
    const client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    client.interceptors.request.use(async (config) => attachAccessToken(getAccessTokenSilently, config));

    client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config || {};

        if (error?.response?.status === 401 && !originalRequest.__authRetry) {
          originalRequest.__authRetry = true;
          try {
            await attachAccessToken(getAccessTokenSilently, originalRequest);
            return client(originalRequest);
          } catch {
            /* fall through */
          }
        }

        if (isMfaError(error) && !originalRequest.__mfaRetry) {
          originalRequest.__mfaRetry = true;
          await loginWithPopup({
            authorizationParams: {
              audience: AUTH0_AUDIENCE,
              scope: AUTH0_SCOPE,
              acr_values: AUTH0_MFA_ACR,
              prompt: 'login',
            },
          });
          await attachAccessToken(getAccessTokenSilently, originalRequest);
          return client(originalRequest);
        }

        return Promise.reject(error);
      },
    );

    return client;
  }, [getAccessTokenSilently, loginWithPopup]);

  const authReady = isAuthenticated && !isLoading;

  return { apiClient, authReady };
}
