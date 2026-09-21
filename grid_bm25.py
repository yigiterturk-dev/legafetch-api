"""BM25 parametre taramasi — indeks BIR KEZ kurulur, skorlama parametrik.

Taranan: bigram agirligi, k1, b, es anlamli genisletme.
Olcut: MRR@10 ve hit@5 (beklenen kanun maddesi).
UYARI: 20 soruluk sete asiri uyum riski var; secilen parametre ikinci bir
soru setiyle DOGRULANMALI.
"""
import math
import re

import main
import mevzuat_bm25 as mb
from eval_erisim import SORULAR

idx = mb.indeks_al(main.client, main.collection_name)
print(f"indeks: {len(idx.dokumanlar)} pasaj, {len(idx.df)} terim\n")


def ara_param(sorgu, k, bigram_agirlik, k1, b, es_anlamli):
    q = mb.tokenize(sorgu, sorgu_mu=es_anlamli)
    if not es_anlamli:
        q = mb.tokenize(sorgu, sorgu_mu=False)
    skorlar = {}
    for w in set(q):
        df = idx.df.get(w)
        if not df:
            continue
        if "_" in w and bigram_agirlik == 0:
            continue
        idf = math.log(1 + (idx.n - df + 0.5) / (df + 0.5))
        agirlik = bigram_agirlik if "_" in w else 1.0
        for i, sayac in enumerate(idx.tf):
            f = sayac.get(w)
            if not f:
                continue
            payda = f + k1 * (1 - b + b * idx.uzunluk[i] / idx.ort_uzunluk)
            skorlar[i] = skorlar.get(i, 0.0) + agirlik * idf * (f * (k1 + 1)) / payda
    ilk = sorted(skorlar.items(), key=lambda x: x[1], reverse=True)[:k]
    return [(idx.dokumanlar[i][2], s) for i, s in ilk]


def degerlendir(bigram_agirlik, k1, b, es_anlamli):
    hit1 = hit5 = 0
    mrr = 0.0
    for soru, desen in SORULAR:
        rx = re.compile(desen)
        sonuc = ara_param(soru, 10, bigram_agirlik, k1, b, es_anlamli)
        for i, (pl, _) in enumerate(sonuc, 1):
            if rx.search(pl.get("docId", "")):
                mrr += 1.0 / i
                if i <= 5:
                    hit5 += 1
                if i == 1:
                    hit1 += 1
                break
    n = len(SORULAR)
    return hit1, hit5, mrr / n


sonuclar = []
for bg in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
    for k1 in (1.2, 1.5):
        for b in (0.3, 0.5, 0.75):
            for es in (True, False):
                h1, h5, mrr = degerlendir(bg, k1, b, es)
                sonuclar.append((mrr, h5, h1, bg, k1, b, es))

sonuclar.sort(reverse=True)
print(f"{'MRR':>6} {'hit@5':>6} {'hit@1':>6} | bigram   k1    b     esanlamli")
print("-" * 58)
for mrr, h5, h1, bg, k1, b, es in sonuclar[:15]:
    print(f"{mrr:6.3f} {h5:6d} {h1:6d} | {bg:<8} {k1:<5} {b:<5} {es}")
print("\n--- en kotu 3 (karsilastirma icin) ---")
for mrr, h5, h1, bg, k1, b, es in sonuclar[-3:]:
    print(f"{mrr:6.3f} {h5:6d} {h1:6d} | {bg:<8} {k1:<5} {b:<5} {es}")
