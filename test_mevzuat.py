import main

SORULAR = [
    "tuketici sozlesmesindeki haksiz madde iptali davasi",
    "iscinin haber vermeden isten ayrilmasi kidem tazminati alabilir mi",
    "arabuluculuga basvurmadan is davasina bakilabilir mi",
    "yillik ucretli izin hakki kac gundur",
    "haciz yolundan maruz kalan borclunun itiraz sureleri",
    "kentsel donusumde pay sahibinin rizasi olmadan yikim olur mu",
]
import time
for q in SORULAR:
    t0 = time.time()
    docs = main.corpus_rank(q, 6)
    mev = [d.metadata["source"] for d in docs if d.metadata.get("tur") == "mevzuat"]
    print("SORU:", q[:52])
    for i, d in enumerate(docs[:6]):
        print("   [%d] %s" % (i + 1, d.metadata["source"][:60]))
    print("   MEVZUAT:", len(mev), "→", "; ".join(m[:45] for m in mev))
    print("   sure: %.1fs" % (time.time() - t0), flush=True)
