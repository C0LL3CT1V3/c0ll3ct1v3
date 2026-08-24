import React from 'react';
import { Route, Routes } from 'react-router-dom';
import ArtistProfilePage from '../../features/profile/ArtistProfilePage';
import BookerEpkPage from '../../features/profile/BookerEpkPage';
import ArtistHomebasePage from '../../features/homebase/ArtistHomebasePage';

function PublicEpkRoutes() {
  return (
    <Routes>
      <Route path="/epk" element={<BookerEpkPage />} />
      <Route path="/epk/*" element={<BookerEpkPage />} />
      <Route path="/homebase" element={<ArtistHomebasePage />} />
      <Route path="/homebase/*" element={<ArtistHomebasePage />} />
      <Route path="/" element={<ArtistProfilePage />} />
    </Routes>
  );
}

export default PublicEpkRoutes;
