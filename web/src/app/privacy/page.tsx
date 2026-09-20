import React from 'react';

export default function PrivacyPage() {
  return (
    <div className="container" style={{ padding: '6rem 2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem' }}>Privacy Policy</h1>
      <p className="subtitle" style={{ marginBottom: '2rem' }}>Effective Date: September 2026</p>
      
      <div style={{ color: '#94a3b8', lineHeight: 1.8 }}>
        <h2 style={{ color: '#fff', marginTop: '2rem', fontSize: '1.5rem', marginBottom: '1rem' }}>1. Data Sovereignty</h2>
        <p>LegaFetch operates on an air-gapped infrastructure model. Any legal texts, case files, or proprietary documents uploaded to your instance remain strictly on your server. We do not transmit this data to OpenAI, Anthropic, or any other third-party LLM providers.</p>
        
        <h2 style={{ color: '#fff', marginTop: '2rem', fontSize: '1.5rem', marginBottom: '1rem' }}>2. Search Queries</h2>
        <p>Your semantic search queries are processed locally using open-source embedding models (e.g., HuggingFace sentence-transformers). Query logs are stored only on your VPS and are not accessible by LegaFetch Systems.</p>
      </div>
      
      <a href="/" className="btn btn-secondary" style={{ marginTop: '3rem' }}>&larr; Back to Home</a>
    </div>
  );
}
