import React from "react";

export default function Ust({ mod = "acik" }: { mod?: "acik" | "uygulama" }) {
  return (
    <header className="ust">
      <div className="kap ust-ic">
        <a href={mod === "uygulama" ? "/konsol" : "/"} className="marka">
          LegaFetch <span>beta</span>
        </a>
        <nav className="ust-gezinti">
          <a href="/documentation">API</a>
          <a href="/infrastructure">Altyapı</a>
          {mod === "uygulama" ? (
            <>
              <a href="/admin">Yönetim</a>
              <form action="/api/auth/logout" method="post">
                <button type="submit" className="dugme dugme-yazi">
                  Çıkış
                </button>
              </form>
            </>
          ) : (
            <a href="/login" className="dugme dugme-sade">
              Giriş yap
            </a>
          )}
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
