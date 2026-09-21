"use client";

import React, { useCallback, useEffect, useState } from "react";
import { API_PROXY } from "@/lib/api";
import Ust, { Alt } from "@/components/ust";
import KonsolGezinti from "@/components/konsol-gezinti";

type Dosya = {
  id: string;
  ad: string;
  aciklama: string;
  olusturma: string;
  guncelleme: string;
  kayit: number;
};

type Kayit = {
  id: string;
  tur: string;
  baslik: string;
  icerik: string;
  veri: unknown;
  olusturma: string;
};

const TUR_ADI: Record<string, string> = {
  not: "Not",
  sorgu: "Arama",
  dilekce: "Dilekçe",
  analiz: "Sözleşme denetimi",
};

function tarih(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("tr-TR");
}

export default function DosyalarPage() {
  const [dosyalar, setDosyalar] = useState<Dosya[]>([]);
  const [acik, setAcik] = useState<string | null>(null);
  const [kayitlar, setKayitlar] = useState<Kayit[]>([]);
  const [yeniAd, setYeniAd] = useState("");
  const [yeniAciklama, setYeniAciklama] = useState("");
  const [not, setNot] = useState("");
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState("");

  const listele = useCallback(async () => {
    try {
      const r = await fetch(`${API_PROXY}/dosyalar`);
      if (!r.ok) throw new Error();
      const d = await r.json();
      setDosyalar(d.dosyalar || []);
      setHata("");
    } catch {
      setHata("Dosyalar okunamadı. Sunucuya ulaşılamıyor olabilir.");
    }
    setYukleniyor(false);
  }, []);

  useEffect(() => {
    listele();
  }, [listele]);

  const ac = async (id: string) => {
    if (acik === id) {
      setAcik(null);
      return;
    }
    setAcik(id);
    setKayitlar([]);
    const r = await fetch(`${API_PROXY}/dosyalar/${id}`);
    if (r.ok) setKayitlar((await r.json()).kayitlar || []);
  };

  const olustur = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!yeniAd.trim()) return;
    const r = await fetch(`${API_PROXY}/dosyalar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ad: yeniAd, aciklama: yeniAciklama }),
    });
    if (r.ok) {
      setYeniAd("");
      setYeniAciklama("");
      listele();
    }
  };

  const notEkle = async (id: string) => {
    if (!not.trim()) return;
    const r = await fetch(`${API_PROXY}/dosyalar/${id}/kayit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tur: "not", baslik: "Not", icerik: not }),
    });
    if (r.ok) {
      setNot("");
      ac(id);
      ac(id);
      const y = await fetch(`${API_PROXY}/dosyalar/${id}`);
      if (y.ok) setKayitlar((await y.json()).kayitlar || []);
      listele();
    }
  };

  const sil = async (id: string) => {
    const r = await fetch(`${API_PROXY}/dosyalar/${id}`, { method: "DELETE" });
    if (r.ok) {
      if (acik === id) setAcik(null);
      listele();
    }
  };

  const kayitSil = async (dosyaId: string, kayitId: string) => {
    const r = await fetch(`${API_PROXY}/dosyalar/${dosyaId}/kayit/${kayitId}`, {
      method: "DELETE",
    });
    if (r.ok) setKayitlar((o) => o.filter((k) => k.id !== kayitId));
  };

  return (
    <>
      <Ust mod="uygulama" />
      <main className="kap" style={{ paddingTop: 32, paddingBottom: 48 }}>
        <KonsolGezinti />
        <h1 style={{ marginTop: 22 }}>İş dosyaları</h1>
        <p className="spot" style={{ marginTop: 10 }}>
          Her müvekkil/uyuşmazlık için bir dosya açın; ürettiğiniz dilekçeler,
          sözleşme denetimleri ve notlar onun altında birikir. Kayıtlar
          sunucudaki veritabanında tutulur — tarayıcınızı temizleseniz de durur.
        </p>

        <form onSubmit={olustur} className="kart kart-dolgu" style={{ marginTop: 20, display: "grid", gap: 10 }}>
          <div className="izgara">
            <label>
              <span className="alan-etiket">Dosya adı</span>
              <input
                className="girdi"
                value={yeniAd}
                onChange={(e) => setYeniAd(e.target.value)}
                placeholder="Yılmaz / İşe iade"
              />
            </label>
            <label>
              <span className="alan-etiket">Açıklama (isteğe bağlı)</span>
              <input
                className="girdi"
                value={yeniAciklama}
                onChange={(e) => setYeniAciklama(e.target.value)}
                placeholder="İstanbul 12. İş Mah. 2026/451 E."
              />
            </label>
          </div>
          <div>
            <button type="submit" className="dugme dugme-ana" disabled={!yeniAd.trim()}>
              Dosya aç
            </button>
          </div>
        </form>

        {hata && <p className="uyari" style={{ marginTop: 16 }}>{hata}</p>}

        <div style={{ marginTop: 22, display: "grid", gap: 10 }}>
          {yukleniyor ? (
            <p className="kucuk">yükleniyor…</p>
          ) : dosyalar.length === 0 ? (
            <p className="kucuk">Henüz dosya yok. Yukarıdan ilkini açın.</p>
          ) : (
            dosyalar.map((d) => (
              <div key={d.id} style={{ display: "grid", gap: 8 }}>
                <div className="dosya-satir">
                  <button
                    type="button"
                    className="kaynak-baslik"
                    style={{ width: "auto" }}
                    onClick={() => ac(d.id)}
                    aria-expanded={acik === d.id}
                  >
                    {d.ad}
                    <span aria-hidden className="kaynak-ok">{acik === d.id ? "▲" : "▼"}</span>
                  </button>
                  <span className="kaynak-meta" style={{ marginTop: 0 }}>
                    <span>{d.kayit} kayıt</span>
                    <span className="tek">{tarih(d.guncelleme)}</span>
                    <button type="button" className="dugme-yazi" onClick={() => sil(d.id)}>
                      sil
                    </button>
                  </span>
                </div>

                {acik === d.id && (
                  <div className="kart kart-dolgu" style={{ display: "grid", gap: 12 }}>
                    {d.aciklama && <p className="kucuk">{d.aciklama}</p>}
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        className="girdi"
                        value={not}
                        onChange={(e) => setNot(e.target.value)}
                        placeholder="Dosyaya not ekle…"
                      />
                      <button
                        type="button"
                        className="dugme dugme-sade"
                        onClick={() => notEkle(d.id)}
                        disabled={!not.trim()}
                      >
                        Ekle
                      </button>
                    </div>

                    {kayitlar.length === 0 ? (
                      <p className="kucuk">Bu dosyada henüz kayıt yok.</p>
                    ) : (
                      <div style={{ display: "grid", gap: 8 }}>
                        {kayitlar.map((k) => (
                          <div key={k.id} className="kaynak-kart">
                            <div className="kaynak-kart-ust">
                              <span className="kaynak-no tek">
                                {TUR_ADI[k.tur] ?? k.tur}
                              </span>
                              <div style={{ minWidth: 0, flex: 1 }}>
                                <div style={{ fontSize: 13.5, fontWeight: 560 }}>
                                  {k.baslik || "(başlıksız)"}
                                </div>
                                <div className="kaynak-meta">
                                  <span className="tek">{tarih(k.olusturma)}</span>
                                </div>
                              </div>
                              <button
                                type="button"
                                className="dugme-yazi kaynak-kopya"
                                onClick={() => kayitSil(d.id, k.id)}
                              >
                                sil
                              </button>
                            </div>
                            {k.icerik && <div className="kaynak-pasaj">{k.icerik}</div>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </main>
      <Alt />
    </>
  );
}
