"""MEVZUAT_BASA_ESIK taramasi — IKI olcum setinde birden.

Esik 0    = her mevzuat maddesi basa (alakasizlar da vitrinde)
Esik cok yuksek = hicbiri basa (eski davranis, MRR 0.185)
Arada bir yerde en iyi denge var; iki sette birden bakilir ki tek sete
asiri uyum olmasin.
"""
import re

import main
from eval_erisim import SORULAR as SET1
from eval_dogrulama import SORULAR as SET2


def olc(sorular, esik):
    main.MEVZUAT_BASA_ESIK = esik
    hit1 = hit5 = 0
    mrr = 0.0
    for soru, desen in sorular:
        rx = re.compile(desen)
        docs = main.corpus_rank(soru, 5)[:5]
        for i, d in enumerate(docs, 1):
            if rx.search((d.metadata or {}).get("docId", "")):
                mrr += 1.0 / i
                if i <= 5:
                    hit5 += 1
                if i == 1:
                    hit1 += 1
                break
    n = len(sorular)
    return hit1, hit5, mrr / n


print(f"{'esik':>5} | {'SET1 h@1':>8} {'h@5':>4} {'MRR':>6} | {'SET2 h@1':>8} {'h@5':>4} {'MRR':>6} | {'ort MRR':>7}")
print("-" * 72)
for esik in (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 99.0):
    a1, a5, amrr = olc(SET1, esik)
    b1, b5, bmrr = olc(SET2, esik)
    etiket = "KAPALI" if esik > 90 else f"{esik}"
    print(f"{etiket:>5} | {a1:8d} {a5:4d} {amrr:6.3f} | {b1:8d} {b5:4d} {bmrr:6.3f} | {(amrr+bmrr)/2:7.3f}",
          flush=True)
