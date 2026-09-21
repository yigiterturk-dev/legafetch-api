import React from "react";

export default function Ust() {
  return (
    <header className="ust">
      <div className="kap ust-ic">
        <a href="/" className="marka">
          LegaFetch <span>beta</span>
        </a>
        <nav className="ust-gezinti">
          <a href="/documentation">API</a>
          <a href="/infrastructure">Altyapı</a>
          <a href="/admin">Yönetim</a>
        </nav>
      </div>
    </header>
  );
}

export function Alt() {
  return (
    <footer className="kap alt">
      <span>
        LegaFetch — Türk hukuk külliyatında anlam tabanlı arama. Sonuçlar ham
        kaynak pasajıdır, hukuki görüş değildir.
      </span>
      <span style={{ display: "flex", gap: 16 }}>
        <a href="/terms">Kullanım koşulları</a>
        <a href="/privacy">Gizlilik</a>
      </span>
    </footer>
  );
}
