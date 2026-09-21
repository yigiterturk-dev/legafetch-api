"""GURULTU / ABSTAIN testi — erisim setlerinin OLCMEDIGI sey.

eval_erisim ve eval_dogrulama "dogru madde kacinci sirada" olcer. Ama
sistem her sorguya GARANTI 2 mevzuat maddesi basiyor; hukuki karsiligi
olmayan bir soruda da basiyor mu, basiyorsa ne kadar guvenle?

Avukat icin en pahali hata: alakasiz kanun maddesinin 1. sirada, yuksek
guvenle sunulmasi.
"""
import main

ALAKASIZ = [
    "pizza hamuru nasil yapilir",
    "yarin hava nasil olacak",
    "python listesinde eleman nasil silinir",
    "en iyi tatil yerleri hangileri",
    "arabamin lastigi patladi ne yapmaliyim",
]
HUKUKI_AMA_KORPUS_DISI = [
    "uzay hukukunda gok cisimlerinin mulkiyeti kime aittir",
    "denizcilikte gemi adaminin disiplin cezalari nelerdir",
]

def bak(baslik, sorular):
    print(f"\n=== {baslik} ===")
    for q in sorular:
        docs = main.corpus_rank(q, 5)[:5]
        mev = [d for d in docs if (d.metadata or {}).get("tur") == "mevzuat"]
        ilk = docs[0].metadata.get("source", "")[:58] if docs else "(bos)"
        ilk_mevzuat_mi = bool(docs) and (docs[0].metadata or {}).get("tur") == "mevzuat"
        isaret = "🔴" if ilk_mevzuat_mi else "  "
        print(f"  {isaret} '{q[:40]}'")
        print(f"       1.: {ilk}")
        print(f"       donen mevzuat sayisi: {len(mev)}")

bak("HUKUKI OLMAYAN SORULAR (ideal: mevzuat basmamali)", ALAKASIZ)
bak("HUKUKI AMA KORPUSTA OLMAYAN ALAN", HUKUKI_AMA_KORPUS_DISI)
print("\n🔴 = alakasiz soruya 1. sirada kanun maddesi basildi")
