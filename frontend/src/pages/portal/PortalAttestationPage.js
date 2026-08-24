import React from 'react';
import AttestationStudio from '../../features/attestation/AttestationStudio';

function PortalAttestationPage() {
  return (
    <div className="portal-studio portal-studio--attest">
      <header className="portal-section-header">
        <h1 className="portal-section-title">Attestation</h1>
        <p className="portal-section-lead">
          We pull drafts from public registries and your own exports. You confirm or correct each
          claim — that confirmation is the signed record machines will see.
        </p>
      </header>
      <AttestationStudio />
    </div>
  );
}

export default PortalAttestationPage;
