import React from 'react';
import { Route, Routes } from 'react-router-dom';
import ArtistEpkPage from '../../pages/epk/ArtistEpkPage';

function PublicEpkRoutes() {
  return (
    <Routes>
      <Route path="*" element={<ArtistEpkPage />} />
    </Routes>
  );
}

export default PublicEpkRoutes;
