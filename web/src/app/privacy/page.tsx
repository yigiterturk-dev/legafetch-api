import React from "react";
import Ust, { Alt } from "@/components/ust";

export const metadata = { title: "Gizlilik — LegaFetch" };

export default function GizlilikSayfasi() {
  return (
    <>
      <Ust />
      <main className="kap kap-dar" style={{ paddingTop: 40 }}>
        <h1>Gizlilik</h1>
        <p className="kucuk" style={{ marginTop: 8 }}>Son güncelleme: 21 Eylül 2026</p>

        <div style={{ display: "grid", gap: 20, marginTop: 28 }}>
          <section>
            <h2>Nerede çalışıyor</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Hizmet, bizim işlettiğimiz adanmış bir sunucuda barındırılır.
              Arama zinciri — gömme, vektör araması, yeniden sıralama — aynı
              makinede çalışır. Sorgunuz veya yüklediğiniz belge herhangi bir
              dil modeli sağlayıcısına ya da üçüncü tarafa gönderilmez.
            </p>
          </section>

          <section>
            <h2>Yüklenen belgeler</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Belge işlenmek üzere belleğe alınır, metni çıkarılır ve istek
              bitince bırakılır; diske yazılmaz ve külliyata eklenmez.
            </p>
          </section>

          <section>
            <h2>Kayıtlar</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Sunucu, işletim ve kötüye kullanım tespiti için erişim kaydı tutar:
              istek zamanı, yol, durum kodu, IP adresi ve tarayıcı bilgisi.
              Kayıtlar sınırlı boyutta tutulur ve dönüşümlü olarak silinir.
              Kayıtlar reklam veya profilleme için kullanılmaz, satılmaz.
            </p>
          </section>

          <section>
            <h2>Çerez</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Yalnızca oturum çerezi kullanılır. İmzalıdır, yalnız sunucuya
              gönderilir (httpOnly) ve oturumun açık olduğunu taşımaktan başka
              bir şey içermez. İzleme çerezi ve üçüncü taraf analitiği yoktur.
            </p>
          </section>

          <section>
            <h2>İletişim</h2>
            <p className="kucuk" style={{ marginTop: 6 }}>
              Sorular ve silme talepleri için{" "}
              <a href="mailto:iletisim@legafetch.com" style={{ color: "var(--marka)" }}>
                iletisim@legafetch.com
              </a>
              .
            </p>
          </section>
        </div>
      </main>
      <Alt />
    </>
  );
}
