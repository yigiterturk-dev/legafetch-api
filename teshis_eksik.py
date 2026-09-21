"""Kacan sorularin beklenen maddeleri korpusta GERCEKTEN var mi?"""
import main
from qdrant_client.models import FieldCondition, Filter, MatchValue

BEKLENEN = [
    ("mevzuat-2004-madde-67", "İİK m.67 itirazın iptali"),
    ("mevzuat-2004-madde-62", "İİK m.62 ödeme emrine itiraz"),
    ("mevzuat-2004-madde-257", "İİK m.257 ihtiyati haciz"),
    ("mevzuat-4857-madde-17", "4857 m.17 ihbar öneli"),
    ("mevzuat-4857-madde-25", "4857 m.25 haklı fesih"),
    ("mevzuat-6098-madde-350", "TBK m.350 gereksinim tahliyesi"),
    ("mevzuat-4721-madde-506", "TMK m.506 saklı pay"),
    ("mevzuat-1475-madde-14", "1475 m.14 kıdem (KONTROL: bu vardı)"),
]

for doc_id, ad in BEKLENEN:
    pts, _ = main.client.scroll(
        main.collection_name,
        scroll_filter=Filter(must=[FieldCondition(key="docId", match=MatchValue(value=doc_id))]),
        limit=3, with_payload=True, with_vectors=False,
    )
    if not pts:
        print(f"  ❌ YOK      | {ad:<42} | {doc_id}")
    else:
        p = pts[0].payload
        metin = (p.get("metin") or "").replace("\n", " ")
        print(f"  ✅ var ({len(pts)}) | {ad:<42} | {metin[:95]}")

# İİK'da toplam kac madde var, hangi araliklarda?
print("\n--- İİK (2004) korpusta hangi maddeler? ---")
nolar = []
offset = None
while True:
    pts, offset = main.client.scroll(
        main.collection_name,
        scroll_filter=Filter(must=[
            FieldCondition(key="belgeSinifi", match=MatchValue(value="mevzuat")),
        ]),
        limit=512, offset=offset, with_payload=True, with_vectors=False,
    )
    for p in pts:
        d = p.payload.get("docId", "")
        if d.startswith("mevzuat-2004-madde-"):
            try:
                nolar.append(int(d.rsplit("-", 1)[1]))
            except ValueError:
                pass
    if offset is None:
        break
nolar = sorted(set(nolar))
print(f"İİK madde sayisi: {len(nolar)}")
print(f"ilk 30: {nolar[:30]}")
print(f"son 10: {nolar[-10:]}")
for hedef in (62, 67, 257):
    print(f"  m.{hedef} listede mi: {hedef in nolar}")
