import React from "react";
import Ust, { Alt } from "@/components/ust";

export const metadata = { title: "Altyapı — LegaFetch" };

export default function AltyapiSayfasi() {
  return (
    <>
      <Ust />
      <main className="kap kap-dar" style={{ paddingTop: 40 }}>
        <h1>Altyapı</h1>
        <p className="spot" style={{ marginTop: 12 }}>
          Sistem, bize ait tek bir adanmış sunucuda çalışır. Arama zinciri
          uçtan uca kendi makinemizdedir; sorgu ya da belge herhangi bir dil
          modeli sağlayıcısına gönderilmez.
        </p>

        <div className="uclu" style={{ marginTop: 32 }}>
          <div className="kart kart-dolgu">
            <h3>Vektör veritabanı</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Qdrant. İki koleksiyon: yoğun vektörler 9.860.914 pasaj, seyrek
              (kelime tabanlı) 6.242.036 pasaj. Külliyatın 8.362 pasajı mevzuat,
              kalanı yargı kararı.
            </p>
          </div>
          <div className="kart kart-dolgu">
            <h3>Gömme ve yeniden sıralama</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Çok dilli açık kaynak gömme modeli ve BGE yeniden sıralayıcı,
              aynı sunucuda CPU üzerinde çalışır. Dışarıya model çağrısı yoktur.
            </p>
          </div>
          <div className="kart kart-dolgu">
            <h3>API katmanı</h3>
            <p className="kucuk" style={{ marginTop: 6 }}>
              FastAPI. Hız sınırı, anahtar doğrulaması ve sağlık ucu buradadır;
              önünde TLS sonlandıran Caddy durur.
            </p>
          </div>
        </div>

        <h2 style={{ marginTop: 40 }}>Dürüst sınırlar</h2>
        <ul className="kucuk" style={{ marginTop: 10, paddingLeft: 18, display: "grid", gap: 8 }}>
          <li>
            Külliyat ağırlıklı olarak içtihattır. Mevzuat tarafı 19 kanunla
            sınırlıdır; aradığınız kanun külliyatta olmayabilir.
          </li>
          <li>
            Motor yorum üretmez, özet yazmaz. Dönen metin kaynağın kendi
            ifadesidir.
          </li>
          <li>
            Kararların güncelliği hasat tarihiyle sınırlıdır; sonucu resmî
            kaynağından doğrulayın.
          </li>
          <li>Tek sunucu üzerinde çalışır; yedekli çalışma (HA) yoktur.</li>
        </ul>

        <p className="kucuk" style={{ marginTop: 24 }}>
          Sayılar 20 Eylül 2026&apos;da koleksiyonlardan ölçülmüştür.
        </p>
      </main>
      <Alt />
    </>
  );
}
