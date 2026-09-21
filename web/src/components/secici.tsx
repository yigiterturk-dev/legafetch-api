"use client";

import React, { useEffect, useRef, useState } from "react";

export type Secenek = { deger: string; etiket: string; ipucu?: string };

/**
 * Native <select> kullanılmıyor: tarayıcı açılır listesi kendi zeminini ve
 * yazı tipini dayatıyor, tasarım dilinin dışına düşüyordu. Stilleri
 * globals.css'teki .secici-* sınıflarında.
 */
export default function Secici({
  deger,
  secenekler,
  onSec,
  baslik,
  genislik = 190,
}: {
  deger: string;
  secenekler: Secenek[];
  onSec: (d: string) => void;
  baslik: string;
  genislik?: number;
}) {
  const [acik, setAcik] = useState(false);
  const kutuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!acik) return;
    const disaridaTikla = (e: MouseEvent) => {
      if (!kutuRef.current?.contains(e.target as Node)) setAcik(false);
    };
    const kacis = (e: KeyboardEvent) => e.key === "Escape" && setAcik(false);
    document.addEventListener("mousedown", disaridaTikla);
    document.addEventListener("keydown", kacis);
    return () => {
      document.removeEventListener("mousedown", disaridaTikla);
      document.removeEventListener("keydown", kacis);
    };
  }, [acik]);

  const secili = secenekler.find((s) => s.deger === deger) ?? secenekler[0];

  return (
    <div className="secici" ref={kutuRef} style={{ width: genislik }}>
      <button
        type="button"
        className="secici-dugme"
        style={{ width: "100%", justifyContent: "space-between" }}
        aria-haspopup="listbox"
        aria-expanded={acik}
        aria-label={baslik}
        onClick={() => setAcik((o) => !o)}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {secili?.etiket}
        </span>
        <span aria-hidden style={{ color: "var(--metin-3)", fontSize: 11 }}>
          {acik ? "▲" : "▼"}
        </span>
      </button>
      {acik && (
        <div className="secici-liste" role="listbox" aria-label={baslik}>
          {secenekler.map((s) => (
            <button
              key={s.deger}
              type="button"
              role="option"
              aria-selected={s.deger === deger}
              className="secici-secenek"
              onClick={() => {
                onSec(s.deger);
                setAcik(false);
              }}
            >
              <span>{s.etiket}</span>
              {s.ipucu && <span className="kucuk tek">{s.ipucu}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
