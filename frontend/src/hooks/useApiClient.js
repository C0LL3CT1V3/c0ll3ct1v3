import { useEffect, useMemo } from 'react';
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

export function useApiClient() {
  const { getAccessTokenSilently, loginWithPopup } = useAuth0();

  const apiClient = useMemo(() => {
    return axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }, []);

  useEffect(() => {
    const requestInterceptor = apiClient.interceptors.request.use(async (config) => {
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: AUTH0_AUDIENCE,
          scope: AUTH0_SCOPE,
        },
      });
      config.headers.Authorization = `Bearer ${token}`;
      return config;
    });

    const responseInterceptor = apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config || {};
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
          const refreshedToken = await getAccessTokenSilently({
            authorizationParams: {
              audience: AUTH0_AUDIENCE,
              scope: AUTH0_SCOPE,
            },
          });
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${refreshedToken}`;
          return apiClient(originalRequest);
        }
        return Promise.reject(error);
      },
    );

    return () => {
      apiClient.interceptors.request.eject(requestInterceptor);
      apiClient.interceptors.response.eject(responseInterceptor);
    };
  }, [apiClient, getAccessTokenSilently, loginWithPopup]);

  return apiClient;
}

