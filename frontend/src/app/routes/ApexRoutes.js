import React from 'react';
import { Route, Routes } from 'react-router-dom';
import MarketingLanding from '../../pages/marketing/MarketingLanding';
import PortalShell from '../../pages/portal/PortalShell';
import ProtectedRoute from '../../components/ProtectedRoute';

function ApexRoutes() {
  return (
    <Routes>
      <Route path="/" element={<MarketingLanding />} />
      <Route
        path="/portal/*"
        element={
          <ProtectedRoute>
            <PortalShell />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default ApexRoutes;
