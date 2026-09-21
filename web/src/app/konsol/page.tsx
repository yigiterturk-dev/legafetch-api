"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";
import KonsolGezinti from "@/components/konsol-gezinti";
import DosyayaKaydet from "@/components/dosyaya-kaydet";
import Secici from "@/components/secici";
import KaynakKarti, { Kaynak } from "@/components/kaynak-paneli";

type Mesaj = {
  id: string;
  kim: "kullanici" | "sistem";
  metin: string;
  kaynaklar?: Kaynak[];
  bekliyor?: boolean;
  saniye?: number;
};

// Qdrant payload'ındaki "tur" alanı (indeksli). Sayılar 2026-09-21 facet
// ölçümü. "jurisdiction" diye bir alan YOK — ülke süzgeci kurulamaz.
const TUR_SECENEKLERI = [
  { deger: "", etiket: "Tüm kaynaklar", ipucu: "9,87M" },
  { deger: "Yargıtay kararı", etiket: "Yargıtay", ipucu: "4,22M" },
  { deger: "Danıştay kararı", etiket: "Danıştay", ipucu: "1,65M" },
  { deger: "AYM kararı", etiket: "AYM", ipucu: "242K" },
  { deger: "içtihat", etiket: "Yerel / istinaf", ipucu: "3,74M" },
  { deger: "kanun", etiket: "Kanun metni", ipucu: "8.392" },
];

const ORNEKLER = [
  "Kıdem tazminatına esas ücrete hangi ödemeler dâhildir?",
  "İhtiyaç nedeniyle tahliye davasında altı aylık süre nasıl işler?",
  "İcra takibine itirazın iptali davasında görevli mahkeme hangisidir?",
];

const GECMIS_ANAHTAR = "legafetch_sorgu_gecmisi";
const GECMIS_SINIR = 8;

/** Cevap metnini [n] atıflarında böler; atıflar ilgili kaynak kartına kaydırır. */
function AtifliMetin({ metin, mesajId }: { metin: string; mesajId: string }) {
  const parcalar = metin.split(/(\[\d{1,2}\])/g);
  return (
    <div className="cevap-metin">
      {parcalar.map((p, i) => {
        const m = /^\[(\d{1,2})\]$/.exec(p);
        if (!m) return <React.Fragment key={i}>{p}</React.Fragment>;
        const no = m[1];
        return (
          <button
            key={i}
            type="button"
            className="atif tek"
            title={`Kaynak ${no}'e git`}
            onClick={() => {
              const hedef = document.getElementById(`k-${mesajId}-${no}`);
              if (!hedef) return;
              hedef.scrollIntoView({ behavior: "smooth", block: "center" });
              hedef.classList.add("kaynak-vurgu");
              setTimeout(() => hedef.classList.remove("kaynak-vurgu"), 1400);
            }}
          >
            [{no}]
          </button>
        );
      })}
    </div>
  );
}

export default function Home() {
  const [mesajlar, setMesajlar] = useState<Mesaj[]>([]);
  const [girdi, setGirdi] = useState("");
  const [calisiyor, setCalisiyor] = useState(false);
  const [tur, setTur] = useState("");
  const [tarihBas, setTarihBas] = useState("");
  const [tarihSon, setTarihSon] = useState("");
  const [gecmis, setGecmis] = useState<string[]>([]);
  const sonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const ham = localStorage.getItem(GECMIS_ANAHTAR);
      if (ham) setGecmis(JSON.parse(ham));
    } catch {
      /* özel pencere / kapalı depolama: geçmişsiz çalış */
    }
  }, []);

  useEffect(() => {
    if (mesajlar.length) sonRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mesajlar]);

  const gecmiseYaz = useCallback((soru: string) => {
    setGecmis((o) => {
      const yeni = [soru, ...o.filter((s) => s !== soru)].slice(0, GECMIS_SINIR);
      try {
        localStorage.setItem(GECMIS_ANAHTAR, JSON.stringify(yeni));
      } catch {
        /* yoksay */
      }
      return yeni;
    });
  }, []);

  const suzgecAcik = Boolean(tur || tarihBas || tarihSon);

  const sor = async (soru: string) => {
    const temiz = soru.trim();
    if (!temiz || calisiyor) return;

    setCalisiyor(true);
    setGirdi("");
    gecmiseYaz(temiz);
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
        body: JSON.stringify({
          query: temiz,
          tur: tur || null,
          tarih_bas: tarihBas || null,
          tarih_son: tarihSon || null,
        }),
      });
      const veri = await yanit.json();
      const gecen = (performance.now() - baslangic) / 1000;
      // Cevabın sonundaki düz "Kaynaklar:" listesi artık kartlarla
      // gösteriliyor; metinde ikinci kez tekrarlamasın.
      const metin = (veri.text || "Sonuç dönmedi.")
        .replace(/\n+Kaynaklar:\n[\s\S]*$/, "")
        .trim();
      setMesajlar((o) =>
        o.map((m) =>
          m.id === bekleyenId
            ? {
                id: bekleyenId,
                kim: "sistem",
                metin,
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

  return (
    <>
      <Ust mod="uygulama" />
      <main className="kap" style={{ paddingTop: 32 }}>
        <KonsolGezinti />
        <h1 style={{ marginTop: 22 }}>Hukuk külliyatında anlam tabanlı arama</h1>
        <p className="spot" style={{ marginTop: 12 }}>
          Soruyu gündelik dille yazın; motor kelime eşleşmesine değil anlama göre
          arar, bulduğu pasajlardan atıflı bir cevap çıkarır ve kullandığı
          pasajların tam metnini altına açar.
        </p>

        <section className="konsol" style={{ marginTop: 24 }}>
          <div className="konsol-ust">
            <span className="tek">arama konsolu</span>
            <div className="suzgec-bar">
              <Secici
                baslik="Kaynak türü"
                deger={tur}
                secenekler={TUR_SECENEKLERI}
                onSec={setTur}
              />
              <label className="tarih-alan">
                <span className="kucuk">tarih</span>
                <input
                  type="date"
                  className="girdi girdi-kucuk"
                  value={tarihBas}
                  max={tarihSon || undefined}
                  onChange={(e) => setTarihBas(e.target.value)}
                  aria-label="Başlangıç tarihi"
                />
                <span className="kucuk">–</span>
                <input
                  type="date"
                  className="girdi girdi-kucuk"
                  value={tarihSon}
                  min={tarihBas || undefined}
                  onChange={(e) => setTarihSon(e.target.value)}
                  aria-label="Bitiş tarihi"
                />
              </label>
              {suzgecAcik && (
                <button
                  type="button"
                  className="dugme-yazi"
                  onClick={() => {
                    setTur("");
                    setTarihBas("");
                    setTarihSon("");
                  }}
                >
                  süzgeci temizle
                </button>
              )}
              <span className="kucuk">
                {calisiyor ? "sorgu çalışıyor…" : "hazır"}
              </span>
            </div>
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
                        <AtifliMetin metin={m.metin} mesajId={m.id} />
                        {m.kaynaklar && m.kaynaklar.length > 0 && (
                          <div className="kaynaklar">
                            <p className="kucuk" style={{ marginBottom: 10 }}>
                              Kullanılan {m.kaynaklar.length} pasaj — başlığa
                              tıklayınca tam metni açılır.
                            </p>
                            <div style={{ display: "grid", gap: 8 }}>
                              {m.kaynaklar.map((k, i) => (
                                <KaynakKarti
                                  key={`${m.id}-${i}`}
                                  kaynak={k}
                                  no={i + 1}
                                  kimlik={`k-${m.id}-${i + 1}`}
                                />
                              ))}
                            </div>
                          </div>
                        )}
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 12,
                            marginTop: 12,
                            flexWrap: "wrap",
                          }}
                        >
                          <DosyayaKaydet
                            tur="sorgu"
                            baslik={
                              mesajlar.find(
                                (x, i) =>
                                  x.kim === "kullanici" &&
                                  mesajlar[i + 1]?.id === m.id,
                              )?.metin ?? "Arama"
                            }
                            icerik={m.metin}
                            veri={{ kaynaklar: m.kaynaklar ?? [] }}
                          />
                          {m.saniye !== undefined && (
                            <span className="kucuk">
                              {m.saniye.toFixed(1)} saniyede döndü
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                ),
              )
            )}
            <div ref={sonRef} />
          </div>

          <div className="konsol-alt">
            {gecmis.length > 0 && (
              <div className="gecmis">
                <span className="kucuk">son sorgular</span>
                {gecmis.map((g) => (
                  <button
                    key={g}
                    type="button"
                    className="gecmis-oge"
                    title={g}
                    onClick={() => sor(g)}
                    disabled={calisiyor}
                  >
                    {g.length > 42 ? `${g.slice(0, 42)}…` : g}
                  </button>
                ))}
                <button
                  type="button"
                  className="dugme-yazi"
                  onClick={() => {
                    setGecmis([]);
                    try {
                      localStorage.removeItem(GECMIS_ANAHTAR);
                    } catch {
                      /* yoksay */
                    }
                  }}
                >
                  temizle
                </button>
              </div>
            )}
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
              <button type="submit" className="dugme dugme-ana" disabled={calisiyor || !girdi.trim()}>
                Ara
              </button>
            </form>
          </div>
        </section>

        <p className="uyari" style={{ marginTop: 16 }}>
          Cevabı bir dil modeli, yalnızca aşağıda listelenen pasajlara
          dayanarak yazar — atıflar bu yüzden önemli. Sorgunuz ve seçilen
          pasajlar bu adımda OpenAI&apos;ye gönderilir. Metni kullanmadan önce
          kaynağını açıp doğrulayın; hukuki değerlendirme yerine geçmez.
        </p>

        <div className="sayac" style={{ marginTop: 32 }}>
          <div>
            <span>9.860.914</span>
            <small>yargı kararı pasajı</small>
          </div>
          <div>
            <span>8.362</span>
            <small>mevzuat pasajı (19 kanun)</small>
          </div>
        </div>

        <section className="uclu" style={{ marginTop: 40 }}>
          <div>
            <h3>Süzgeçler</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Kaynak türü ve karar tarihi, aramanın kendisinde uygulanır —
              sonuçlar sonradan kırpılmaz, aday havuzu baştan daraltılır.
              Külliyatta ülke/yargı yeri alanı bulunmadığı için ülke süzgeci yok.
            </p>
          </div>
          <div>
            <h3>Pasajın tam metni</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Her kaynak açılır: modelin gördüğü pasaj metni, esas ve karar
              numarası, daire ve tarih. Cevaptaki [n] atıfına tıklayınca ilgili
              kaynağa gider. &quot;Atıf kopyala&quot; dilekçeye hazır biçimde panoya alır.
            </p>
          </div>
          <div>
            <h3>Kaynak kademesi</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Her pasaj geldiği merciye göre etiketlenir: kanun ve AYM kararları
              içtihadın önüne alınır. Bu bir güven yüzdesi değil, sıralama
              ölçütüdür.
            </p>
          </div>
        </section>
      </main>
      <Alt />
    </>
  );
}
