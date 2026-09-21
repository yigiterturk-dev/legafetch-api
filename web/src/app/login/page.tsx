"use client";

import React, { useState } from "react";

export default function GirisEkrani() {
  const [anahtar, setAnahtar] = useState("");
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [hata, setHata] = useState("");

  const girisYap = async (e: React.FormEvent) => {
    e.preventDefault();
    setGonderiliyor(true);
    setHata("");
    try {
      const yanit = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ license: anahtar }),
      });
      if (yanit.ok) {
        window.location.href = "/konsol";
        return;
      }
      setHata(
        yanit.status === 401
          ? "Lisans anahtarı geçersiz."
          : yanit.status === 429
            ? "Çok fazla deneme yapıldı. Bir dakika sonra tekrar deneyin."
            : "Sunucu hatası. Tekrar deneyin.",
      );
    } catch {
      setHata("Sunucuya ulaşılamadı.");
    }
    setGonderiliyor(false);
  };

  return (
    <main
      style={{
        minHeight: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
      }}
    >
      <div style={{ width: "100%", maxWidth: 380 }}>
        <a href="/" className="marka" style={{ marginBottom: 24 }}>
          LegaFetch <span>beta</span>
        </a>

        <h1 style={{ fontSize: 24, marginTop: 20 }}>Lisans anahtarıyla giriş</h1>
        <p className="kucuk" style={{ marginTop: 8 }}>
          Erişim, kuruma verilen anahtarla açılır. Anahtar tarayıcıda saklanmaz;
          oturum imzalı bir çerezle taşınır.
        </p>

        <form onSubmit={girisYap} className="kart kart-dolgu" style={{ marginTop: 20 }}>
          <label className="etiket" htmlFor="lisans">
            Lisans anahtarı
          </label>
          <input
            id="lisans"
            className="girdi tek"
            spellCheck={false}
            type="password"
            required
            autoFocus
            autoComplete="off"
            value={anahtar}
            onChange={(e) => setAnahtar(e.target.value)}
            placeholder="Size verilen anahtarı yapıştırın"
          />

          {hata && (
            <p className="uyari" style={{ marginTop: 12 }}>
              {hata}
            </p>
          )}

          <button
            type="submit"
            className="dugme dugme-ana"
            style={{ width: "100%", marginTop: 16 }}
            disabled={gonderiliyor || !anahtar.trim()}
          >
            {gonderiliyor ? "Doğrulanıyor…" : "Giriş yap"}
          </button>
        </form>

        <p className="kucuk" style={{ marginTop: 16 }}>
          Anahtarınız yoksa{" "}
          <a href="mailto:iletisim@legafetch.com" style={{ color: "var(--marka)" }}>
            iletisim@legafetch.com
          </a>{" "}
          adresine yazın.
        </p>
      </div>
    </main>
  );
}
