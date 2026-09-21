"""BM25 kolu tek basina ne kadar iyi? Beklenen madde kacinci sirada?"""
import main
import mevzuat_bm25
from eval_erisim import SORULAR
import re

idx = mevzuat_bm25.indeks_al(main.client, main.collection_name)
print(f"indeks: {len(idx.dokumanlar)} pasaj\n")

hit5 = hit1 = 0
mrr = 0.0
for soru, desen in SORULAR:
    rx = re.compile(desen)
    sonuc = idx.ara(soru, 10)
    sira = 0
    for i, (pl, skor) in enumerate(sonuc, 1):
        if rx.search(pl.get("docId", "")):
            sira = i
            break
    ilk = sonuc[0][0].get("kaynak", "")[:55] if sonuc else "(bos)"
    ilk_skor = sonuc[0][1] if sonuc else 0
    if sira:
        mrr += 1.0 / sira
        if sira <= 5:
            hit5 += 1
        if sira == 1:
            hit1 += 1
        print(f"  @{sira:<2} | {soru[:46]:<46} | 1.: {ilk} ({ilk_skor:.1f})")
    else:
        print(f"  --  | {soru[:46]:<46} | 1.: {ilk} ({ilk_skor:.1f})")
n = len(SORULAR)
print(f"\nBM25 TEK BASINA: hit@1={hit1}/{n} hit@5={hit5}/{n} MRR@10={mrr/n:.3f}")
