"use client";

import React, { useEffect, useState } from "react";
import { API_PROXY } from "@/lib/api";
import Secici from "@/components/secici";

type Dosya = { id: string; ad: string };

/**
 * Üretilen dilekçe / analiz / aramayı bir iş dosyasının altına kaydeder.
 * Kayıt sunucudaki SQLite'a gider (localStorage değil): tarayıcı temizlenince
 * müvekkil dosyası uçmamalı.
 */
export default function DosyayaKaydet({
  tur,
  baslik,
  veri,
  icerik = "",
}: {
  tur: string;
  baslik: string;
  veri?: unknown;
  icerik?: string;
}) {
  const [dosyalar, setDosyalar] = useState<Dosya[]>([]);
  const [secili, setSecili] = useState("");
  const [durum, setDurum] = useState<"" | "kaydediliyor" | "kaydedildi" | "hata">("");

  useEffect(() => {
    fetch(`${API_PROXY}/dosyalar`)
      .then((r) => (r.ok ? r.json() : { dosyalar: [] }))
      .then((d) => {
        setDosyalar(d.dosyalar || []);
        if (d.dosyalar?.length) setSecili(d.dosyalar[0].id);
      })
      .catch(() => setDosyalar([]));
  }, []);

  const kaydet = async () => {
    if (!secili) return;
    setDurum("kaydediliyor");
    try {
      const r = await fetch(`${API_PROXY}/dosyalar/${secili}/kayit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tur, baslik, icerik, veri }),
      });
      setDurum(r.ok ? "kaydedildi" : "hata");
    } catch {
      setDurum("hata");
    }
    setTimeout(() => setDurum(""), 2200);
  };

  if (dosyalar.length === 0) {
    return (
      <a href="/konsol/dosyalar" className="dugme dugme-sade">
        Dosya oluştur → kaydet
      </a>
    );
  }

  return (
    <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
      <Secici
        baslik="Dosya"
        deger={secili}
        secenekler={dosyalar.map((d) => ({ deger: d.id, etiket: d.ad }))}
        onSec={setSecili}
        genislik={200}
      />
      <button type="button" className="dugme dugme-sade" onClick={kaydet} disabled={durum === "kaydediliyor"}>
        {durum === "kaydedildi"
          ? "dosyaya eklendi"
          : durum === "hata"
            ? "kaydedilemedi"
            : "Dosyaya kaydet"}
      </button>
    </span>
  );
}
