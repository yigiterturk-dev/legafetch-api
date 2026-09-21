"use client";

import React, { useState } from "react";

export type Kaynak = {
  source: string;
  authority_score: number;
  jurisdiction?: string;
  metin?: string;
  tarih?: string;
  daire?: string;
  esasNo?: string;
  kararNo?: string;
  kurum?: string;
  belgeSinifi?: string;
  docId?: string;
};

// authority_score bir GÜVEN yüzdesi değil, kaynağın kademesinden türetilmiş
// sıralama puanı. Ekranda yüzde gibi göstermiyoruz.
export function kademeAdi(puan: number): string {
  if (puan >= 95) return "Kanun / AYM";
  if (puan >= 85) return "Yargıtay / Danıştay";
  if (puan >= 70) return "İstinaf";
  return "Diğer içtihat";
}

/**
 * Kaynak metni mevzuat-mcp'den markdown olarak geliyor: madde başlıkları
 * `**MADDE 23**` biçiminde. Ekranda yıldızları ham göstermek çirkin ve
 * kullanıcıyı "bu metin bozuk mu" diye düşündürüyor; sadece soyuyoruz.
 */
function pasajiTemizle(m?: string): string {
  return (m || "")
    .replace(/\*\*/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function trTarih(iso?: string): string {
  if (!iso || iso.length < 10) return "";
  const [y, a, g] = iso.slice(0, 10).split("-");
  return `${g}.${a}.${y}`;
}

/** "Yargıtay kararı 9. Hukuk Dairesi, E. 2019/3421, K. 2020/1234, T. 12.03.2020" */
export function atifMetni(k: Kaynak): string {
  if (k.belgeSinifi !== "yargi-karari") return k.source;
  const parcalar: string[] = [];
  const merci = [k.kurum?.replace(/ kararı$/, ""), k.daire]
    .filter(Boolean)
    .join(" ")
    .trim();
  parcalar.push(merci || k.source);
  if (k.esasNo) parcalar.push(`E. ${k.esasNo}`);
  if (k.kararNo) parcalar.push(`K. ${k.kararNo}`);
  const t = trTarih(k.tarih);
  if (t) parcalar.push(`T. ${t}`);
  return parcalar.join(", ");
}

export default function KaynakKarti({
  kaynak,
  no,
  kimlik,
}: {
  kaynak: Kaynak;
  no: number;
  kimlik: string;
}) {
  const [acik, setAcik] = useState(false);
  const [kopyalandi, setKopyalandi] = useState(false);
  const meta = [
    trTarih(kaynak.tarih),
    kaynak.esasNo ? `E. ${kaynak.esasNo}` : "",
    kaynak.kararNo ? `K. ${kaynak.kararNo}` : "",
  ].filter(Boolean);

  const kopyala = async () => {
    try {
      await navigator.clipboard.writeText(atifMetni(kaynak));
      setKopyalandi(true);
      setTimeout(() => setKopyalandi(false), 1600);
    } catch {
      /* pano izni yoksa sessiz geç */
    }
  };

  return (
    <div className="kaynak-kart" id={kimlik}>
      <div className="kaynak-kart-ust">
        <span className="kaynak-no tek">[{no}]</span>
        <div style={{ minWidth: 0, flex: 1 }}>
          <button
            type="button"
            className="kaynak-baslik"
            aria-expanded={acik}
            onClick={() => setAcik((o) => !o)}
            title={acik ? "Pasajı gizle" : "Pasaj metnini göster"}
          >
            {kaynak.source}
            <span aria-hidden className="kaynak-ok">{acik ? "▲" : "▼"}</span>
          </button>
          <div className="kaynak-meta">
            <span className="kademe">{kademeAdi(kaynak.authority_score)}</span>
            {kaynak.kurum && <span>{kaynak.kurum}</span>}
            {meta.map((m) => (
              <span key={m} className="tek">{m}</span>
            ))}
          </div>
        </div>
        <button type="button" className="dugme-yazi kaynak-kopya" onClick={kopyala}>
          {kopyalandi ? "kopyalandı" : "atıf kopyala"}
        </button>
      </div>
      {acik && (
        <div className="kaynak-pasaj">
          {kaynak.metin?.trim() ? (
            pasajiTemizle(kaynak.metin)
          ) : (
            <span className="kucuk">Bu kaynak için pasaj metni dönmedi.</span>
          )}
        </div>
      )}
    </div>
  );
}
