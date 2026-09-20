import React from 'react';

export default function DocumentationPage() {
  return (
    <div className="container" style={{ padding: '6rem 2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem' }}>API Documentation</h1>
      <p className="subtitle">Integrate LegaFetch semantic search into your own legal applications using our REST API.</p>
      
      <div className="console-window" style={{ marginTop: '3rem' }}>
        <div className="console-header">POST /api/chat</div>
        <div className="console-body" style={{ minHeight: 'auto', padding: '1.5rem' }}>
          <pre style={{ color: '#e2e8f0', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.9rem' }}>
{`// Request
POST https://api.legafetch.com/api/chat
Content-Type: application/json

{
  "query": "Anonim şirket asgari sermaye"
}

// Response
{
  "text": "Arama tamamlandı...",
  "sources": ["TR_COMMERCIAL_CODE_332_LOCAL"]
}`}
          </pre>
        </div>
      </div>
      <a href="/" className="btn btn-secondary" style={{ marginTop: '3rem' }}>&larr; Back to Home</a>
    </div>
  );
}
