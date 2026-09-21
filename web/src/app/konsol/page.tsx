"use client";

import React, { useState, useRef, useEffect } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";

type Kaynak = {
  source: string;
  authority_score: number;
  jurisdiction: string;
};

type Mesaj = {
  id: string;
  kim: "kullanici" | "sistem";
  metin: string;
  kaynaklar?: Kaynak[];
  bekliyor?: boolean;
  saniye?: number;
};

// authority_score bir GUVEN yuzdesi degil, kaynagin kademesinden turetilmis
// siralama puani. Ekranda yuzde gibi gostermiyoruz.
function kademeAdi(puan: number): string {
  if (puan >= 95) return "Kanun / AYM";
  if (puan >= 85) return "Yargıtay / Danıştay";
  if (puan >= 70) return "İstinaf";
  return "Diğer içtihat";
}

const ORNEKLER = [
  "Kıdem tazminatına esas ücrete hangi ödemeler dâhildir?",
  "İhtiyaç nedeniyle tahliye davasında altı aylık süre nasıl işler?",
  "İcra takibine itirazın iptali davasında görevli mahkeme hangisidir?",
];

export default function Home() {
  const [mesajlar, setMesajlar] = useState<Mesaj[]>([]);
  const [girdi, setGirdi] = useState("");
  const [calisiyor, setCalisiyor] = useState(false);
  const sonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (mesajlar.length) sonRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mesajlar]);

  const sor = async (soru: string) => {
    const temiz = soru.trim();
    if (!temiz || calisiyor) return;

    setCalisiyor(true);
    setGirdi("");
    const bekleyenId = crypto.randomUUID();
    setMesajlar((o) => [
      ...o,
      { id: crypto.randomUUID(), kim: "kullanici", metin: temiz },
      { id: bekleyenId, kim: "sistem", metin: "", bekliyor: true },
    ]);

    const baslangic = performance.now();
    try {
      const yanit = await fetch(`${API_PROXY}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: temiz }),
      });
      const veri = await yanit.json();
      const gecen = (performance.now() - baslangic) / 1000;
      setMesajlar((o) =>
        o.map((m) =>
          m.id === bekleyenId
            ? {
                id: bekleyenId,
                kim: "sistem",
                metin:
                  (veri.text || "Sonuç dönmedi.").replace(
                    "Arama tamamlandı. Bulunan kritik pasajlar:\n\n",
                    "",
                  ),
                kaynaklar: veri.sources || [],
                saniye: gecen,
              }
            : m,
        ),
      );
    } catch {
      setMesajlar((o) =>
        o.map((m) =>
          m.id === bekleyenId
            ? {
                id: bekleyenId,
                kim: "sistem",
                metin: "Sunucuya ulaşılamadı. Bağlantıyı kontrol edip tekrar deneyin.",
              }
            : m,
        ),
      );
    }
    setCalisiyor(false);
  };

  const dosyaYukle = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const dosya = e.target.files?.[0];
    if (!dosya || calisiyor) return;
    e.target.value = "";

    setCalisiyor(true);
    const bekleyenId = crypto.randomUUID();
    setMesajlar((o) => [
      ...o,
      {
        id: crypto.randomUUID(),
        kim: "kullanici",
        metin: `Belge: ${dosya.name} — metinde geçen konuların mevzuat karşılığı aranıyor.`,
      },
      { id: bekleyenId, kim: "sistem", metin: "", bekliyor: true },
    ]);

    const form = new FormData();
    form.append("file", dosya);
    const baslangic = performance.now();
    try {
      const yanit = await fetch(`${API_PROXY}/analyze-contract`, {
        method: "POST",
        body: form,
      });
      const veri = await yanit.json();
      setMesajlar((o) =>
        o.map((m) =>
          m.id === bekleyenId
            ? {
                id: bekleyenId,
                kim: "sistem",
                metin: veri.analysis || "Belgeden metin çıkarılamadı.",
                kaynaklar: veri.sources || [],
                saniye: (performance.now() - baslangic) / 1000,
              }
            : m,
        ),
      );
    } catch {
      setMesajlar((o) =>
        o.map((m) =>
          m.id === bekleyenId
            ? { id: bekleyenId, kim: "sistem", metin: "Belge gönderilemedi." }
            : m,
        ),
      );
    }
    setCalisiyor(false);
  };

  return (
    <>
      <Ust mod="uygulama" />
      <main className="kap" style={{ paddingTop: 40 }}>
        <h1>Hukuk külliyatında anlam tabanlı arama</h1>
        <p className="spot" style={{ marginTop: 12 }}>
          Soruyu gündelik dille yazın; motor kelime eşleşmesine değil anlama göre
          arar ve eşleşen pasajı kaynağıyla birlikte döndürür. Yorum üretmez,
          metni olduğu gibi getirir.
        </p>

        <div className="sayac">
          <div>
            <span>9.860.914</span>
            <small>yargı kararı pasajı</small>
          </div>
          <div>
            <span>8.362</span>
            <small>mevzuat pasajı (19 kanun)</small>
          </div>
        </div>
        <p className="kucuk" style={{ marginTop: -8, marginBottom: 20 }}>
          Kaynaklar: Yargıtay, Danıştay ve AYM kararları ile yürürlükteki kanun
          metinleri.
        </p>

        <section className="konsol" style={{ marginTop: 8 }}>
          <div className="konsol-ust">
            <span className="tek">arama konsolu</span>
            <span className="kucuk">
              {calisiyor ? "sorgu çalışıyor…" : "hazır"}
            </span>
          </div>

          <div className="konsol-govde">
            {mesajlar.length === 0 ? (
              <div style={{ margin: "auto 0", display: "grid", gap: 12 }}>
                <p className="kucuk">Örnek bir soruyla başlayın:</p>
                <div style={{ display: "grid", gap: 8 }}>
                  {ORNEKLER.map((o) => (
                    <button
                      key={o}
                      type="button"
                      className="dugme dugme-sade"
                      style={{ justifyContent: "flex-start", height: "auto", padding: "10px 14px" }}
                      onClick={() => sor(o)}
                    >
                      {o}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              mesajlar.map((m) =>
                m.kim === "kullanici" ? (
                  <div key={m.id} className="soru belir">
                    {m.metin}
                  </div>
                ) : (
                  <div key={m.id} className="cevap belir">
                    {m.bekliyor ? (
                      <div style={{ display: "flex", gap: 5, alignItems: "center", height: 20 }}>
                        <span className="nokta" />
                        <span className="nokta" style={{ animationDelay: ".2s" }} />
                        <span className="nokta" style={{ animationDelay: ".4s" }} />
                      </div>
                    ) : (
                      <>
                        <div className="cevap-metin">{m.metin}</div>
                        {m.kaynaklar && m.kaynaklar.length > 0 && (
                          <div className="kaynaklar">
                            {m.kaynaklar.map((k, i) => (
                              <span key={i} className="kaynak">
                                <b>{k.source}</b>
                                <em className="kademe" style={{ fontStyle: "normal" }}>
                                  {kademeAdi(k.authority_score)}
                                </em>
                              </span>
                            ))}
                          </div>
                        )}
                        {m.saniye !== undefined && (
                          <p className="kucuk" style={{ marginTop: 10 }}>
                            {m.saniye.toFixed(1)} saniyede döndü
                          </p>
                        )}
                      </>
                    )}
                  </div>
                ),
              )
            )}
            <div ref={sonRef} />
          </div>

          <div className="konsol-alt">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sor(girdi);
              }}
              style={{ display: "flex", gap: 10, alignItems: "center" }}
            >
              <input
                className="girdi"
                value={girdi}
                onChange={(e) => setGirdi(e.target.value)}
                placeholder="Sorunuzu yazın…"
                disabled={calisiyor}
              />
              <label
                className="dugme dugme-sade"
                style={{ cursor: calisiyor ? "not-allowed" : "pointer" }}
                title="PDF veya metin dosyası yükleyin; ilk 10 sayfadaki konulara karşılık gelen mevzuat aranır."
              >
                <input
                  type="file"
                  hidden
                  accept=".pdf,.txt,.doc,.docx"
                  onChange={dosyaYukle}
                  disabled={calisiyor}
                />
                Belge yükle
              </label>
              <button type="submit" className="dugme dugme-ana" disabled={calisiyor || !girdi.trim()}>
                Ara
              </button>
            </form>
          </div>
        </section>

        <p className="uyari" style={{ marginTop: 16 }}>
          Dönen metin, külliyattaki kaynağın kendi ifadesidir; motor özet veya
          hukuki değerlendirme yazmaz. Kararın güncelliğini ve olaya
          uygunluğunu kaynağından doğrulayın.
        </p>

        <section className="uclu" style={{ marginTop: 48 }}>
          <div>
            <h3>Anlam tabanlı arama</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Sorgu bir vektöre çevrilir, külliyattaki pasajlarla yakınlığına
              göre aday çıkarılır, ardından yeniden sıralanır. Aynı kavramın
              farklı kelimelerle yazıldığı kararları da bulur.
            </p>
          </div>
          <div>
            <h3>Kaynak kademesi</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Her pasaj, geldiği merciye göre etiketlenir: kanun ve AYM kararları
              içtihadın önüne alınır. Bu bir güven yüzdesi değil, sıralama
              ölçütüdür.
            </p>
          </div>
          <div>
            <h3>Belgeden mevzuata</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Yüklenen PDF&apos;in ilk 10 sayfasından metin çıkarılır ve geçen
              konuların mevzuat karşılığı aranır. Belge sunucuda saklanmaz.
            </p>
          </div>
        </section>
      </main>
      <Alt />
    </>
  );
}
