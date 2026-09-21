# -*- coding: utf-8 -*-
"""LegaFetch ICTIHAT ERISIM OLCUM SETI — 28 soru, konu isabeti + merci isabeti.

NEDEN AYRI BIR SET: eval_erisim.py ve eval_dogrulama.py yalnizca MEVZUAT
kolunu olcuyor (beklenen docId = kanun maddesi). Oysa korpusun %99,94'u
ictihat. "Dogru karari buluyor mu" sorusunun bugune kadar tek bir sayisi
yoktu; bu dosya o bosluu kapatir.

NEDEN "beklenen karar" YOK: bir hukuki soruya cevap veren binlerce karar var.
9,86M pasaj icinden ONCEDEN SECILMIS tek karari ilk 5'te istemek hem haksiz
hem bilgisiz bir olcut olurdu (olculdu: rastgele cekilen kararlarin cogunun
konusu "kusur orani", "bilirkisi raporu" gibi jenerik). Bunun yerine iki
NESNEL olcut kullanilir:

  1. KONU ISABETI — donen kararin metninde, o konudaki HER kararin tasimak
     zorunda oldugu terim gruplari geciyor mu. Her grup alternatifli
     ("kidem|kıdem tazminat"), her grubun EN AZ BIRI gecmeli. Trafik kazasi
     sorusuna is kazasi karari donerse bu olcut yakalar.
  2. MERCI ISABETI — konunun ait oldugu daire/mahkeme geliyor mu. Kidem
     tazminati sorusuna Danistay donmesi, konu terimleri tutsa bile hatadir.

Olcut sozcukseldir, kusursuz degil: dogru konuda olup terimi baska kelimeyle
anlatan karari kacirir (yanlis NEGATIF). Yani rakam gercek kaliteden bir
miktar DUSUK cikar; egilimi ve karsilastirmayi olcmek icin yeterlidir.

Kullanim (api konteyneri icinde):
  docker exec -i legafetch-api python /app/eval_ictihat.py
"""
import re
import sys
import time

import main  # noqa: E402  (uretim hattini oldugu gibi kullanir)

K = 5

# (soru, [terim gruplari], beklenen merci deseni)
# Terim gruplari: her grup alternatiflerden olusur, hepsi kucuk harf ve
# TURKCE karakterli. Govde "icerir mi" diye bakilir (cekim eki toleransi:
# "nafaka" -> "nafakaya" da eslesir).
SORULAR = [
    ("işçinin kıdem tazminatına hak kazanabilmesi için aranan şartlar nelerdir",
     [["kıdem tazminat"], ["fesih", "feshin", "iş sözleşme"]],
     r"9\.|22\.|Hukuk Genel Kurulu"),
    ("işe iade davası kazanıldıktan sonra işe başlatmama tazminatı nasıl belirlenir",
     [["işe iade", "işe başlat"], ["tazminat"]],
     r"9\.|22\.|Hukuk Genel Kurulu"),
    ("fazla çalışma iddiası tanık beyanıyla ispatlanabilir mi, hakkaniyet indirimi",
     [["fazla çalışma", "fazla mesai"], ["tanık", "ispat"]],
     r"9\.|22\.|Hukuk Genel Kurulu"),
    ("sigortasız çalıştırılan işçinin hizmet tespiti davası nasıl görülür",
     [["hizmet tespit", "sigortalılık tespit", "sigortalılık başlangıç"],
      ["sigortalı", "çalışma"]],
     r"10\.|21\.|Hukuk Genel Kurulu"),
    ("iş kazası sonucu sürekli iş göremezlik nedeniyle maddi tazminat hesabı",
     [["iş kazası"], ["tazminat"]],
     r"10\.|21\.|Hukuk Genel Kurulu"),
    ("konut kirasında kira bedelinin tespiti davasında hangi ölçüt uygulanır",
     [["kira bedel"], ["tespit", "belirlen"]],
     r"3\.|6\.|Hukuk Genel Kurulu"),
    ("tahliye taahhüdüne dayalı tahliye davasında taahhüdün geçerlilik şartları",
     [["tahliye taahhüd", "tahliye taahhüt"], ["kiracı", "kiralayan", "kira"]],
     r"3\.|6\.|12\.|Hukuk Genel Kurulu"),
    ("kat malikinin ortak gider borcundan sorumluluğu ve icra takibi",
     [["ortak gider", "aidat", "kat mülkiyet"], ["sorumlu", "takip", "borç"]],
     r"18\.|20\.|3\.|Hukuk Genel Kurulu"),
    ("muris muvazaası nedeniyle tapu iptali ve tescil davasında ispat",
     [["muvazaa"], ["tapu iptal", "tescil", "miras"]],
     r"1\.|14\.|8\.|Hukuk Genel Kurulu"),
    ("saklı payı zedelenen mirasçının tenkis davası açma koşulları",
     [["tenkis"], ["saklı pay", "mirasçı", "miras"]],
     r"1\.|14\.|3\.|Hukuk Genel Kurulu"),
    ("evlilik birliğinin sarsılması nedeniyle boşanmada kusur belirlemesi",
     [["boşanma"], ["kusur"]],
     r"2\.|Hukuk Genel Kurulu"),
    ("yoksulluk nafakasının süresiz olması ve kaldırılması koşulları",
     [["yoksulluk nafaka"], ["nafaka"]],
     r"2\.|3\.|Hukuk Genel Kurulu"),
    ("çocuğun velayetinin belirlenmesinde üstün yararı ilkesi",
     [["velayet"], ["çocuğun", "üstün yarar", "idrak"]],
     r"2\.|Hukuk Genel Kurulu"),
    ("itirazın iptali davasında icra inkar tazminatına hükmedilmesinin şartları",
     [["itirazın iptal"], ["inkar tazminat", "inkâr tazminat", "likit"]],
     r"19\.|11\.|13\.|3\.|Hukuk Genel Kurulu"),
    ("markanın hükümsüzlüğü davasında karıştırılma ihtimali değerlendirmesi",
     [["marka"], ["hükümsüz", "karıştırılma", "iltibas", "benzerlik"]],
     r"11\.|Hukuk Genel Kurulu"),
    ("kambiyo senetlerine özgü haciz yolunda borca itiraz ve imza itirazı",
     [["kambiyo"], ["itiraz"]],
     r"12\.|19\.|11\.|Hukuk Genel Kurulu"),
    ("ihalenin feshi talebinde zarar unsuru ve süre",
     [["ihalenin feshi", "ihale"], ["fesih", "feshi"]],
     r"12\.|Hukuk Genel Kurulu"),
    ("trafik kazasında sigorta şirketinin rücu hakkı ve kusur oranı",
     [["trafik", "kaza"], ["sigorta"]],
     r"17\.|11\.|4\.|Hukuk Genel Kurulu"),
    ("kamulaştırma bedelinin tespiti davasında arazi için gelir yöntemi",
     [["kamulaştırma"], ["bedel"]],
     r"5\.|18\.|Hukuk Genel Kurulu"),
    ("imar planına karşı açılan iptal davasında şehircilik ilkeleri denetimi",
     [["imar plan"], ["iptal", "şehircilik", "planlama"]],
     r"Danıştay"),
    ("devlet memuruna verilen disiplin cezasının iptali davasında savunma hakkı",
     [["disiplin"], ["memur", "savunma", "soruşturma"]],
     r"Danıştay"),
    # --- ALT KONU AYIRT EDICILIGI -------------------------------------------
    # Bu 6 soru ayri bir sinifi olcer: sorunun ayirt edici terimi ("iki hakli
    # ihtar") ayni ust konunun yaygin kardesine ("ihtiyac nedeniyle tahliye")
    # kayiyor mu. Dense arama ust konuya yaklasip ayirt edici terimi eritmeye
    # egilimli; tahliye taahhudu sorusunda bu OLCULDU (2026-09-21).
    ("iki haklı ihtar nedeniyle kiralananın tahliyesi davası",
     [["iki haklı ihtar"], ["tahliye", "kira"]],
     r"3\.|6\.|12\.|Hukuk Genel Kurulu"),
    ("belirsiz alacak davası açmakta hukuki yarar bulunması şartı",
     [["belirsiz alacak"], ["hukuki yarar", "dava şart"]],
     r"9\.|22\.|Hukuk Genel Kurulu"),
    ("ıslah ile talep artırımında karşı tarafın zamanaşımı def'i",
     [["ıslah"], ["zamanaşım"]],
     r"9\.|22\.|11\.|Hukuk Genel Kurulu"),
    ("asıl işveren alt işveren ilişkisinde muvazaa iddiası",
     [["alt işveren"], ["muvazaa"]],
     r"9\.|22\.|Hukuk Genel Kurulu"),
    ("ticari defterlerin sahibi lehine delil olarak kullanılması",
     [["ticari defter"], ["delil"]],
     r"11\.|19\.|23\.|Hukuk Genel Kurulu"),
    ("ihtiyati tedbir kararına itiraz ve teminat",
     [["ihtiyati tedbir"], ["itiraz", "teminat"]],
     r"11\.|6\.|3\.|Hukuk Genel Kurulu"),
    ("vergi ziyaı cezalı tarhiyata karşı açılan davada re'sen takdir",
     [["vergi"], ["ceza", "tarhiyat", "takdir", "ziya"]],
     r"Danıştay"),
]


# Kararlar duzeltme isaretini ("velâyet", "kâr", "hâl") sorgudan farkli
# kullaniyor; olcut bunu ayri kelime sanmasin diye duzlestirilir.
SAPKA = {"â": "a", "î": "i", "û": "u", "Â": "a", "Î": "i", "Û": "u"}


def kucuk(s: str) -> str:
    """Turkce duyarli kucultme (I -> ı, İ -> i) + sapkali harf duzlestirme."""
    s = s.replace("I", "ı").replace("İ", "i").lower()
    return "".join(SAPKA.get(ch, ch) for ch in s)


def _koklu_gecer(terim: str, jetonlar) -> bool:
    """Cok kelimeli terim, kelimeleri BITISIK olmasa da sayilir.

    NEDEN: ilk surumde "hizmet tespit" dizgesi aranıyordu ve mahkemenin
    "sigortalı hizmetlerinin tespiti" yazdigi karar KACIRILIYORDU (olculdu
    2026-09-21: 4 yanlis negatiften 2'si buydu). Turkce cekim eki aldigi icin
    her kelime ONEK olarak aranir, sira ve bitisiklik aranmaz.
    """
    for kelime in kucuk(terim).split():
        if not any(j.startswith(kelime) for j in jetonlar):
            return False
    return True


def konuya_uygun(metin: str, gruplar) -> bool:
    jetonlar = re.findall(r"\w+", kucuk(metin), re.UNICODE)
    return all(any(_koklu_gecer(t, jetonlar) for t in grup) for grup in gruplar)


def ictihatlari_al(docs):
    """Sonuctan yalniz ictihat belgeleri, sirasi bozulmadan."""
    return [d for d in docs if d.metadata.get("tur") != "mevzuat"]


def olc(yol, etiket: str):
    print("\n--- %s ---" % etiket)
    konu_toplam = 0.0
    ilk_isabet = 0
    merci_isabet = 0
    bos = 0
    sure = 0.0
    for soru, gruplar, merci_deseni in SORULAR:
        t0 = time.time()
        try:
            docs = yol(soru, K * 3)
        except TypeError:
            docs = yol(soru)
        sure += time.time() - t0
        ic = ictihatlari_al(docs)[:K]
        if not ic:
            bos += 1
            print("  %-6s | %-52s | ICTIHAT DONMEDI" % ("-", soru[:52]))
            continue
        uygun = [konuya_uygun(d.page_content or "", gruplar) for d in ic]
        oran = sum(uygun) / len(ic)
        konu_toplam += oran
        if uygun[0]:
            ilk_isabet += 1
        merci_var = any(
            re.search(merci_deseni, d.metadata.get("source", "") or "") for d in ic
        )
        if merci_var:
            merci_isabet += 1
        print(
            "  %s%s | %-52s | konu %d/%d | %s"
            % (
                "✓" if uygun[0] else "✗",
                " M" if merci_var else " -",
                soru[:52],
                sum(uygun),
                len(ic),
                (ic[0].metadata.get("source", "") or "")[:44],
            )
        )
    n = len(SORULAR)
    print(
        "  => konu@1 = %d/%d (%%%d)   konu@5 ort = %.2f   merci@5 = %d/%d (%%%d)"
        % (
            ilk_isabet, n, 100 * ilk_isabet // n,
            konu_toplam / n,
            merci_isabet, n, 100 * merci_isabet // n,
        )
    )
    if bos:
        print("  !! %d soruda hic ictihat donmedi" % bos)
    print("  ort. %.1f sn/sorgu" % (sure / n))


if __name__ == "__main__":
    olc(main.corpus_rank, "ÜRETİM / corpus_rank (iki kol + rerank)")
    olc(main.corpus_search, "corpus_search (saf dense ictihat kolu)")
