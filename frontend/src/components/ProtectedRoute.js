import React, { useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useLocation } from 'react-router-dom';

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  const location = useLocation();
  const shouldRedirect = !isLoading && !isAuthenticated;

  useEffect(() => {
    if (!shouldRedirect) {
      return;
    }
    loginWithRedirect({
      appState: { returnTo: `${location.pathname}${location.search}` },
      authorizationParams: {
        redirect_uri: window.location.origin,
      },
    });
  }, [shouldRedirect, location.pathname, loginWithRedirect]);

  if (isLoading) {
    return <div className="App">Loading authentication...</div>;
  }

  if (shouldRedirect) {
    return <div className="App">Redirecting to login...</div>;
  }

  return children;
}

export default ProtectedRoute;
