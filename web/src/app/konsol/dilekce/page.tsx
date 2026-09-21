"use client";

import React, { useState } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";
import KonsolGezinti from "@/components/konsol-gezinti";
import Secici from "@/components/secici";
import KaynakKarti, { Kaynak } from "@/components/kaynak-paneli";
import DosyayaKaydet from "@/components/dosyaya-kaydet";

type Dilekce = {
  tur: string;
  baslik: string;
  mahkeme: string;
  taraflar: string;
  konu: string;
  aciklamalar: string[];
  hukuki_sebepler: string[];
  deliller: string[];
  sonuc: string;
  sources: Kaynak[];
  uyari: string;
};

const TURLER = [
  { deger: "dava", etiket: "Dava dilekçesi" },
  { deger: "cevap", etiket: "Cevap dilekçesi" },
  { deger: "cevaba-cevap", etiket: "Cevaba cevap (replik)" },
  { deger: "istinaf", etiket: "İstinaf dilekçesi" },
  { deger: "temyiz", etiket: "Temyiz dilekçesi" },
  { deger: "itiraz-iptali", etiket: "İtirazın iptali davası" },
  { deger: "cevap-idari", etiket: "İdari dava (iptal)" },
  { deger: "ihtarname", etiket: "İhtarname" },
  { deger: "sikayet", etiket: "Şikâyet / suç duyurusu" },
  { deger: "beyan", etiket: "Beyan dilekçesi" },
];

export default function DilekcePage() {
  const [tur, setTur] = useState("dava");
  const [mahkeme, setMahkeme] = useState("");
  const [davaci, setDavaci] = useState("");
  const [davali, setDavali] = useState("");
  const [dosyaNo, setDosyaNo] = useState("");
  const [talep, setTalep] = useState("");
  const [olay, setOlay] = useState("");
  const [okunuyor, setOkunuyor] = useState("");
  const [belgeHata, setBelgeHata] = useState("");
  const [eklenen, setEklenen] = useState<string[]>([]);
  const [calisiyor, setCalisiyor] = useState(false);
  const [sonuc, setSonuc] = useState<Dilekce | null>(null);
  const [hata, setHata] = useState("");
  const [saniye, setSaniye] = useState<number | null>(null);

  /** Belgeyi sunucuda metne cevirir ve maddi olay alanina EKLER.
   *  Sessizce ureticiye yedirmiyoruz: avukat ne okundugunu gorsun, kirpsin. */
  const belgeEkle = async (dosya: File) => {
    setBelgeHata("");
    setOkunuyor(dosya.name);
    try {
      const form = new FormData();
      form.append("file", dosya);
      const yanit = await fetch(`${API_PROXY}/belge-metni`, { method: "POST", body: form });
      const d = await yanit.json();
      if (!yanit.ok) throw new Error(d?.detail || `Sunucu ${yanit.status}`);
      setOlay((o) =>
        (o ? o.trimEnd() + "\n\n" : "") +
        `--- ${d.dosya} (belgeden okundu) ---\n${d.metin}`);
      setEklenen((e) => [
        ...e,
        `${d.dosya} · ${d.karakter.toLocaleString("tr-TR")} karakter${d.uyari ? " · " + d.uyari : ""}`,
      ]);
    } catch (err) {
      setBelgeHata(err instanceof Error ? err.message : "Belge okunamadı.");
    } finally {
      setOkunuyor("");
    }
  };

  const uret = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!olay.trim() || calisiyor) return;
    setCalisiyor(true);
    setHata("");
    setSonuc(null);
    const t0 = performance.now();
    try {
      const yanit = await fetch(`${API_PROXY}/dilekce`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tur,
          olay,
          mahkeme,
          davaci,
          davali,
          talep,
          dosya_no: dosyaNo,
        }),
      });
      if (!yanit.ok) throw new Error(String(yanit.status));
      setSonuc(await yanit.json());
      setSaniye((performance.now() - t0) / 1000);
    } catch {
      setHata("Dilekçe üretilemedi. Sunucuya ulaşılamadı veya istek zaman aşımına uğradı.");
    }
    setCalisiyor(false);
  };

  const wordIndir = async () => {
    if (!sonuc) return;
    const yanit = await fetch(`${API_PROXY}/dilekce/docx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sonuc),
    });
    if (!yanit.ok) return;
    const blob = await yanit.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dilekce-${tur}.docx`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <Ust mod="uygulama" />
      <main className="kap" style={{ paddingTop: 32, paddingBottom: 48 }}>
        <KonsolGezinti />
        <h1 style={{ marginTop: 22 }}>Dilekçe taslağı</h1>
        <p className="spot" style={{ marginTop: 10 }}>
          Olayı kendi cümlelerinizle anlatın. Motor önce külliyattan dayanak
          çeker, taslağı <b>yalnızca o dayanaklara</b> yaslanarak yazar ve
          kullandığı pasajları altına koyar. Vermediğiniz isim, tarih ve tutarı
          uydurmaz — boşluk bırakır.
        </p>

        <form onSubmit={uret} style={{ marginTop: 22, display: "grid", gap: 14 }}>
          <div className="izgara">
            <div>
              <span className="alan-etiket">Dilekçe türü</span>
              <Secici
                baslik="Dilekçe türü"
                deger={tur}
                secenekler={TURLER}
                onSec={setTur}
                genislik={230}
              />
            </div>
            <label>
              <span className="alan-etiket">Mahkeme / merci</span>
              <input
                className="girdi"
                value={mahkeme}
                onChange={(e) => setMahkeme(e.target.value)}
                placeholder="İstanbul 3. Asliye Hukuk Mahkemesi"
              />
            </label>
            <label>
              <span className="alan-etiket">Dosya no</span>
              <input
                className="girdi"
                value={dosyaNo}
                onChange={(e) => setDosyaNo(e.target.value)}
                placeholder="2026/123 E."
              />
            </label>
            <label>
              <span className="alan-etiket">Davacı / başvuran</span>
              <input
                className="girdi"
                value={davaci}
                onChange={(e) => setDavaci(e.target.value)}
                placeholder="Ad Soyad, TCKN"
              />
            </label>
            <label>
              <span className="alan-etiket">Davalı / karşı taraf</span>
              <input
                className="girdi"
                value={davali}
                onChange={(e) => setDavali(e.target.value)}
                placeholder="Ad Soyad / unvan"
              />
            </label>
            <label>
              <span className="alan-etiket">Talep</span>
              <input
                className="girdi"
                value={talep}
                onChange={(e) => setTalep(e.target.value)}
                placeholder="Kıdem ve ihbar tazminatının tahsili"
              />
            </label>
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <label className="dugme" style={{ cursor: okunuyor ? "default" : "pointer" }}>
              {okunuyor ? `${okunuyor} okunuyor…` : "Evrak yükle (PDF, DOCX, UDF, TXT)"}
              <input
                type="file"
                accept=".pdf,.docx,.udf,.txt,.md"
                style={{ display: "none" }}
                disabled={!!okunuyor}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) belgeEkle(f);
                  e.target.value = "";
                }}
              />
            </label>
            <span className="kucuk">
              Belgenin metni aşağıdaki alana eklenir; gereksiz kısımları silebilirsiniz.
            </span>
          </div>
          {eklenen.length > 0 && (
            <ul className="kucuk" style={{ margin: "2px 0 0", paddingLeft: 18 }}>
              {eklenen.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
          {belgeHata && <p className="uyari" style={{ margin: 0 }}>{belgeHata}</p>}

          <label>
            <span className="alan-etiket">
              Maddi olay — ne oldu, ne zaman, kim ne yaptı (zorunlu)
            </span>
            <textarea
              className="metin-alani"
              value={olay}
              onChange={(e) => setOlay(e.target.value)}
              placeholder="Müvekkil 12.03.2019 - 04.08.2026 arasında davalı iş yerinde çalıştı. İş sözleşmesi 04.08.2026'da işveren tarafından haklı neden gösterilmeden feshedildi. Son brüt ücreti 42.000 TL, ayrıca yol ve yemek yardımı alıyordu…"
              required
            />
          </label>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button type="submit" className="dugme dugme-ana" disabled={calisiyor || !olay.trim()}>
              {calisiyor ? "yazılıyor…" : "Taslağı üret"}
            </button>
            {saniye !== null && !calisiyor && (
              <span className="kucuk">{saniye.toFixed(1)} saniyede döndü</span>
            )}
          </div>
        </form>

        {hata && (
          <p className="uyari" style={{ marginTop: 18 }}>
            {hata}
          </p>
        )}

        {sonuc && (
          <section style={{ marginTop: 26, display: "grid", gap: 16 }}>
            {sonuc.uyari && <p className="uyari">{sonuc.uyari}</p>}

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button type="button" className="dugme dugme-sade" onClick={wordIndir}>
                Word olarak indir
              </button>
              <button
                type="button"
                className="dugme dugme-sade"
                onClick={() => {
                  const d = sonuc;
                  const metin = [
                    d.mahkeme ? `${d.mahkeme.toUpperCase()}'NE` : "",
                    "",
                    d.taraflar,
                    d.konu ? `KONU: ${d.konu}` : "",
                    "",
                    "AÇIKLAMALAR",
                    ...d.aciklamalar.map((a, i) => `${i + 1}. ${a}`),
                    "",
                    d.hukuki_sebepler.length ? `HUKUKİ SEBEPLER: ${d.hukuki_sebepler.join("; ")}` : "",
                    d.deliller.length ? `DELİLLER: ${d.deliller.join("; ")}` : "",
                    "",
                    "SONUÇ VE İSTEM",
                    d.sonuc,
                  ]
                    .filter((x) => x !== undefined)
                    .join("\n");
                  navigator.clipboard?.writeText(metin);
                }}
              >
                Metni kopyala
              </button>
              <DosyayaKaydet
                tur="dilekce"
                baslik={sonuc.baslik || `${tur} dilekçesi`}
                veri={sonuc}
              />
            </div>

            <div className="belge">
              {sonuc.mahkeme && (
                <div className="belge-ortali">{sonuc.mahkeme.toUpperCase()}&apos;NE</div>
              )}
              {!sonuc.mahkeme && sonuc.baslik && (
                <div className="belge-ortali">{sonuc.baslik.toUpperCase()}</div>
              )}
              {sonuc.taraflar.split("\n").filter(Boolean).map((t) => (
                <div key={t}>{t}</div>
              ))}
              {sonuc.konu && (
                <div style={{ marginTop: 10 }}>
                  <b>KONU:</b> {sonuc.konu}
                </div>
              )}
              {sonuc.aciklamalar.length > 0 && (
                <>
                  <h4>AÇIKLAMALAR</h4>
                  <ol style={{ paddingLeft: 20 }}>
                    {sonuc.aciklamalar.map((a, i) => (
                      <li key={i} style={{ marginBottom: 8 }}>
                        {a}
                      </li>
                    ))}
                  </ol>
                </>
              )}
              {sonuc.hukuki_sebepler.length > 0 && (
                <>
                  <h4>HUKUKİ SEBEPLER</h4>
                  <div>{sonuc.hukuki_sebepler.join("; ")}</div>
                </>
              )}
              {sonuc.deliller.length > 0 && (
                <>
                  <h4>DELİLLER</h4>
                  <div>{sonuc.deliller.join("; ")}</div>
                </>
              )}
              {sonuc.sonuc && (
                <>
                  <h4>SONUÇ VE İSTEM</h4>
                  <div>{sonuc.sonuc}</div>
                </>
              )}
            </div>

            {sonuc.sources.length > 0 && (
              <div>
                <p className="kucuk" style={{ marginBottom: 10 }}>
                  Taslağın dayandığı {sonuc.sources.length} pasaj — başlığa
                  tıklayınca tam metni açılır.
                </p>
                <div style={{ display: "grid", gap: 8 }}>
                  {sonuc.sources.map((k, i) => (
                    <KaynakKarti key={i} kaynak={k} no={i + 1} kimlik={`d-${i + 1}`} />
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
