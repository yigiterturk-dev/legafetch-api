"use client";

import React, { useState } from 'react';

export default function LoginScreen() {
  const [licenseKey, setLicenseKey] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAuthenticating(true);
    setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license: licenseKey })
      });
      if (res.ok) {
        window.location.href = '/';
        return;
      }
      setError(res.status === 401 ? 'Lisans anahtarı geçersiz.' : 'Sunucu hatası, tekrar deneyin.');
    } catch {
      setError('Sunucuya ulaşılamadı.');
    }
    setIsAuthenticating(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100 flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-slate-700 to-slate-900 border border-slate-600 flex items-center justify-center text-white font-bold text-3xl shadow-lg mb-6">
            L
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight">LegaFetch <span className="text-blue-400">PRO</span></h1>
          <p className="text-slate-400 mt-2">Hukuk Zeka Motoru — Kurumsal Giriş</p>
        </div>

        <form onSubmit={handleLogin} className="bg-slate-900/80 backdrop-blur-xl border border-slate-700 rounded-3xl p-8 shadow-2xl">
          <div className="mb-6">
            <label className="block text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Lisans Anahtarı</label>
            <input
              type="password"
              required
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
              placeholder="LGF-XXXX-XXXX-XXX"
            />
          </div>

          {error && (
            <div className="mb-4 rounded-xl bg-red-950/50 border border-red-800 text-red-400 text-sm font-medium px-4 py-3">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isAuthenticating}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-4 rounded-xl shadow-lg transition-all flex justify-center items-center gap-2"
          >
            {isAuthenticating ? 'Yetkilendiriliyor...' : 'Sisteme Giriş Yap'}
          </button>
        </form>
      </div>
    </div>
  );
}
