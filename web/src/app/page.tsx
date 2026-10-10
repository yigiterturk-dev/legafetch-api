import React from "react";
import Ust, { Alt } from "@/components/ust";

// Lemon Squeezy mağazası açıldığında LS_MAGAZA_URL env'i verilir; düğme o zaman
// belirir. Tanımsızken sayfa birebir bugünkü hâlinde kalır (build-time sabittir).
const MAGAZA = process.env.LS_MAGAZA_URL?.trim();

export const metadata = {
  title: "LegaFetch — Türk hukuk külliyatında anlam tabanlı arama",
  description:
    "9,87 milyon pasajlık Türk yargı kararı ve mevzuat külliyatında anlam eşleşmesiyle arama. Cevap yalnızca bulunan pasajlara dayandırılır ve her iddia kaynağına atıflanır.",
};

const NEDEN = [
  {
    baslik: "Kelimeyi değil kavramı arar",
    metin:
      "Sorgu bir vektöre çevrilir ve külliyattaki pasajlarla anlam yakınlığına göre eşleştirilir. Aradığınız kavramın başka kelimelerle yazıldığı kararlar da çıkar — aynı ifadeyi tutturmanız gerekmez.",
  },
  {
    baslik: "Cevabı kaynağa bağlar",
    metin:
      "Bulunan pasajlar bir dil modeline verilir ve cevap YALNIZCA o pasajlara dayanarak yazılır; her iddia [n] biçiminde ilgili pasaja atıflanır. Kullanılan kaynaklar cevabın altında listelenir, doğrulaması sizde kalır.",
  },
  {
    baslik: "Belgeden mevzuata",
    metin:
      "Bir sözleşme ya da dilekçe yükleyin; metinden çıkarılan konuların mevzuat karşılığı aranır. Belge sunucuda saklanmaz.",
  },
];

const SINIRLAR = [
  "Külliyat ağırlıklı olarak içtihattır; mevzuat tarafı 73 kanunla sınırlıdır — yönetmelik ve tebliğler henüz yok.",
  "Cevabı bir dil modeli yazar. Yalnızca bulunan pasajlara dayanması istenir ama bu garanti değildir; atıfları açıp okuyun.",
  "Sorgunuz ve eşleşen pasajlar OpenAI'ye (gpt-4o-mini) gönderilir. Sözleşme denetiminde YÜKLEDİĞİNİZ SÖZLEŞMENİN METNİ, dilekçe üretiminde ANLATTIĞINIZ MADDİ OLAY da gönderilir. Müvekkil adı, TCKN, dosya numarası gibi tanıtıcı bilgileri metinden çıkarın.",
  "Motor hukuki görüş üretmez. Çıkan sonucun olayınıza uygunluğunu siz değerlendirirsiniz.",
  "Kararların güncelliği hasat tarihiyle sınırlıdır; kritik işlerde resmî kaynaktan doğrulayın.",
  "Tek sunucuda çalışır, yedekli (HA) değildir. Beta.",
];

export default function TanitimSayfasi() {
  return (
    <>
      <Ust />
      <main>
        <section className="kap" style={{ paddingTop: 72, paddingBottom: 8 }}>
          <p className="tek kucuk" style={{ letterSpacing: ".06em", textTransform: "uppercase" }}>
            Hukuk araştırma motoru
          </p>
          <h1 style={{ marginTop: 14, maxWidth: "18ch", fontSize: 40 }}>
            Doğru kararı, doğru kelimeyi bilmeden bulun
          </h1>
          <p className="spot" style={{ marginTop: 16 }}>
            LegaFetch, Türk yargı kararları ve mevzuat metinlerinden oluşan 9,87
            milyon pasajlık bir külliyatta anlam tabanlı arama yapar. Soruyu
            gündelik dille yazarsınız; motor, kelime eşleşmesine değil kavram
            yakınlığına bakar; bulduğu pasajlardan atıflı bir cevap çıkarır ve
            kullandığı kaynakları yanında gösterir.
          </p>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 28 }}>
            {MAGAZA && (
              <a href={MAGAZA} className="dugme dugme-ana" target="_blank" rel="noreferrer">
                Hemen satın al
              </a>
            )}
            <a href="/login" className={MAGAZA ? "dugme dugme-sade" : "dugme dugme-ana"}>
              Lisans anahtarıyla gir
            </a>
            <a
              href="mailto:iletisim@legafetch.com?subject=LegaFetch%20eri%C5%9Fim%20talebi"
              className="dugme dugme-sade"
            >
              Erişim iste
            </a>
          </div>

          <div className="sayac" style={{ marginTop: 40 }}>
            <div>
              <span>9.860.914</span>
              <small>yargı kararı pasajı</small>
            </div>
            <div>
              <span>15.479</span>
              <small>mevzuat pasajı (73 kanun)</small>
            </div>
            <div>
              <span>4 sn</span>
              <small>tipik sorgu süresi</small>
            </div>
          </div>
          <p className="kucuk">
            Sayılar 20 Eylül 2026&apos;da külliyattan ölçülmüştür. Kaynaklar:
            Yargıtay, Danıştay ve AYM kararları ile yürürlükteki kanun metinleri.
          </p>
        </section>

        <section className="kap" style={{ paddingTop: 56 }}>
          <h2>Ne yapar</h2>
          <div className="uclu" style={{ marginTop: 20 }}>
            {NEDEN.map((n) => (
              <div key={n.baslik} className="kart kart-dolgu">
                <h3>{n.baslik}</h3>
                <p className="kucuk" style={{ marginTop: 8 }}>
                  {n.metin}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="kap" style={{ paddingTop: 56 }}>
          <h2>Nasıl çalışır</h2>
          <ol
            className="kucuk"
            style={{ marginTop: 16, paddingLeft: 20, display: "grid", gap: 10, maxWidth: "70ch" }}
          >
            <li>
              Soruyu yazarsınız — &quot;kıdem tazminatına esas ücrete hangi
              ödemeler dâhildir&quot; gibi, madde numarası bilmeniz gerekmez.
            </li>
            <li>
              Sorgu hem anlam (yoğun vektör) hem kelime (seyrek indeks) tarafında
              aranır, iki koldan aday pasajlar çıkar.
            </li>
            <li>
              Adaylar yeniden sıralanır; kanun ve yüksek mahkeme kararları alt
              derece içtihadın önüne alınır.
            </li>
            <li>
              Seçilen pasajlar bir dil modeline verilir; cevap yalnızca o
              pasajlara dayanarak, atıflarıyla birlikte yazılır. Kaynakları
              açıp doğrulayıp kullanırsınız.
            </li>
          </ol>
        </section>

        <section className="kap" style={{ paddingTop: 56 }}>
          <h2>Kimin için</h2>
          <p className="spot" style={{ marginTop: 12 }}>
            Emsal karar taramasına vakit harcayan avukat ve hukuk büroları,
            araştırmacılar ve kendi uygulamasına hukuk araması gömmek isteyen
            geliştiriciler için. Arayüzden de kullanılır,{" "}
            <a href="/documentation" style={{ color: "var(--marka)" }}>
              API&apos;den de
            </a>
            .
          </p>
        </section>

        <section className="kap" style={{ paddingTop: 56 }}>
          <h2>Dürüst sınırlar</h2>
          <ul
            className="kucuk"
            style={{ marginTop: 14, paddingLeft: 20, display: "grid", gap: 8, maxWidth: "70ch" }}
          >
            {SINIRLAR.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </section>

        <section className="kap" style={{ paddingTop: 48 }}>
          <div
            className="kart kart-dolgu"
            style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center", justifyContent: "space-between" }}
          >
            <div>
              <h3>Erişim lisans anahtarıyla açılır</h3>
              <p className="kucuk" style={{ marginTop: 6 }}>
                Anahtarınız varsa doğrudan girin; yoksa yazın, kısa bir deneme
                erişimi açalım.
              </p>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <a href="/login" className="dugme dugme-ana">
                Giriş yap
              </a>
              <a
                href="mailto:iletisim@legafetch.com?subject=LegaFetch%20eri%C5%9Fim%20talebi"
                className="dugme dugme-sade"
              >
                Erişim iste
              </a>
            </div>
          </div>
        </section>
      </main>
      <Alt />
    </>
  );
}
