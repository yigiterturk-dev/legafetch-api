"use client";

import React, { useState } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";
import KonsolGezinti from "@/components/konsol-gezinti";
import Secici from "@/components/secici";

type Senaryo = {
  varsayim: string;
  gun: number;
  dusulen_gun: number;
  kidem_gun: number;
  sure: string;
  esas_ucret: number;
  tavan_uygulandi: boolean;
  brut: number;
  damga: number;
  net: number;
};

type Kalem = { donem: string; gun: number; kod: string; ad: string; etki: string; aciklama: string };

type Sonuc = {
  dosyalar: string[];
  tespit: Record<string, string | number>;
  senaryolar: Senaryo[];
  ihbar: { hak_var: boolean; hafta: number; brut: number; net: number | null; gerekce: string };
  yillik_izin: { yillik_hak_gun: number; not: string };
  eksik_gun: { kesin_dusulecek: number; tartismali: number; kalemler: Kalem[] };
  tavan: { deger: number | null; kullanilabilir: boolean; oneri: number | null; not: string };
  cekinceler: string[];
};

const tl = (n: number) =>
  n.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const FESHEDEN = [
  { deger: "", etiket: "Belgeden okunsun" },
  { deger: "isci", etiket: "İşçi feshetti" },
  { deger: "isveren", etiket: "İşveren feshetti" },
];

export default function IscilikPage() {
  const [dosyalar, setDosyalar] = useState<File[]>([]);
  const [ucret, setUcret] = useState("");
  const [tavan, setTavan] = useState("");
  const [fesheden, setFesheden] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState("");
  const [sonuc, setSonuc] = useState<Sonuc | null>(null);

  async function hesapla() {
    if (!dosyalar.length) {
      setHata("En az bir belge yükleyin: SGK hizmet dökümü ve varsa fesih ihtarnamesi.");
      return;
    }
    setYukleniyor(true);
    setHata("");
    setSonuc(null);
    try {
      const form = new FormData();
      dosyalar.forEach((d) => form.append("files", d));
      if (ucret) form.append("giydirilmis_aylik", ucret);
      if (tavan) form.append("tavan", tavan);
      if (fesheden) form.append("fesheden", fesheden);
      const yanit = await fetch(`${API_PROXY}/iscilik-hesabi`, { method: "POST", body: form });
      const govde = await yanit.json();
      if (!yanit.ok) throw new Error(govde?.detail || "Hesap yapılamadı.");
      setSonuc(govde as Sonuc);
    } catch (e) {
      setHata(e instanceof Error ? e.message : "Hesap yapılamadı.");
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <>
      <Ust />
      <main className="kabuk">
        <KonsolGezinti />
        <h1>İşçilik alacağı</h1>
        <p className="kucuk">
          SGK hizmet dökümünü (ve varsa fesih ihtarnamesini) yükleyin; tarihler,
          prim günleri ve eksik gün kodları belgeden okunur, tutar burada
          hesaplanır. <b>Aritmetiği dil modeli yapmaz</b> — model yalnız belgeden
          satır çıkarır, çıkardığı her kazanç belgede birebir aranır.
        </p>

        <div className="kart kart-dolgu" style={{ display: "grid", gap: 12 }}>
          <label>
            <span className="alan-etiket">Belgeler (PDF / DOCX / UDF, en çok 5)</span>
            <input
              type="file"
              className="girdi"
              multiple
              accept=".pdf,.docx,.udf,.txt"
              onChange={(e) => setDosyalar(Array.from(e.target.files || []))}
            />
          </label>
          {dosyalar.length > 0 && (
            <p className="kucuk">{dosyalar.map((d) => d.name).join(", ")}</p>
          )}
          <div className="izgara">
            <label>
              <span className="alan-etiket">Giydirilmiş brüt aylık ücret (TL) — boşsa dökümdeki son SGK kazancı</span>
              <input type="number" className="girdi" value={ucret}
                     onChange={(e) => setUcret(e.target.value)} placeholder="94195.38" />
            </label>
            <label>
              <span className="alan-etiket">Kıdem tavanı (TL) — fesih dönemindeki yıllık tavan</span>
              <input type="number" className="girdi" value={tavan}
                     onChange={(e) => setTavan(e.target.value)} placeholder="yürürlükteki tavan" />
            </label>
          </div>
          <Secici deger={fesheden} secenekler={FESHEDEN} onSec={setFesheden}
                  baslik="Feshi kim yaptı" genislik={220} />
          <p className="uyari">
            Tavan altı ayda bir değişir ve uygulamaya gömülmedi: eski bir rakam
            yanlış olduğunu söylemeden yanlış sonuç verir. Boş bırakırsanız tavan
            uygulanmaz ve ücret tavanı aşıyorsa tutar olduğundan yüksek çıkar.
          </p>
          <div>
            <button className="dugme" onClick={hesapla} disabled={yukleniyor}>
              {yukleniyor ? "Belgeler okunuyor…" : "Hesapla"}
            </button>
          </div>
          {hata && <p className="uyari">{hata}</p>}
        </div>

        {sonuc && (
          <>
            <div className="kart kart-dolgu" style={{ display: "grid", gap: 8 }}>
              <h3>Belgeden okunanlar</h3>
              <div className="satir-arasi"><span>İşyeri</span><span>{sonuc.tespit.isyeri || "—"}</span></div>
              <div className="satir-arasi"><span>İşe giriş</span><span>{sonuc.tespit.ise_giris}</span></div>
              <div className="satir-arasi"><span>Fesih</span><span>{sonuc.tespit.isten_cikis}</span></div>
              <div className="satir-arasi"><span>Hizmet süresi</span>
                <span>{sonuc.tespit.hizmet_suresi} ({sonuc.tespit.hizmet_gunu} gün)</span></div>
              <div className="satir-arasi"><span>Feshi yapan</span>
                <span>{sonuc.tespit.fesheden === "isci" ? "işçi" : "işveren"}</span></div>
              <div className="satir-arasi"><span>Esas alınan ücret</span>
                <span>{tl(Number(sonuc.tespit.esas_alinan_ucret))} TL</span></div>
              <div className="satir-arasi"><span>Okunan döküm satırı</span>
                <span>{sonuc.tespit.satir_sayisi}</span></div>
            </div>

            <div className="kart kart-dolgu" style={{ display: "grid", gap: 10 }}>
              <h3>Kıdem tazminatı — varsayıma göre</h3>
              <p className="kucuk">{sonuc.tavan.not}</p>
              <div style={{ overflowX: "auto" }}>
                <table className="tablo">
                  <thead>
                    <tr><th>Varsayım</th><th>Kıdeme esas süre</th><th>Brüt</th><th>Net</th></tr>
                  </thead>
                  <tbody>
                    {sonuc.senaryolar.map((s) => (
                      <tr key={s.varsayim}>
                        <td>{s.varsayim}</td>
                        <td>{s.sure} ({s.kidem_gun} gün)</td>
                        <td>{tl(s.brut)} TL</td>
                        <td>{tl(s.net)} TL</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="kucuk">
                Nette yalnız binde 7,59 damga vergisi düşüldü; kıdem tazminatı
                gelir vergisinden istisnadır. Faiz dahil değil.
              </p>
            </div>

            <div className="kart kart-dolgu" style={{ display: "grid", gap: 8 }}>
              <h3>İhbar tazminatı</h3>
              {sonuc.ihbar.hak_var ? (
                <div className="satir-arasi">
                  <span>{sonuc.ihbar.hafta} haftalık bildirim süresi</span>
                  <span>{tl(sonuc.ihbar.brut)} TL brüt</span>
                </div>
              ) : (
                <p>Hesaplanmadı.</p>
              )}
              <p className="kucuk">{sonuc.ihbar.gerekce}</p>
            </div>

            {sonuc.eksik_gun.kalemler.length > 0 && (
              <div className="kart kart-dolgu" style={{ display: "grid", gap: 8 }}>
                <h3>Eksik gün kayıtları</h3>
                <p className="kucuk">
                  Kesin düşülecek: {sonuc.eksik_gun.kesin_dusulecek} gün ·
                  Tartışmalı: {sonuc.eksik_gun.tartismali} gün
                </p>
                <div style={{ overflowX: "auto" }}>
                  <table className="tablo">
                    <thead><tr><th>Dönem</th><th>Gün</th><th>Kod</th><th>Neden</th><th>Kıdeme etkisi</th></tr></thead>
                    <tbody>
                      {sonuc.eksik_gun.kalemler.map((k, i) => (
                        <tr key={`${k.donem}-${i}`}>
                          <td>{k.donem}</td><td>{k.gun}</td><td>{k.kod || "—"}</td>
                          <td>{k.ad}</td><td>{k.aciklama}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="kart kart-dolgu" style={{ display: "grid", gap: 8 }}>
              <h3>Çekinceler</h3>
              <ul>
                {sonuc.cekinceler.map((c, i) => <li key={i}>{c}</li>)}
                <li>{sonuc.yillik_izin.not} Yıllık hak ediş: {sonuc.yillik_izin.yillik_hak_gun} gün.</li>
                <li>
                  Fazla mesai, UBGT, hafta tatili ve bakiye ücret bu hesaba dahil
                  değil; bordro ve puantaj gerekir.
                </li>
              </ul>
            </div>
          </>
        )}
      </main>
      <Alt />
    </>
  );
}
