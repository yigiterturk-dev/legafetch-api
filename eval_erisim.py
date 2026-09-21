"""LegaFetch ERİŞİM ÖLÇÜM SETİ — 20 soru, beklenen kaynak, hit@5 + MRR.

Neden bu dosya: eval_rerank.py ve audit_sorgular.sh sorguları ASCII yazıyordu
("kidem tazminati") — e5 gömmesi Türkçe diakritiklere duyarlı, korpus
diakritikli. Tüm geçmiş kalite ölçümleri bu yüzden tuzağın içindeydi.
Ayrıca ikisinde de "beklenen kaynak" yoktu: ne döndüğüne bakıyor, DOĞRU mu
diye bakmıyorlardı. Burada her sorunun cevabı önceden yazılı.

Beklenen kaynaklar korpustaki 19 kanundan seçildi (olmayan kanunu sormak
erişimi değil ithalatı ölçer).

Kullanım (api konteyneri içinde):
  docker exec -i legafetch-api python /app/eval_erisim.py [ascii]
"""
import re
import sys
import time

import main  # noqa: E402  (üretim hattını olduğu gibi kullanır)

K = 5

# (soru, beklenen docId deseni) — desen docId'ye uygulanır:
# docId formatı: mevzuat-<kanun_no>-madde-<madde_no>
SORULAR = [
    ("işçinin kıdem tazminatı hesabında giydirilmiş ücret nasıl bulunur",
     r"mevzuat-1475-madde-14\b"),
    ("işe iade davası ne kadar sürede açılır, feshin geçersizliği",
     r"mevzuat-4857-madde-(20|21)\b"),
    ("yıllık ücretli izin süresi kaç gündür",
     r"mevzuat-4857-madde-53\b"),
    ("belirsiz süreli iş sözleşmesinde ihbar öneli süreleri nedir",
     r"mevzuat-4857-madde-17\b"),
    ("işverenin haklı nedenle derhal fesih hakkı hangi hallerde doğar",
     r"mevzuat-4857-madde-25\b"),
    ("konut kirasında kira bedelinin belirlenmesi ve artış sınırı",
     r"mevzuat-6098-madde-344\b"),
    ("kiraya verenin gereksinimi nedeniyle kiracının tahliyesi",
     r"mevzuat-6098-madde-350\b"),
    ("kat maliklerinin ortak gider ve avans payı yükümlülüğü",
     r"mevzuat-634-madde-20\b"),
    ("kat malikleri kurulu toplantı ve karar yeter sayısı",
     r"mevzuat-634-madde-(29|30|32)\b"),
    ("itirazın iptali davası hangi sürede açılır",
     r"mevzuat-2004-madde-67\b"),
    ("ödeme emrine itiraz süresi kaç gündür",
     r"mevzuat-2004-madde-6[02]\b"),
    ("ihtiyati haciz kararı hangi şartlarda verilir",
     r"mevzuat-2004-madde-257\b"),
    ("dava şartları nelerdir, mahkemenin görevi",
     r"mevzuat-6100-madde-11[45]\b"),
    ("istinaf başvuru süresi kaç haftadır",
     r"mevzuat-6100-madde-345\b"),
    ("senetle ispat zorunluluğu ve delil başlangıcı",
     r"mevzuat-6100-madde-(200|202)\b"),
    ("evlilik birliğinin temelinden sarsılması nedeniyle boşanma",
     r"mevzuat-4721-madde-166\b"),
    ("mirasta saklı pay oranları nelerdir",
     r"mevzuat-4721-madde-506\b"),
    ("ayıplı malda tüketicinin seçimlik hakları nelerdir",
     r"mevzuat-6502-madde-11\b"),
    ("kişisel verilerin açık rıza olmadan işlenebileceği haller",
     r"mevzuat-6698-madde-5\b"),
    ("imar planlarına itiraz süresi ve askı süreci",
     r"mevzuat-3194-madde-8\b"),
]

# Diakritik soyma: aynı soruların ASCII hâli (tuzağın boyutunu ölçmek için)
TR2ASCII = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")


def _docid(d) -> str:
    md = d.metadata or {}
    return str(md.get("docId") or md.get("id") or "")


def _kaynak(d) -> str:
    return str((d.metadata or {}).get("source") or "")[:70]


def olc(sorular, yol, etiket: str):
    """yol: (sorgu, k) -> doc listesi. hit@5 ve MRR@5 döndürür."""
    hit = 0
    rr_top = 0.0
    sureler = []
    satirlar = []
    for soru, desen in sorular:
        t0 = time.time()
        try:
            docs = yol(soru, K)[:K]
        except Exception as e:  # ölçüm bir soruda patlarsa set durmasın
            satirlar.append(("HATA", soru, str(e)[:60]))
            continue
        sureler.append(time.time() - t0)
        rx = re.compile(desen)
        sira = 0
        for i, d in enumerate(docs, 1):
            if rx.search(_docid(d)):
                sira = i
                break
        if sira:
            hit += 1
            rr_top += 1.0 / sira
            satirlar.append((f"  ✓ @{sira}", soru[:52], _kaynak(docs[sira - 1])))
        else:
            ilk = _kaynak(docs[0]) if docs else "(boş)"
            satirlar.append(("  ✗    ", soru[:52], f"1.: {ilk}"))
    n = len(sorular)
    print(f"\n--- {etiket} ---")
    for s in satirlar:
        print(f"{s[0]} | {s[1]:<54} | {s[2]}")
    ort = sum(sureler) / len(sureler) if sureler else 0
    print(f"  => hit@{K} = {hit}/{n} (%{100*hit/n:.0f})   MRR@{K} = {rr_top/n:.3f}   "
          f"ort. {ort:.1f} sn/sorgu")
    return hit, rr_top / n


if __name__ == "__main__":
    ascii_mod = len(sys.argv) > 1 and sys.argv[1] == "ascii"
    sorular = SORULAR
    baslik = "TÜRKÇE"
    if ascii_mod:
        sorular = [(q.translate(TR2ASCII), d) for q, d in SORULAR]
        baslik = "ASCII (diakritiksiz)"

    print(f"LegaFetch erişim ölçümü — {len(sorular)} soru, k={K}, sorgu dili: {baslik}")
    olc(sorular, main.corpus_rank, f"{baslik} / corpus_rank (ÜRETİM: iki kol + rerank + zorla mevzuat)")
    olc(sorular, main.corpus_search, f"{baslik} / corpus_search (saf dense, enjeksiyonsuz)")
