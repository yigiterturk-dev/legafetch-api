"use client";

import React, { useState } from "react";
import Ust, { Alt } from "@/components/ust";
import KonsolGezinti from "@/components/konsol-gezinti";

const tl = (n: number) =>
  n.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function gunFarki(a: string, b: string): number {
  if (!a || !b) return 0;
  const g = (new Date(b).getTime() - new Date(a).getTime()) / 86400000;
  return g > 0 ? Math.floor(g) : 0;
}

/** Kıdem tazminatı — 1475 s. Kanun m.14. */
function KidemHesabi() {
  const [giris, setGiris] = useState("");
  const [cikis, setCikis] = useState("");
  const [ucret, setUcret] = useState("");
  const [tavan, setTavan] = useState("");

  const gun = gunFarki(giris, cikis);
  const aylik = Number(ucret) || 0;
  const tavanT = Number(tavan) || 0;
  // Her tam yıl için 30 günlük giydirilmiş brüt ücret, artan süre için oranlı.
  const yil = gun / 365;
  const esas = tavanT > 0 ? Math.min(aylik, tavanT) : aylik;
  const brut = esas * yil;
  // Kıdem tazminatından yalnızca damga vergisi kesilir (binde 7,59);
  // gelir vergisinden istisnadır.
  const damga = brut * 0.00759;

  return (
    <div className="kart kart-dolgu" style={{ display: "grid", gap: 12 }}>
      <h3>Kıdem tazminatı</h3>
      <p className="kucuk">
        Dayanak: 1475 s. İş Kanunu m.14 — her tam hizmet yılı için 30 günlük
        <b> giydirilmiş brüt</b> ücret, artan süreler için oranlı.
      </p>
      <div className="izgara">
        <label>
          <span className="alan-etiket">İşe giriş</span>
          <input type="date" className="girdi" value={giris} onChange={(e) => setGiris(e.target.value)} />
        </label>
        <label>
          <span className="alan-etiket">İşten çıkış</span>
          <input type="date" className="girdi" value={cikis} onChange={(e) => setCikis(e.target.value)} />
        </label>
        <label>
          <span className="alan-etiket">Giydirilmiş brüt aylık ücret (TL)</span>
          <input
            type="number"
            className="girdi"
            value={ucret}
            onChange={(e) => setUcret(e.target.value)}
            placeholder="42000"
          />
        </label>
        <label>
          <span className="alan-etiket">Kıdem tavanı (TL) — boş bırakılırsa uygulanmaz</span>
          <input
            type="number"
            className="girdi"
            value={tavan}
            onChange={(e) => setTavan(e.target.value)}
            placeholder="yürürlükteki tavanı yazın"
          />
        </label>
      </div>
      <p className="uyari">
        Tavan altı ayda bir değişir; uygulamaya gömülmedi çünkü eski bir rakam
        sessizce yanlış sonuç üretir. Yürürlükteki tavanı siz girin.
      </p>
      {gun > 0 && aylik > 0 && (
        <div className="sonuc-kutu">
          <div className="satir-arasi">
            <span>Hizmet süresi</span>
            <span>
              {Math.floor(yil)} yıl {Math.floor((gun % 365) / 30)} ay ({gun} gün)
            </span>
          </div>
          <div className="satir-arasi">
            <span>Hesaba esas ücret</span>
            <span>{tl(esas)} TL{tavanT > 0 && esas === tavanT ? " (tavan uygulandı)" : ""}</span>
          </div>
          <div className="satir-arasi">
            <span>Damga vergisi (binde 7,59)</span>
            <span>−{tl(damga)} TL</span>
          </div>
          <div style={{ marginTop: 10 }}>
            Brüt kıdem tazminatı: <b>{tl(brut)} TL</b>
            <div className="kucuk" style={{ marginTop: 4 }}>
              Net (damga sonrası): {tl(brut - damga)} TL
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** İhbar tazminatı — 4857 s. Kanun m.17 bildirim süreleri. */
function IhbarHesabi() {
  const [giris, setGiris] = useState("");
  const [cikis, setCikis] = useState("");
  const [ucret, setUcret] = useState("");

  const gun = gunFarki(giris, cikis);
  const aylik = Number(ucret) || 0;
  const hafta = gun < 183 ? 2 : gun < 548 ? 4 : gun < 1095 ? 6 : 8;
  const gunluk = aylik / 30;
  const brut = gunluk * hafta * 7;

  return (
    <div className="kart kart-dolgu" style={{ display: "grid", gap: 12 }}>
      <h3>İhbar tazminatı</h3>
      <p className="kucuk">
        Dayanak: 4857 s. İş Kanunu m.17 — 6 aydan az 2 hafta, 6 ay–1,5 yıl 4
        hafta, 1,5–3 yıl 6 hafta, 3 yıldan fazla 8 hafta. Süreler sözleşmeyle
        artırılabilir; aşağıdaki hesap kanuni asgari süreyi kullanır.
      </p>
      <div className="izgara">
        <label>
          <span className="alan-etiket">İşe giriş</span>
          <input type="date" className="girdi" value={giris} onChange={(e) => setGiris(e.target.value)} />
        </label>
        <label>
          <span className="alan-etiket">İşten çıkış</span>
          <input type="date" className="girdi" value={cikis} onChange={(e) => setCikis(e.target.value)} />
        </label>
        <label>
          <span className="alan-etiket">Giydirilmiş brüt aylık ücret (TL)</span>
          <input
            type="number"
            className="girdi"
            value={ucret}
            onChange={(e) => setUcret(e.target.value)}
            placeholder="42000"
          />
        </label>
      </div>
      {gun > 0 && aylik > 0 && (
        <div className="sonuc-kutu">
          <div className="satir-arasi">
            <span>Bildirim süresi</span>
            <span>{hafta} hafta</span>
          </div>
          <div className="satir-arasi">
            <span>Günlük ücret</span>
            <span>{tl(gunluk)} TL</span>
          </div>
          <div style={{ marginTop: 10 }}>
            Brüt ihbar tazminatı: <b>{tl(brut)} TL</b>
            <div className="kucuk" style={{ marginTop: 4 }}>
              İhbar tazminatı gelir vergisine tâbidir; net tutar vergi dilimine
              göre değişir, burada hesaplanmaz.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Basit faiz — 3095 s. Kanun. Oran kullanıcıdan alınır. */
function FaizHesabi() {
  const [anapara, setAnapara] = useState("");
  const [oran, setOran] = useState("");
  const [bas, setBas] = useState("");
  const [son, setSon] = useState("");

  const p = Number(anapara) || 0;
  const r = Number(oran) || 0;
  const gun = gunFarki(bas, son);
  const faiz = (p * r * gun) / 36500;

  return (
    <div className="kart kart-dolgu" style={{ display: "grid", gap: 12 }}>
      <h3>Faiz hesabı (basit faiz)</h3>
      <p className="kucuk">
        Dayanak: 3095 s. Kanuni Faiz ve Temerrüt Faizine İlişkin Kanun. Oran
        türü (kanuni faiz / avans faizi / sözleşme faizi) ve dönem değiştiği
        için oran gömülmedi — uyguladığınız oranı siz girin. Bileşik faiz
        hesaplanmaz; dönem içi oran değişimi varsa dönemleri ayrı hesaplayın.
      </p>
      <div className="izgara">
        <label>
          <span className="alan-etiket">Anapara (TL)</span>
          <input type="number" className="girdi" value={anapara} onChange={(e) => setAnapara(e.target.value)} />
        </label>
        <label>
          <span className="alan-etiket">Yıllık oran (%)</span>
          <input type="number" className="girdi" value={oran} onChange={(e) => setOran(e.target.value)} placeholder="9" />
        </label>
        <label>
          <span className="alan-etiket">Başlangıç (temerrüt) tarihi</span>
          <input type="date" className="girdi" value={bas} onChange={(e) => setBas(e.target.value)} />
        </label>
        <label>
          <span className="alan-etiket">Bitiş tarihi</span>
          <input type="date" className="girdi" value={son} onChange={(e) => setSon(e.target.value)} />
        </label>
      </div>
      {p > 0 && r > 0 && gun > 0 && (
        <div className="sonuc-kutu">
          <div className="satir-arasi">
            <span>Gün sayısı</span>
            <span>{gun} gün</span>
          </div>
          <div className="satir-arasi">
            <span>İşlemiş faiz</span>
            <span>{tl(faiz)} TL</span>
          </div>
          <div style={{ marginTop: 10 }}>
            Toplam (anapara + faiz): <b>{tl(p + faiz)} TL</b>
          </div>
        </div>
      )}
    </div>
  );
}

export default function HesapPage() {
  return (
    <>
      <Ust mod="uygulama" />
      <main className="kap" style={{ paddingTop: 32, paddingBottom: 48 }}>
        <KonsolGezinti />
        <h1 style={{ marginTop: 22 }}>Hesaplayıcılar</h1>
        <p className="spot" style={{ marginTop: 10 }}>
          Kanun metnindeki kuralı uygular; <b>değişken oranları gömmez</b>.
          Tavan, faiz oranı ve vergi dilimi dönemden döneme değiştiği için
          bunları siz girersiniz — eski bir rakamı sessizce kullanmak, hiç
          hesaplamamaktan kötüdür.
        </p>
        <div style={{ marginTop: 22, display: "grid", gap: 16 }}>
          <KidemHesabi />
          <IhbarHesabi />
          <FaizHesabi />
        </div>
      </main>
      <Alt />
    </>
  );
}
