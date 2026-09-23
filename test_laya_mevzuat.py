"""laya_mevzuat mekanik test — SENTEZİK (uydurma) maddelerle, kulliyat gerektirmez.

Gerçek verdict kulliyatli eval_laya.py'den gelir; bu test sadece:
 1) arayüz dogru calisiyor mu (jev_mevzuat ile birebir sekil)
 2) skorlar hedefi distraktordan ayiriyor mu
 3) servis cokerse fallback calisiyor mu (bos sozluk -> bge sirasi)
 4) gecikme
"""
import time

import laya_mevzuat


class Doc:
    def __init__(self, docid, metin):
        self.metadata = {"docId": docid, "source": docid}
        self.page_content = metin


# --- SENTEZIK PARAFRANSLAR (gercek metin degil; mekanik test icin) ---
CASES = [
    ("Kosullu saliverilme orani kac yildir? Beklenen: 5275-107, tuzak: 3713-17",
     Doc("5275-107", "Ceza ve Guvenlik Tedbirlerinin Infazina Iliskin Kanun madde 107: "
         "Hukumlu, cezasinin yarisi gectikten sonra kosullu saliverilebilir. Agirlastirici "
         "mudet cezalarinda uyulmasi gereken oran, cezanin turune gore uctan ikiye kadar "
         "degisen kat sayilarla belirlenir. Iyi hal hali koşulları saklıdır."),
     [Doc("5275-107", "Madde 107 - Kosullu saliverilmede ceza yarisi gecince talep edilebilir; "
          "agirlastirici mudet cezalarinda oran kat sayilariyla hesaplanir."),
      Doc("3713-17", "Madde 17 - Cocuklara ozel guvenlik tedbirleri uygulanir; "
          "koruma kararlari hakim karariyla verilir, itiraz edilebilir."),
      Doc("5275-9", "Madde 9 - Ceza infaz kurumlarinda uyum calismalari yurutulur; "
          "sosal hizmet uzmanlari gorev yapar; egitim programlari planlanir."),
      Doc("6136-4", "Madde 4 - Atesli silah ve mermi bulundurma izni ilgili idarece verilir; "
          "ruhsatsiz bulundurma su olusturur."),
      Doc("5237-53", "Madde 53 - Bazi haklardan yoksun birakma; kamu hizmeti yasagi, "
          "meslek ve sanat yasagi halleri sureleriyle birlikte duzenlenir."),
      Doc("5271-231", "Madde 231 - Hukmun aciklanmasinin geri birakilmasi; denetim suresi, "
          "yukumluluklar, sure icinde kasitli suç islenmesi halinde hukum kesinlesir.")]),
    ("Yabanci hangi hallerde sinir disi edilir? Beklenen: 6458-54, tuzak: komsu 6458-53",
     Doc("6458-54", "Yabancilar ve Uluslararasi Koruma Kanunu madde 54: Sinir disi etme "
         "karari valilik tarafindan verilir; ulusal guvenlik, kamu duzeni veya kamu sagligi "
         "acisindan ciddi tehlike bulunan yabancilar hakkinda uygulanir; idari gozetim sartlari"),
     [Doc("6458-54", "Madde 54 - Sinir disi etme karari valilikce verilir; ulusal guvenlik, "
          "kamu duzeni ve kamu sagligi tehlikesi bulunanlar hakkinda uygulanir."),
      Doc("6458-53", "Madde 53 - Sinir disi etme karari, kararin tebliği ve yürürlüğü; "
          "kararin gerekceleri, itiraz yollari ve bildirim kurallari bu maddede yer alir."),
      Doc("6458-55", "Madde 55 - Geri itilme yasaği; uluslararasi koruma basvurularinin "
          "degerlendirilmesi sirasinda temel ilkeler."),
      Doc("6706-5", "Madde 5 - Uluslararasi isbirligi ilkeleri, karsiliklilik ve "
          "adli yardimlasma taleplerinin karsi tarafa iletme usulu."),
      Doc("5237-59", "Madde 59 - Yabancilara ozel guvenlik tedbiri; turkiye'de ikamet "
          "yasagi ve sinir disi etme cezasinin infazi."),
      Doc("4864-7", "Madde 7 - Goc idaresi teskilatinin gorev ve yetkileri; veri tabani, "
          "izleme ve bildirim yukumlulukleri.")]),
    ("Kisisel verilerimin silinmesini talep edebilir miyim? Beklenen: 6698-7",
     Doc("6698-7", "Kisisel Verilerin Korunmasi Kanunu madde 7: Veri sorumlusu, bu Kanun ve "
         "diger kanunlarin ongordugu haklarin silinmesi veya yok edilmesi gerekli haller "
         "ortak kalktiginda resen ya da ilgili kisinin talebi uzerine siler, yok eder "
         "veya anonim hale getirir."),
     [Doc("6698-7", "Madde 7 - Silme, yok etme veya anonim hale getirme; gerekleri ortadan "
          "kalktiginda resen veya talep uzerine silinir."),
      Doc("6698-5", "Madde 5 - Kisisel veri isleme sartlari; acik riza veya kanundaki "
          "istisnalar cercevesinde isleme yapilabilir."),
      Doc("6698-11", "Madde 11 - Ilgili kisinin haklari: ogrenme, duzeltme, silme, "
          "aktarimin bildirilmesi ve zararin giderilmesini talep etme."),
      Doc("6698-12", "Madde 12 - Veri guvenligine iliskin yukumlulukler; ihlal bildirimi, "
          "gizlilik yukumlulugu ve tedbirler."),
      Doc("6098-137", "Madde 137 - Veri kayit sistemlerini hukuka sayarak bozma, silme, "
          "yok etme; cezai sorumluluk halleri."),
      Doc("6102-138", "Madde 138 - Elektronik ortamda veri yok etme sucu; banka ve "
          "sirket kayitlarina iliskin ozel haller.")]),
]


def metin_al(d):
    return f"{d.metadata.get('source', '')}\n{d.page_content or ''}"


print("== 1) MEKANIK TEST: alaka_skorla sekli + siralama ==")
ok = 0
for i, (soru, hedef, adaylar) in enumerate(CASES, 1):
    t0 = time.time()
    skor = laya_mevzuat.alaka_skorla(soru, adaylar, metin_al)
    ms = (time.time() - t0) * 1000
    if not skor:
        print("  case {}: SKOR YOK (fallback devrede)".format(i))
        continue
    sira = sorted(skor, key=lambda k: skor[k], reverse=True)
    birinci = adaylar[sira[0]].metadata["docId"]
    ok_mu = birinci == hedef.metadata["docId"]
    ok += ok_mu
    print("  case {}: ilk={} {} | skorlar={} | {:.0f} ms".format(
        i, birinci, "OK" if ok_mu else "MISS",
        {j: round(v, 3) for j, v in sorted(skor.items())}, ms))

print("\n== 2) FALLBACK TESTI: yanlis URL -> bos sozluk ==")
laya_mevzuat.LAYA_URL = "http://127.0.0.1:59999"
laya_mevzuat.LAYA_TIMEOUT = 3
soru, hedef, adaylar = CASES[0][0], CASES[0][1], CASES[0][2]
skor = laya_mevzuat.alaka_skorla(soru, adaylar, metin_al)
donen = laya_mevzuat.sirala(soru, adaylar, metin_al)
print("  skor:", skor, "-> fallback", "OK (sira korunur)" if donen == adaylar else "BOZUK")

print("\n== 3) OZET: {}/{} hedef ilk sirada (sentezik metinlerle)".format(ok, len(CASES)))
