"""Komsu madde hatasi: reranker mi zayif, yoksa DOGRU maddenin metninde
aranan terim hic gecmiyor mu?

Eger dogru maddenin metninde sorgunun anahtar ifadesi YOKSA, hicbir
reranker onu secemez — o zaman dert ithalattaki KENAR BASLIGI eksigidir
(Turk kanunlarinda her maddenin kenar basligi vardir: "Yoksulluk
nafakasi", "Itirazin iptali"; payload'daki 'baslik' alani ise jenerik:
"Turk Medeni Kanunu — MADDE 175").
"""
import main
import mevzuat_bm25
from qdrant_client.models import FieldCondition, Filter, MatchValue

# (dogru docId, yanlis gelen docId, sorgudaki ayirt edici ifade)
VAKALAR = [
    ("mevzuat-4721-madde-175", "mevzuat-4721-madde-176", "yoksulluk nafakasi"),
    ("mevzuat-657-madde-125", "mevzuat-657-madde-126", "disiplin cezalari"),
    ("mevzuat-6100-madde-119", "mevzuat-6100-madde-129", "dava dilekcesi"),
    ("mevzuat-5237-madde-158", "mevzuat-5237-madde-157", "nitelikli dolandiricilik"),
    ("mevzuat-2577-madde-7", "mevzuat-2577-madde-10", "dava acma suresi"),
    ("mevzuat-6098-madde-49", "mevzuat-6100-madde-16", "haksiz fiil"),
    ("mevzuat-3194-madde-32", "mevzuat-3194-madde-26", "ruhsatsiz yapi"),
    ("mevzuat-4857-madde-18", "mevzuat-4857-madde-20", "gecerli sebep"),
]


def metin_al(doc_id):
    pts, _ = main.client.scroll(
        main.collection_name,
        scroll_filter=Filter(must=[FieldCondition(key="docId", match=MatchValue(value=doc_id))]),
        limit=5, with_payload=True, with_vectors=False,
    )
    return " ".join((p.payload.get("metin") or "") for p in pts)


kayip = 0
for dogru, yanlis, ifade in VAKALAR:
    md = mevzuat_bm25.normalize(metin_al(dogru))
    my = mevzuat_bm25.normalize(metin_al(yanlis))
    d_var = ifade in md
    y_var = ifade in my
    # ifadenin kelimeleri ayri ayri geciyor mu (tam ifade yoksa)
    kelimeler = ifade.split()
    d_kelime = sum(1 for k in kelimeler if k in md)
    if not d_var:
        kayip += 1
    isaret = "✅" if d_var else "🔴"
    print(f"{isaret} '{ifade}'")
    print(f"     DOGRU  {dogru:<28} tam ifade: {d_var} | kelime {d_kelime}/{len(kelimeler)} | uzunluk {len(md)}")
    print(f"     gelen  {yanlis:<28} tam ifade: {y_var}")

print(f"\n🔴 dogru maddenin metninde aranan ifade GECMEYEN vaka: {kayip}/{len(VAKALAR)}")
print("   (yuksekse dert reranker degil, ithalattaki kenar basligi eksigi)")
