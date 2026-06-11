import React from 'react';
import { Route, Routes } from 'react-router-dom';
import ArtistProfilePage from '../../features/profile/ArtistProfilePage';
import BookerEpkPage from '../../features/profile/BookerEpkPage';

function PublicEpkRoutes() {
  return (
    <Routes>
      <Route path="/epk" element={<BookerEpkPage />} />
      <Route path="*" element={<ArtistProfilePage />} />
    </Routes>
  );
}

export default PublicEpkRoutes;
