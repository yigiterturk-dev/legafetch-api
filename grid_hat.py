"""Tam hat kombinasyon taramasi: BM25'i havuza eklemek mi, skora katmak mi?

A ekseni: CORPUS_MEVZUAT_BM25_K  — BM25 adaylari havuza girsin mi (kac tane)
B ekseni: MEVZUAT_BM25_BOOST     — BM25 skoru secim formuline katilsin mi

Ikisi farkli seyler: havuza eklemek rerank'in onune yeni aday koyar (yanlis
secme riski), skora katmak ise mevcut adaylar arasinda siralamayi degistirir.
"""
import re

import main
from eval_erisim import SORULAR


def olc_kombinasyon(bm25_k, boost):
    main.CORPUS_MEVZUAT_BM25_K = bm25_k
    main.MEVZUAT_BM25_BOOST = boost
    hit5 = hit1 = 0
    mrr = 0.0
    kacan = []
    for soru, desen in SORULAR:
        rx = re.compile(desen)
        docs = main.corpus_rank(soru, 5)[:5]
        sira = 0
        for i, d in enumerate(docs, 1):
            if rx.search((d.metadata or {}).get("docId", "")):
                sira = i
                break
        if sira:
            mrr += 1.0 / sira
            if sira <= 5:
                hit5 += 1
            if sira == 1:
                hit1 += 1
        else:
            kacan.append(soru[:38])
    n = len(SORULAR)
    return hit1, hit5, mrr / n, kacan


print(f"{'bm25_k':>7} {'boost':>6} | {'hit@1':>5} {'hit@5':>5} {'MRR':>6}")
print("-" * 40)
tum = []
for bm25_k, boost in [(0, 0.0), (0, 0.3), (0, 0.5), (0, 1.0),
                      (8, 0.0), (8, 0.3), (8, 0.5), (8, 1.0),
                      (4, 0.3), (16, 0.3)]:
    h1, h5, mrr, kacan = olc_kombinasyon(bm25_k, boost)
    tum.append((mrr, h5, h1, bm25_k, boost, kacan))
    print(f"{bm25_k:>7} {boost:>6} | {h1:5d} {h5:5d} {mrr:6.3f}", flush=True)

tum.sort(reverse=True)
mrr, h5, h1, bk, bo, kacan = tum[0]
print(f"\nEN IYI: bm25_k={bk} boost={bo} -> hit@1={h1} hit@5={h5} MRR={mrr:.3f}")
print("kacanlar:")
for s in kacan:
    print(f"  - {s}")
