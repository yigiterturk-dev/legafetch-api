"use client";

import { API_PROXY } from "@/lib/api";

import React, { useState, useEffect } from 'react';

type Stats = {
  total_queries: number;
  active_api_keys: number;
  top_jurisdiction: string;
  uptime: string;
};

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    // Fetch from backend
    fetch(`${API_PROXY}/admin/stats`)
    .then(res => res.json())
    .then(data => setStats(data))
    .catch(err => console.error(err));
  }, []);

  return (
    <div className="container" style={{ padding: '2rem' }}>
      <header className="header" style={{ marginBottom: '4rem', padding: '0' }}>
        <div className="logo">LegaFetch <span style={{ color: '#d4af37' }}>ADMIN</span></div>
        <nav style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <a href="/" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.9rem' }}>&larr; Back to Console</a>
        </nav>
      </header>
      
      <main>
        <h1 style={{ fontSize: '2rem', marginBottom: '2rem' }}>API Usage & Monetization Dashboard</h1>
        
        {stats ? (
          <div className="grid-3" style={{ marginBottom: '3rem' }}>
            <div className="feature-block" style={{ borderTop: '2px solid #10b981' }}>
              <h3 style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Total API Queries (30 Days)</h3>
              <p style={{ fontSize: '2.5rem', margin: '0.5rem 0 0 0', color: '#f8fafc' }}>
                {stats.total_queries.toLocaleString()}
              </p>
              <div style={{ color: '#10b981', fontSize: '0.8rem', marginTop: '0.5rem' }}>+14.2% from last month</div>
            </div>
            
            <div className="feature-block" style={{ borderTop: '2px solid #3b82f6' }}>
              <h3 style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Active Law Firms (API Keys)</h3>
              <p style={{ fontSize: '2.5rem', margin: '0.5rem 0 0 0', color: '#f8fafc' }}>
                {stats.active_api_keys}
              </p>
              <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '0.5rem' }}>B2B Clients</div>
            </div>
            
            <div className="feature-block" style={{ borderTop: '2px solid #d4af37' }}>
              <h3 style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Most Searched Jurisdiction</h3>
              <p style={{ fontSize: '2.5rem', margin: '0.5rem 0 0 0', color: '#d4af37' }}>
                {stats.top_jurisdiction}
              </p>
              <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '0.5rem' }}>Golden Visa Searches Trending</div>
            </div>
          </div>
        ) : (
          <p style={{ color: '#94a3b8' }}>Loading secure stats...</p>
        )}

        <div style={{ background: '#0f0f11', border: '1px solid #27272a', borderRadius: '8px', padding: '2rem' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem', borderBottom: '1px solid #27272a', paddingBottom: '0.5rem' }}>Recent API Activity</h2>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', color: '#94a3b8', fontSize: '0.9rem' }}>
            <thead>
              <tr style={{ color: '#f8fafc' }}>
                <th style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>Time</th>
                <th style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>API Key</th>
                <th style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>Endpoint</th>
                <th style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>Just now</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a', fontFamily: 'monospace' }}>LGF-PRO-****</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>/api/chat</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a', color: '#10b981' }}>200 OK</td>
              </tr>
              <tr>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>2 mins ago</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a', fontFamily: 'monospace' }}>LGF-BASIC-****</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>/api/chat</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a', color: '#ef4444' }}>401 Unauthorized</td>
              </tr>
              <tr>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>5 mins ago</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a', fontFamily: 'monospace' }}>LGF-PRO-****</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a' }}>/api/analyze-contract</td>
                <td style={{ padding: '0.75rem', borderBottom: '1px solid #27272a', color: '#10b981' }}>200 OK</td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
