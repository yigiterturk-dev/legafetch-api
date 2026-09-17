"""Reranker A/B: uretim hatti (corpus_rank) ile reranksiz tek-kol baseline.

2026-09-17 ders: eski surum yalnizca main.corpus_search cagirip mevzuat
kolunu hic olcmuyordu; sayac da ASCII ('Sayil', 'Kanunu') sniffliyordu,
Turkce kaynaklar ('Sayılı', 'Kanun —') hic yakalanmiyordu. Artik uretimle
ayni yol (main.corpus_rank) olculur, mevzuat sayaci metadata 'tur'
alanindan gelir.
"""
import time
import main  # noqa

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
    t0 = time.time()
    eski = main.corpus_search(q, main.CORPUS_K)[:6]  # rerank+mevzuat kolu yok (eski davranis)
    yeni = main.corpus_rank(q, 6)                    # uretim: iki kol + daralt + rerank + garanti
    sure = time.time() - t0
    def mev(d):
        return 1 if d.metadata.get("tur") == "mevzuat" else 0
    print(f"SORU: {q[:55]}  [{sure:.1f}s]")
    print(f"  reranksiz : {[d.metadata['source'][:40] for d in eski]}")
    print(f"  uretim    : {[d.metadata['source'][:40] for d in yeni]}")
    print(f"  mevzuat: eski={sum(map(mev, eski))} uretim={sum(map(mev, yeni))} (garanti: >=2)")
    print(flush=True)
