import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { getSubdomain } from './hooks/useTenantSlug';
import ApexRoutes from './app/routes/ApexRoutes';
import PublicEpkRoutes from './app/routes/PublicEpkRoutes';
import './styles/portal.css';
import './styles/epk.css';

function App() {
  const subdomain = getSubdomain();

  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      {subdomain ? <PublicEpkRoutes /> : <ApexRoutes />}
    </Router>
  );
}

export default App;
