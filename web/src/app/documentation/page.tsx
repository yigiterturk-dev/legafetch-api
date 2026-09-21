import React from "react";
import Ust, { Alt } from "@/components/ust";

export const metadata = { title: "API — LegaFetch" };

export default function ApiSayfasi() {
  return (
    <>
      <Ust />
      <main className="kap kap-dar" style={{ paddingTop: 40 }}>
        <h1>API</h1>
        <p className="spot" style={{ marginTop: 12 }}>
          Arama, kendi uygulamanızdan da çağrılabilir. Uç nokta{" "}
          <code className="tek">https://api.legafetch.com</code>, kimlik
          doğrulama <code className="tek">X-API-Key</code> başlığıyla yapılır.
          Anahtar tarayıcıya konmaz; isteği kendi sunucunuzdan atın.
        </p>

        <div className="konsol" style={{ marginTop: 28 }}>
          <div className="konsol-ust">
            <span className="tek">POST /api/chat</span>
            <span className="kucuk">arama</span>
          </div>
          <div className="konsol-govde" style={{ minHeight: 0, padding: 16 }}>
            <pre className="tek" style={{ fontSize: 13, lineHeight: 1.7, overflowX: "auto" }}>
{`curl -X POST https://api.legafetch.com/api/chat \\
  -H "X-API-Key: <anahtar>" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "kıdem tazminatına esas ücret"}'

# yanıt
{
  "text": "...eşleşen pasajların metni...",
  "sources": [
    { "source": "Yargıtay 9. HD", "authority_score": 90, "jurisdiction": "Global" }
  ]
}`}
            </pre>
          </div>
        </div>

        <div className="konsol" style={{ marginTop: 20 }}>
          <div className="konsol-ust">
            <span className="tek">POST /api/analyze-contract</span>
            <span className="kucuk">belgeden mevzuata</span>
          </div>
          <div className="konsol-govde" style={{ minHeight: 0, padding: 16 }}>
            <pre className="tek" style={{ fontSize: 13, lineHeight: 1.7, overflowX: "auto" }}>
{`curl -X POST https://api.legafetch.com/api/analyze-contract \\
  -H "X-API-Key: <anahtar>" \\
  -F "file=@sozlesme.pdf"

# yanıt: { "analysis": "...", "sources": [...] }`}
            </pre>
          </div>
        </div>

        <h2 style={{ marginTop: 36 }}>Bilinmesi gerekenler</h2>
        <ul className="kucuk" style={{ marginTop: 10, paddingLeft: 18, display: "grid", gap: 8 }}>
          <li>
            Dosya sınırı 10 MB, PDF&apos;lerde ilk 10 sayfa okunur; belge diske
            yazılmaz.
          </li>
          <li>
            <code className="tek">authority_score</code> bir güven yüzdesi
            değildir; kaynağın kademesinden türetilmiş sıralama puanıdır.
          </li>
          <li>
            <code className="tek">jurisdiction</code> alanı şu an tüm kayıtlarda
            <code className="tek"> Global</code> döner — külliyat Türk hukukudur,
            ülke süzgeci yoktur.
          </li>
          <li>
            İstek başına hız sınırı uygulanır; sınır aşılınca{" "}
            <code className="tek">429</code> döner.
          </li>
          <li>
            Bir sorgu tipik olarak birkaç saniye sürer. İstemci zaman aşımını
            60 saniyenin altına indirmeyin.
          </li>
        </ul>
      </main>
      <Alt />
    </>
  );
}
