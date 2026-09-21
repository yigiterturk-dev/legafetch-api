"""Kacan maddelerin pasaj metni: aranan ifade iceride mi, gurultu ne kadar?"""
import main
import mevzuat_bm25
from qdrant_client.models import FieldCondition, Filter, MatchValue

HEDEF = [
    ("mevzuat-2004-madde-67", ["itirazin iptali", "bir yil", "icinde"]),
    ("mevzuat-2004-madde-62", ["itiraz", "yedi gun", "7 gun"]),
    ("mevzuat-2004-madde-257", ["ihtiyati haciz"]),
    ("mevzuat-4857-madde-17", ["ihbar", "bildirim suresi", "iki hafta"]),
]

for doc_id, aranan in HEDEF:
    pts, _ = main.client.scroll(
        main.collection_name,
        scroll_filter=Filter(must=[FieldCondition(key="docId", match=MatchValue(value=doc_id))]),
        limit=10, with_payload=True, with_vectors=False,
    )
    print(f"\n{'='*70}\n{doc_id} — {len(pts)} pasaj")
    for p in pts:
        pl = p.payload
        metin = pl.get("metin") or ""
        norm = mevzuat_bm25.normalize(metin)
        bulunan = [a for a in aranan if a in norm]
        print(f"  sira={pl.get('sira')} uzunluk={len(metin)} | eslesen ifade: {bulunan or 'HİÇBİRİ'}")
        print(f"    kaynak: {pl.get('kaynak','')}")
        print(f"    bas: {metin[:150].replace(chr(10),' ')}")

# Sozluk kontrolu: BM25 indeksinde bu terimler hangi dokumanlarda gecıyor?
idx = mevzuat_bm25.indeks_al(main.client, main.collection_name)
print(f"\n{'='*70}\nBM25 sozluk kontrolu")
for terim in ["itirazin", "iptali", "ihtiyati", "haciz", "odeme", "emrine", "ihbar", "onel"]:
    print(f"  '{terim}': df={idx.df.get(terim, 0)}")
