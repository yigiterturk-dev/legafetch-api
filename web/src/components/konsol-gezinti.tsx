"use client";

import React from "react";
import { usePathname } from "next/navigation";

const SEKMELER = [
  { yol: "/konsol", ad: "Arama", aciklama: "Külliyatta anlam tabanlı arama" },
  { yol: "/konsol/dilekce", ad: "Dilekçe", aciklama: "Olaydan atıflı dilekçe taslağı" },
  { yol: "/konsol/sozlesme", ad: "Sözleşme", aciklama: "Yüklenen sözleşmenin risk denetimi" },
  { yol: "/konsol/dosyalar", ad: "Dosyalar", aciklama: "İş dosyaları ve içine kaydedilenler" },
  { yol: "/konsol/iscilik", ad: "İşçilik alacağı", aciklama: "Hizmet dökümünden kıdem/ihbar hesabı" },
  { yol: "/konsol/hesap", ad: "Hesaplayıcı", aciklama: "Kıdem, ihbar, faiz" },
  { yol: "/konsol/test", ad: "Saha testi", aciklama: "Cevapları değerlendirin — ürün geliştirme notu" },
];

export default function KonsolGezinti() {
  const yol = usePathname();
  return (
    <nav className="sekmeler" aria-label="Konsol bölümleri">
      {SEKMELER.map((s) => {
        const etkin = yol === s.yol;
        return (
          <a
            key={s.yol}
            href={s.yol}
            className={`sekme${etkin ? " sekme-etkin" : ""}`}
            aria-current={etkin ? "page" : undefined}
            title={s.aciklama}
          >
            {s.ad}
          </a>
        );
      })}
    </nav>
  );
}
