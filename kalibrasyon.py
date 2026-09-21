import main
from rerank import rerank_scored

kotu = main.corpus_search_mevzuat("tuketici sozlesmesindeki haksiz madde iptali davasi", 6)
iyi = main.corpus_search_mevzuat("arabuluculuga basvurmadan is davasi", 6)
izin = main.corpus_search_mevzuat("yillik ucretli izin hakki kac gundur", 6)

for etiket, aday, soru in [
    ("KOTU", kotu, "tuketici sozlesmesindeki haksiz madde iptali"),
    ("IYI", iyi, "arabuluculuga basvurmadan is davasina bakilabilir mi"),
    ("IZIN", izin, "yillik ucretli izin hakki kac gundur"),
]:
    skorlu = rerank_scored(soru, aday)
    print(etiket, "|", soru[:45])
    for d, s in skorlu[:6]:
        print("   skor=%+.2f  %s" % (s, d.metadata["source"][:52]))
    print()
