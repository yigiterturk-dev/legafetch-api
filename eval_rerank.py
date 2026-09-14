"""Reranker A/B: ayni adaylar, rerank acik/kapali. mevzuat gorunurlugu + top-1."""
import os, time
import main  # noqa
from rerank import rerank

SORULAR = [
    "4857 sayili kanuna gore iseci iade davasinda arabuluculuk sart mi?",
    "kidem tazminati hangi hallerde odenebilir?",
    "kira artisinda yuzde 25 tavani hangi donemde uygulanir?",
    "hakem kuruluna basvurmadan is davasi acilabilir mi?",
    "tuketici sozlesmesindeki haksiz madde iptal edilebilir mi?",
    "icra takibinde itirazin iptali davasi hangi surede acilir?",
    "calisanin yillik ucretli izin hakki kac gundur?",
    "tazminat davasinda faiz karar tarihinden mi isler?",
    "kentsel donusumde pay sahibinin rizasi olmadan yikim olur mu?",
    "arabuluculuk faaliyeti sonunda anlasma belgeyi kim imzalar?",
]

for q in SORULAR:
    aday = main.corpus_search(q, 40)
    eski = aday[:6]  # iki kolsuz eski davranis (mevzuat sadece tesadufen girerse gorunur)
    yeni = rerank(q, aday, 6)
    def mev(d):
        m = d.metadata.get("source", "")
        return "MEV" if ("Sayil" in m or "Kanunu" in m or "Anayasas" in m) else "ict"
    print(f"SORU: {q[:55]}")
    print(f"  reranksiz : {[m for m in map(lambda d: d.metadata['source'][:40], eski)]}".replace("[", "").replace("]", "").replace("'", ""))
    print(f"  rerankli  : {[m for m in map(lambda d: d.metadata['source'][:40], yeni)]}".replace("[", "").replace("]", "").replace("'", ""))
    print(f"  mevzuat: reranksiz={sum(1 for d in eski if 'mev' == 'x' or 'Sayil' in d.metadata.get('source','') or 'Kanunu' in d.metadata.get('source',''))} rerankli={sum(1 for d in yeni if 'Sayil' in d.metadata.get('source','') or 'Kanunu' in d.metadata.get('source',''))}")
    print(flush=True)
