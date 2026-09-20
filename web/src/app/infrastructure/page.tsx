import React from 'react';

export default function InfrastructurePage() {
  return (
    <div className="container" style={{ padding: '6rem 2rem' }}>
      <h1 style={{ marginBottom: '2rem' }}>Infrastructure Details</h1>
      <p className="subtitle" style={{ marginBottom: '2rem' }}>LegaFetch is built on a scalable, air-gapped architecture designed specifically for legal data.</p>
      
      <div className="features grid-3" style={{ borderTop: 'none', paddingTop: 0 }}>
        <div className="feature-block">
          <h3>Vector Database (Qdrant)</h3>
          <p>Our core relies on Qdrant, a Rust-based vector engine that ensures sub-50ms latency for millions of legal documents. It runs 100% locally on your VPS, ensuring no external data leakage.</p>
        </div>
        <div className="feature-block">
          <h3>Semantic Embeddings</h3>
          <p>We utilize localized, offline embedding models (e.g., all-MiniLM) to tokenize and vectorize Turkish and Spanish legal texts without relying on third-party APIs.</p>
        </div>
        <div className="feature-block">
          <h3>API Layer (FastAPI)</h3>
          <p>A highly concurrent Python backend handles incoming queries, bridging the gap between the Next.js frontend and the Qdrant database seamlessly.</p>
        </div>
      </div>
      <a href="/" className="btn btn-secondary" style={{ marginTop: '3rem' }}>&larr; Back to Home</a>
    </div>
  );
}
