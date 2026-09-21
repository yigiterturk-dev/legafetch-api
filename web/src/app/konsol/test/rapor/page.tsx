"use client";

// Saha testi raporu — toplanan insan degerlendirmesinin ozeti.
// Tek metrik: "kullanilabilir oran" = (evet + duzelterek) / karar verilen.
// Otomatik hit@5 ile karistirmayin: bu, cevabin ISE YARAYIP yaramadigini
// olcer; hit@5 dogru maddenin havuzda olup olmadigini.

import React, { useEffect, useState } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";
import KonsolGezinti from "@/components/konsol-gezinti";

type Not = {
  id: string;
  alan: string;
  soru: string;
  cevap: string;
  kaynaklar: string[];
  karar: string;
  dogru_madde: string;
  notu: string;
  saniye: number;
  olusturma: string;
};

type Veri = {
  notlar: Not[];
  ozet: Record<string, number>;
  alan: Record<string, number>;
  kararli: number;
  kullanilabilir_oran: number | null;
};

const ETIKET: Record<string, string> = {
  evet: "Kullanırdım",
  duzelterek: "Düzelterek",
  hayir: "Hayır",
  arama: "Arama",
  sozlesme: "Sözleşme",
  dilekce: "Dilekçe",
  genel: "Genel",
};

export default function Rapor() {
  const [veri, setVeri] = useState<Veri | null>(null);
  const [hata, setHata] = useState("");

  useEffect(() => {
    fetch(`${API_PROXY}/test-notlari`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Sunucu ${r.status}`))))
      .then(setVeri)
      .catch((e) => setHata(e.message));
  }, []);

  return (
    <>
      <Ust mod="uygulama" />
      <KonsolGezinti />
      <main className="sarmal">
        <h1>Saha testi raporu</h1>
        {hata && <p className="hata">{hata}</p>}
        {!veri && !hata && <p className="bos">Yükleniyor…</p>}

        {veri && (
          <>
            {veri.kararli === 0 ? (
              <p className="bos">Henüz değerlendirilmiş cevap yok.</p>
            ) : (
              <div className="kartlar">
                <div className="kart one">
                  <span className="rakam">%{veri.kullanilabilir_oran}</span>
                  <span className="etiket">kullanılabilir<br />(evet + düzelterek)</span>
                </div>
                {(["evet", "duzelterek", "hayir"] as const).map((k) => (
                  <div className="kart" key={k}>
                    <span className="rakam">{veri.ozet[k] ?? 0}</span>
                    <span className="etiket">{ETIKET[k]}</span>
                  </div>
                ))}
                <div className="kart">
                  <span className="rakam">{veri.ozet.notsuz ?? 0}</span>
                  <span className="etiket">serbest not</span>
                </div>
              </div>
            )}

            <h2>Notlar</h2>
            {veri.notlar.length === 0 && <p className="bos">Kayıt yok.</p>}
            {veri.notlar.map((n) => (
              <article key={n.id} className="satir">
                <div className="ust">
                  <span className={`rozet r-${n.karar || "not"}`}>
                    {ETIKET[n.karar] || "not"}
                  </span>
                  <span className="alan">{ETIKET[n.alan] || n.alan}</span>
                  <span className="zaman">{n.olusturma.replace("T", " ").slice(0, 16)}</span>
                  {n.saniye > 0 && <span className="zaman">{n.saniye.toFixed(1)} sn</span>}
                </div>
                {n.soru && <p className="soru">{n.soru}</p>}
                {n.dogru_madde && (
                  <p className="madde">Gelmesi gereken: <strong>{n.dogru_madde}</strong></p>
                )}
                {n.notu && <p className="notu">{n.notu}</p>}
                {n.kaynaklar.length > 0 && (
                  <details>
                    <summary>Gösterilen kaynaklar ({n.kaynaklar.length})</summary>
                    <ol>{n.kaynaklar.map((k, i) => <li key={i}>{k}</li>)}</ol>
                  </details>
                )}
              </article>
            ))}
          </>
        )}
      </main>
      <Alt />

      <style jsx>{`
        .sarmal { max-width: 860px; margin: 0 auto; padding: 28px 20px 80px; }
        h1 { font-size: 1.3rem; margin: 0 0 18px; }
        h2 { font-size: 1rem; margin: 30px 0 12px; }
        .kartlar { display: flex; gap: 12px; flex-wrap: wrap; }
        .kart { border: 1px solid #e6e6ea; border-radius: 12px; padding: 16px 18px; background: #fff; min-width: 120px; display: grid; gap: 4px; }
        .kart.one { border-color: #2d2a6e; }
        .rakam { font-size: 1.6rem; font-weight: 700; color: #2d2a6e; }
        .etiket { font-size: .8rem; color: #666; line-height: 1.35; }
        .satir { border: 1px solid #e6e6ea; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; background: #fff; }
        .ust { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
        .rozet { font-size: .75rem; padding: 3px 9px; border-radius: 999px; border: 1px solid #c9c9d3; }
        .r-evet { border-color: #2e7d32; color: #2e7d32; }
        .r-duzelterek { border-color: #b26a00; color: #b26a00; }
        .r-hayir { border-color: #b3261e; color: #b3261e; }
        .alan, .zaman { font-size: .78rem; color: #888; }
        .soru { margin: 0 0 6px; font-weight: 600; }
        .madde { margin: 0 0 6px; font-size: .88rem; color: #b26a00; }
        .notu { margin: 0; white-space: pre-wrap; line-height: 1.6; color: #333; }
        details { margin-top: 8px; font-size: .82rem; color: #666; }
        ol { margin: 8px 0 0; padding-left: 20px; line-height: 1.5; }
        .bos { color: #777; }
        .hata { color: #b3261e; }
      `}</style>
    </>
  );
}
