import React from 'react';

export default function TermsPage() {
  return (
    <div className="container" style={{ padding: '6rem 2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem' }}>Terms of Service</h1>
      <p className="subtitle" style={{ marginBottom: '2rem' }}>Welcome to LegaFetch Data Infrastructure.</p>
      
      <div style={{ color: '#94a3b8', lineHeight: 1.8 }}>
        <p>By using the LegaFetch engine, you agree to deploy the system on authorized hardware and maintain compliance with local data protection regulations (such as KVKK in Turkey and GDPR in Spain).</p>
        <p style={{ marginTop: '1rem' }}>LegaFetch provides the semantic search software "as is", without warranty of any kind. You are responsible for the legal validity of the documents you index in the Qdrant database.</p>
      </div>
      
      <a href="/" className="btn btn-secondary" style={{ marginTop: '3rem' }}>&larr; Back to Home</a>
    </div>
  );
}
