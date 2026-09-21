"use client";

// Saha testi ekrani — Av. Mehmet Emin Şalış icin.
//
// Neden ayri ekran: konsolun kendisinde "bunu kullanir miydin" diye soracak
// yer yok; olculen tek sey otomatik hit@5 (bkz. eval_kapsam.py). Bu ekran
// olcumun insan tarafini toplar ve SQLite'a yazar — tarayici temizlense de
// konteyner yeniden yaratilsa da kaybolmaz.

import React, { useState, useRef, useEffect } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";
import KonsolGezinti from "@/components/konsol-gezinti";
import KaynakKarti, { Kaynak } from "@/components/kaynak-paneli";

type Karar = "evet" | "duzelterek" | "hayir";

type Tur = {
  id: string;
  soru: string;
  cevap: string;
  kaynaklar: Kaynak[];
  saniye: number;
  karar?: Karar;
  kaydedildi?: boolean;
};

const KARARLAR: { deger: Karar; etiket: string; ipucu: string }[] = [
  { deger: "evet", etiket: "Evet, kullanırdım", ipucu: "Olduğu gibi dilekçeye girer" },
  { deger: "duzelterek", etiket: "Düzelterek", ipucu: "Doğru yönü gösterdi ama elden geçmeli" },
  { deger: "hayir", etiket: "Hayır", ipucu: "Yanlış ya da işe yaramaz" },
];

const SINIRLAR = [
  "Mevzuat tarafı 73 kanun. Yönetmelik, tebliğ ve KHK yok — o alanlara girerse eli boş döner.",
  "Bir maddenin yürürlükte mi, mülga mı olduğunu sistem bilmiyor. Tarih kontrolü sizde.",
  "İçtihadın %93'ü 2023-2026 arası. Daha eski yerleşik içtihat külliyatta ince.",
  "Ölçülmüş isabet: doğru kanun maddesi ilk 5 sonuçta %79. Kalan %21'i görmek istiyoruz.",
  "Cevabı bir dil modeli yazıyor; sorgunuz ve eşleşen pasajlar OpenAI'ye gidiyor. Müvekkil adı, TCKN, dosya no yazmayın.",
];

export default function SahaTesti() {
  const [turlar, setTurlar] = useState<Tur[]>([]);
  const [girdi, setGirdi] = useState("");
  const [calisiyor, setCalisiyor] = useState(false);
  const [hata, setHata] = useState("");
  const [sayac, setSayac] = useState<number | null>(null);
  const sonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    sonRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turlar.length]);

  useEffect(() => {
    fetch(`${API_PROXY}/test-notlari`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setSayac(d.kararli ?? 0))
      .catch(() => {});
  }, []);

  async function sor(e: React.FormEvent) {
    e.preventDefault();
    const soru = girdi.trim();
    if (!soru || calisiyor) return;
    setGirdi("");
    setHata("");
    setCalisiyor(true);
    const t0 = Date.now();
    try {
      const yanit = await fetch(`${API_PROXY}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: soru }),
      });
      if (!yanit.ok) throw new Error(`Sunucu ${yanit.status}`);
      const d = await yanit.json();
      setTurlar((o) => [
        ...o,
        {
          id: Math.random().toString(36).slice(2),
          soru,
          cevap: d.text || "",
          kaynaklar: (d.sources || []) as Kaynak[],
          saniye: (Date.now() - t0) / 1000,
        },
      ]);
    } catch (err) {
      setHata(err instanceof Error ? err.message : "Sorgu tamamlanamadı.");
    } finally {
      setCalisiyor(false);
    }
  }

  function guncelle(id: string, yama: Partial<Tur>) {
    setTurlar((o) => o.map((t) => (t.id === id ? { ...t, ...yama } : t)));
  }

  return (
    <>
      <Ust mod="uygulama" />
      <KonsolGezinti />
      <main className="sarmal">
        <section className="brifing">
          <h1>Saha testi — Av. Mehmet Emin Şalış</h1>
          <p className="giris">
            Kendi dosyalarınızdan gerçek sorular sorun. Her cevabın altında tek
            bir soru var: <strong>bunu bir dilekçede kullanır mıydınız?</strong>{" "}
            Puan vermenize gerek yok, üç düğmeden birine basıp varsa iki satır
            not bırakmanız yeter. Yanlış çıkan cevap bizim için doğru çıkandan
            değerlidir — asıl aradığımız o.
          </p>
          <h2>Bilerek açık bıraktığımız yerler</h2>
          <ul className="sinirlar">
            {SINIRLAR.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
          {sayac !== null && (
            <p className="sayac">Şu ana kadar değerlendirilen cevap: <strong>{sayac}</strong></p>
          )}
        </section>

        {turlar.map((t) => (
          <article key={t.id} className="tur">
            <p className="soru">{t.soru}</p>
            <div className="cevap">{t.cevap || "(cevap boş döndü)"}</div>
            {t.kaynaklar.length > 0 && (
              <div className="kaynaklar">
                {t.kaynaklar.map((k, i) => (
                  <KaynakKarti key={i} kaynak={k} no={i + 1} kimlik={`k-${t.id}-${i + 1}`} />
                ))}
              </div>
            )}
            <p className="sure">{t.saniye.toFixed(1)} sn</p>
            <Degerlendirme tur={t} guncelle={guncelle} onKaydedildi={() => setSayac((s) => (s ?? 0) + 1)} />
          </article>
        ))}

        <div ref={sonRef} />

        {hata && <p className="hata">{hata}</p>}

        <form onSubmit={sor} className="sorgu">
          <textarea
            value={girdi}
            onChange={(e) => setGirdi(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) sor(e as unknown as React.FormEvent);
            }}
            placeholder="Kendi dosyanızdan bir soru yazın — müvekkil adı ve dosya numarası olmadan."
            rows={3}
          />
          <button type="submit" disabled={calisiyor || !girdi.trim()}>
            {calisiyor ? "Aranıyor…" : "Sor"}
          </button>
        </form>

        <SerbestNot onKaydedildi={() => setSayac((s) => s)} />
      </main>
      <Alt />

      <style jsx>{`
        .sarmal { max-width: 860px; margin: 0 auto; padding: 28px 20px 80px; }
        .brifing { border: 1px solid #e6e6ea; border-radius: 12px; padding: 20px 22px; background: #fff; }
        h1 { font-size: 1.35rem; margin: 0 0 10px; }
        h2 { font-size: .95rem; margin: 18px 0 8px; color: #444; }
        .giris { margin: 0; line-height: 1.6; color: #333; }
        .sinirlar { margin: 0; padding-left: 18px; color: #555; font-size: .9rem; line-height: 1.65; }
        .sayac { margin: 16px 0 0; font-size: .85rem; color: #666; }
        .tur { border: 1px solid #e6e6ea; border-radius: 12px; padding: 18px 20px; margin-top: 22px; background: #fff; }
        .soru { font-weight: 600; margin: 0 0 12px; }
        .cevap { white-space: pre-wrap; line-height: 1.65; color: #222; }
        .kaynaklar { margin-top: 14px; display: grid; gap: 10px; }
        .sure { font-size: .8rem; color: #888; margin: 12px 0 0; }
        .sorgu { margin-top: 24px; display: flex; gap: 10px; align-items: flex-end; }
        textarea { flex: 1; padding: 12px; border: 1px solid #d5d5dd; border-radius: 10px; font: inherit; resize: vertical; background: #fff; }
        button { padding: 12px 20px; border-radius: 10px; border: 0; background: #2d2a6e; color: #fff; font: inherit; cursor: pointer; }
        button:disabled { opacity: .5; cursor: default; }
        .hata { color: #b3261e; margin-top: 16px; }
      `}</style>
    </>
  );
}

/** Cevabın altındaki üç düğme + not alanı. Kayıt tek sefer. */
function Degerlendirme({
  tur, guncelle, onKaydedildi,
}: { tur: Tur; guncelle: (id: string, y: Partial<Tur>) => void; onKaydedildi: () => void }) {
  const [dogruMadde, setDogruMadde] = useState("");
  const [notu, setNotu] = useState("");
  const [kaydediliyor, setKaydediliyor] = useState(false);

  async function kaydet(karar: Karar) {
    if (tur.kaydedildi || kaydediliyor) return;
    setKaydediliyor(true);
    try {
      await fetch(`${API_PROXY}/test-notu`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          alan: "arama",
          soru: tur.soru,
          cevap: tur.cevap,
          kaynaklar: tur.kaynaklar.map((k) => k.source),
          karar,
          dogru_madde: dogruMadde,
          notu,
          saniye: tur.saniye,
        }),
      });
      guncelle(tur.id, { karar, kaydedildi: true });
      onKaydedildi();
    } finally {
      setKaydediliyor(false);
    }
  }

  if (tur.kaydedildi) {
    return <p className="bitti">Kaydedildi: {KARARLAR.find((k) => k.deger === tur.karar)?.etiket}
      <style jsx>{`.bitti { margin: 16px 0 0; font-size: .85rem; color: #2e7d32; }`}</style>
    </p>;
  }

  return (
    <div className="kutu">
      <p className="baslik">Bunu bir dilekçede kullanır mıydınız?</p>
      <div className="dugmeler">
        {KARARLAR.map((k) => (
          <button key={k.deger} type="button" title={k.ipucu}
                  disabled={kaydediliyor} onClick={() => kaydet(k.deger)}>
            {k.etiket}
          </button>
        ))}
      </div>
      <input value={dogruMadde} onChange={(e) => setDogruMadde(e.target.value)}
             placeholder="Gelmesi gereken madde neydi? (örn. TBK m.344)" />
      <textarea value={notu} onChange={(e) => setNotu(e.target.value)} rows={2}
                placeholder="Notunuz (isteğe bağlı) — neden böyle karar verdiniz?" />
      <p className="ipucu">Önce varsa maddeyi ve notu yazın, sonra düğmeye basın; kayıt düğmeyle olur.</p>

      <style jsx>{`
        .kutu { margin-top: 16px; padding-top: 16px; border-top: 1px dashed #dcdce2; display: grid; gap: 10px; }
        .baslik { margin: 0; font-weight: 600; font-size: .92rem; }
        .dugmeler { display: flex; gap: 8px; flex-wrap: wrap; }
        button { padding: 9px 14px; border-radius: 9px; border: 1px solid #c9c9d3; background: #fff; font: inherit; cursor: pointer; }
        button:hover:not(:disabled) { border-color: #2d2a6e; color: #2d2a6e; }
        input, textarea { padding: 10px; border: 1px solid #d5d5dd; border-radius: 9px; font: inherit; background: #fff; resize: vertical; }
        .ipucu { margin: 0; font-size: .78rem; color: #888; }
      `}</style>
    </div>
  );
}

/** Sözleşme denetimi ve dilekçe üretimi konsolun kendi sekmelerinde yapılır;
 *  izlenim buraya düşer. */
function SerbestNot({ onKaydedildi }: { onKaydedildi: () => void }) {
  const [alan, setAlan] = useState<"sozlesme" | "dilekce" | "genel">("sozlesme");
  const [notu, setNotu] = useState("");
  const [durum, setDurum] = useState("");

  const SECENEKLER: { d: typeof alan; e: string }[] = [
    { d: "sozlesme", e: "Sözleşme denetimi" },
    { d: "dilekce", e: "Dilekçe üretimi" },
    { d: "genel", e: "Genel izlenim" },
  ];

  async function gonder(e: React.FormEvent) {
    e.preventDefault();
    if (!notu.trim()) return;
    await fetch(`${API_PROXY}/test-notu`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alan, notu }),
    });
    setNotu("");
    setDurum("Not kaydedildi.");
    onKaydedildi();
    setTimeout(() => setDurum(""), 2500);
  }

  return (
    <form onSubmit={gonder} className="serbest">
      <h2>Diğer sekmeler için not</h2>
      <p className="aciklama">
        Sözleşme denetimini ve dilekçe üretimini konsoldaki kendi sekmelerinde
        deneyin; izlenimi buraya bırakın.
      </p>
      <div className="secim">
        {SECENEKLER.map((s) => (
          <button key={s.d} type="button" className={alan === s.d ? "secili" : ""}
                  onClick={() => setAlan(s.d)}>
            {s.e}
          </button>
        ))}
      </div>
      <textarea value={notu} onChange={(e) => setNotu(e.target.value)} rows={3}
                placeholder="Ne denediniz, ne oldu, ne eksikti?" />
      <button type="submit" className="gonder" disabled={!notu.trim()}>Notu kaydet</button>
      {durum && <span className="durum">{durum}</span>}

      <style jsx>{`
        .serbest { margin-top: 40px; border: 1px solid #e6e6ea; border-radius: 12px; padding: 18px 20px; background: #fff; display: grid; gap: 10px; }
        h2 { font-size: 1rem; margin: 0; }
        .aciklama { margin: 0; font-size: .88rem; color: #555; line-height: 1.6; }
        .secim { display: flex; gap: 8px; flex-wrap: wrap; }
        .secim button { padding: 8px 13px; border-radius: 9px; border: 1px solid #c9c9d3; background: #fff; font: inherit; cursor: pointer; }
        .secim button.secili { border-color: #2d2a6e; color: #2d2a6e; font-weight: 600; }
        textarea { padding: 10px; border: 1px solid #d5d5dd; border-radius: 9px; font: inherit; background: #fff; resize: vertical; }
        .gonder { justify-self: start; padding: 10px 18px; border-radius: 9px; border: 0; background: #2d2a6e; color: #fff; font: inherit; cursor: pointer; }
        .gonder:disabled { opacity: .5; cursor: default; }
        .durum { font-size: .85rem; color: #2e7d32; }
      `}</style>
    </form>
  );
}
