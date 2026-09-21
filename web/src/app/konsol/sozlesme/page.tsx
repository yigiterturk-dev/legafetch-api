"use client";

import React, { useState } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";
import KonsolGezinti from "@/components/konsol-gezinti";
import KaynakKarti, { Kaynak } from "@/components/kaynak-paneli";
import DosyayaKaydet from "@/components/dosyaya-kaydet";

type Risk = { madde: string; bulgu: string; onem: string; dayanak: number[] };
type Analiz = {
  filename: string;
  status: string;
  tur: string;
  ozet: string;
  riskler: Risk[];
  eksikler: string[];
  analysis: string;
  karakter: number;
  sources: Kaynak[];
  uyari: string;
};

const ONEM_SIRA: Record<string, number> = { yuksek: 0, orta: 1, dusuk: 2 };

export default function SozlesmePage() {
  const [calisiyor, setCalisiyor] = useState(false);
  const [sonuc, setSonuc] = useState<Analiz | null>(null);
  const [hata, setHata] = useState("");
  const [dosyaAdi, setDosyaAdi] = useState("");
  const [saniye, setSaniye] = useState<number | null>(null);

  const yukle = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const dosya = e.target.files?.[0];
    if (!dosya || calisiyor) return;
    e.target.value = "";
    setCalisiyor(true);
    setHata("");
    setSonuc(null);
    setDosyaAdi(dosya.name);
    const form = new FormData();
    form.append("file", dosya);
    const t0 = performance.now();
    try {
      const yanit = await fetch(`${API_PROXY}/analyze-contract`, { method: "POST", body: form });
      if (!yanit.ok) throw new Error(String(yanit.status));
      setSonuc(await yanit.json());
      setSaniye((performance.now() - t0) / 1000);
    } catch {
      setHata("Belge gönderilemedi veya analiz zaman aşımına uğradı.");
    }
    setCalisiyor(false);
  };

  const riskler = [...(sonuc?.riskler ?? [])].sort(
    (a, b) => (ONEM_SIRA[a.onem] ?? 1) - (ONEM_SIRA[b.onem] ?? 1),
  );

  return (
    <>
      <Ust mod="uygulama" />
      <main className="kap" style={{ paddingTop: 32, paddingBottom: 48 }}>
        <KonsolGezinti />
        <h1 style={{ marginTop: 22 }}>Sözleşme denetimi</h1>
        <p className="spot" style={{ marginTop: 10 }}>
          PDF, Word veya düz metin yükleyin. Metin çıkarılır, konusuyla eşleşen
          mevzuat ve içtihat çekilir, ardından sözleşme <b>yalnızca o
          pasajlara</b> yaslanarak denetlenir: riskli maddeler sözleşmeden
          alıntıyla, eksik maddeler ayrı listede gösterilir.
        </p>

        <div style={{ marginTop: 20, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label className="dugme dugme-ana" style={{ cursor: calisiyor ? "not-allowed" : "pointer" }}>
            <input
              type="file"
              hidden
              accept=".pdf,.txt,.docx,.md"
              onChange={yukle}
              disabled={calisiyor}
            />
            {calisiyor ? "inceleniyor…" : "Sözleşme yükle"}
          </label>
          {dosyaAdi && <span className="kucuk">{dosyaAdi}</span>}
          {saniye !== null && !calisiyor && (
            <span className="kucuk">{saniye.toFixed(1)} saniyede döndü</span>
          )}
        </div>

        <p className="uyari" style={{ marginTop: 14 }}>
          Yüklediğiniz belgenin metni ve seçilen pasajlar denetim için
          OpenAI&apos;ye gönderilir. Belge sunucuda saklanmaz. Çıktı taslaktır,
          hukuki görüş değildir.
        </p>

        {hata && <p className="uyari" style={{ marginTop: 16 }}>{hata}</p>}

        {sonuc && (
          <section style={{ marginTop: 26, display: "grid", gap: 18 }}>
            {sonuc.status !== "success" && <p className="uyari">{sonuc.analysis}</p>}
            {sonuc.uyari && <p className="uyari">{sonuc.uyari}</p>}

            {sonuc.ozet && (
              <div className="kart kart-dolgu">
                <div className="kaynak-meta" style={{ marginTop: 0, marginBottom: 8 }}>
                  {sonuc.tur && <span className="kademe">{sonuc.tur}</span>}
                  <span className="tek">{sonuc.karakter.toLocaleString("tr-TR")} karakter okundu</span>
                </div>
                <p style={{ fontSize: 14.5, lineHeight: 1.7 }}>{sonuc.ozet}</p>
                <div style={{ marginTop: 12 }}>
                  <DosyayaKaydet
                    tur="analiz"
                    baslik={`Sözleşme denetimi — ${sonuc.filename}`}
                    veri={sonuc}
                  />
                </div>
              </div>
            )}

            {riskler.length > 0 && (
              <div>
                <h3>Riskli görülen {riskler.length} nokta</h3>
                <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                  {riskler.map((r, i) => (
                    <div key={i} className={`risk risk-${["yuksek", "orta", "dusuk"].includes(r.onem) ? r.onem : "orta"}`}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                        <b style={{ fontSize: 14 }}>{r.bulgu}</b>
                        <span className="kucuk tek" style={{ flex: "none" }}>
                          {r.onem === "yuksek" ? "yüksek" : r.onem === "dusuk" ? "düşük" : "orta"}
                        </span>
                      </div>
                      {r.madde && <div className="risk-alinti">“{r.madde}”</div>}
                      {r.dayanak.length > 0 && (
                        <div className="kaynak-meta">
                          dayanak:{" "}
                          {r.dayanak.map((n) => (
                            <span key={n} className="tek">[{n}]</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {sonuc.eksikler.length > 0 && (
              <div>
                <h3>Sözleşmede bulunmayan, beklenen maddeler</h3>
                {sonuc.uyari && (
                  <p className="uyari" style={{ marginTop: 8 }}>
                    Bu liste yalnızca incelenen bölüme göredir; kırpılan
                    sayfalarda yer alan maddeler burada &quot;eksik&quot;
                    görünebilir.
                  </p>
                )}
                <ul style={{ paddingLeft: 20, marginTop: 10, fontSize: 14, lineHeight: 1.8 }}>
                  {sonuc.eksikler.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            )}

            {sonuc.sources.length > 0 && (
              <div>
                <p className="kucuk" style={{ marginBottom: 10 }}>
                  Denetimin dayandığı {sonuc.sources.length} pasaj:
                </p>
                <div style={{ display: "grid", gap: 8 }}>
                  {sonuc.sources.map((k, i) => (
                    <KaynakKarti key={i} kaynak={k} no={i + 1} kimlik={`s-${i + 1}`} />
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </main>
      <Alt />
    </>
  );
}
