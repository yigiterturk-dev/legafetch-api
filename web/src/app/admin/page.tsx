"use client";

import React, { useEffect, useState } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";

type Ozet = {
  total_queries: number;
  breakdown: Record<string, number>;
  active_api_keys: number;
  vector_count: number;
  uptime_hours: number;
};

export default function YonetimSayfasi() {
  const [ozet, setOzet] = useState<Ozet | null>(null);
  const [hata, setHata] = useState("");

  useEffect(() => {
    fetch(`${API_PROXY}/admin/stats`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setOzet)
      .catch(() => setHata("Özet alınamadı."));
  }, []);

  const sayi = (n: number) => n.toLocaleString("tr-TR");

  return (
    <>
      <Ust mod="uygulama" />
      <main className="kap" style={{ paddingTop: 40 }}>
        <h1>Yönetim</h1>
        <p className="spot" style={{ marginTop: 12 }}>
          Sayaçlar API süreci başladığından beri sayar; süreç yeniden başlarsa
          sıfırlanır. Kalıcı kullanım geçmişi tutulmuyor.
        </p>

        {hata && (
          <p className="uyari" style={{ marginTop: 20 }}>
            {hata}
          </p>
        )}

        {!ozet && !hata && (
          <p className="kucuk" style={{ marginTop: 20 }}>
            Yükleniyor…
          </p>
        )}

        {ozet && (
          <>
            <div className="uclu" style={{ marginTop: 24 }}>
              <div className="kart kart-dolgu">
                <h3 className="kucuk">Süreç başından beri sorgu</h3>
                <p className="tek" style={{ fontSize: 28, marginTop: 6 }}>
                  {sayi(ozet.total_queries)}
                </p>
              </div>
              <div className="kart kart-dolgu">
                <h3 className="kucuk">Külliyattaki pasaj</h3>
                <p className="tek" style={{ fontSize: 28, marginTop: 6 }}>
                  {sayi(ozet.vector_count)}
                </p>
              </div>
              <div className="kart kart-dolgu">
                <h3 className="kucuk">Ayakta kalma</h3>
                <p className="tek" style={{ fontSize: 28, marginTop: 6 }}>
                  {ozet.uptime_hours.toLocaleString("tr-TR", {
                    maximumFractionDigits: 1,
                  })}{" "}
                  saat
                </p>
              </div>
              <div className="kart kart-dolgu">
                <h3 className="kucuk">Tanımlı lisans anahtarı</h3>
                <p className="tek" style={{ fontSize: 28, marginTop: 6 }}>
                  {sayi(ozet.active_api_keys)}
                </p>
                <p className="kucuk" style={{ marginTop: 4 }}>
                  Çok kiracılı yapı yok; tek anahtar.
                </p>
              </div>
            </div>

            <h2 style={{ marginTop: 36 }}>Uç nokta dağılımı</h2>
            {Object.keys(ozet.breakdown || {}).length === 0 ? (
              <p className="kucuk" style={{ marginTop: 10 }}>
                Süreç başladığından beri kayıtlı istek yok.
              </p>
            ) : (
              <div className="kart" style={{ marginTop: 12, overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                  <thead>
                    <tr style={{ background: "var(--yuzey)" }}>
                      <th style={{ textAlign: "left", padding: "10px 16px", fontWeight: 560 }}>
                        Uç nokta
                      </th>
                      <th style={{ textAlign: "right", padding: "10px 16px", fontWeight: 560 }}>
                        İstek
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(ozet.breakdown).map(([yol, adet]) => (
                      <tr key={yol} style={{ borderTop: "1px solid var(--kenar)" }}>
                        <td className="tek" style={{ padding: "10px 16px" }}>
                          {yol}
                        </td>
                        <td className="tek" style={{ padding: "10px 16px", textAlign: "right" }}>
                          {sayi(adet)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </main>
      <Alt />
    </>
  );
}
