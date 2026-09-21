import React from "react";
import Ust, { Alt } from "@/components/ust";

export const metadata = { title: "Kullanım koşulları — LegaFetch" };

export default function KosullarSayfasi() {
  return (
    <>
      <Ust />
      <main className="kap kap-dar" style={{ paddingTop: 40 }}>
        <h1>Kullanım koşulları</h1>
        <p className="kucuk" style={{ marginTop: 8 }}>Son güncelleme: 21 Eylül 2026</p>

        <div style={{ display: "grid", gap: 20, marginTop: 28 }}>
          <section>
            <h2>Hizmetin kapsamı</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              LegaFetch, Türk yargı kararları ve mevzuat metinleri üzerinde arama
              yapan bir yazılımdır. Hukuki danışmanlık vermez, avukatlık hizmeti
              sunmaz ve dönen sonuçlar hukuki görüş niteliği taşımaz. Sonucu
              kullanmadan önce kaynağından doğrulamak kullanıcıya aittir.
            </p>
          </section>

          <section>
            <h2>Erişim</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Erişim, size verilen lisans anahtarıyla sağlanır. Anahtarın
              gizliliğinden siz sorumlusunuz; paylaşılan anahtarla yapılan
              kullanım size ait sayılır. Hız sınırlarını aşan, otomatik toplu
              çekim yapan ya da külliyatı kopyalamaya yönelen kullanımda erişim
              durdurulabilir.
            </p>
          </section>

          <section>
            <h2>Garanti ve sorumluluk</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Hizmet &quot;olduğu gibi&quot; sunulur. Sonuçların eksiksizliği,
              güncelliği veya belirli bir amaca uygunluğu garanti edilmez.
              Külliyat eksik kaynak içerebilir. Hizmetin kesintiye uğraması
              mümkündür; tek sunucu üzerinde çalışır.
            </p>
          </section>

          <section>
            <h2>Değişiklik</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Koşullar değişirse bu sayfa güncellenir ve güncelleme tarihi
              yukarıda görünür.
            </p>
          </section>
        </div>
      </main>
      <Alt />
    </>
  );
}
