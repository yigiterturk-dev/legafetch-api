"""DOGRULAMA SETI — parametre taramasinda KULLANILMAYAN 20 soru.

Neden ayri set: bigram agirligi / k1 / b degerleri eval_erisim.py'nin 20
sorusu uzerinde tarandi (grid_bm25.py). Ayni sette olculen iyilesme asiri
uyum olabilir. Bu set tarama sirasinda hic gorulmedi.

Onemli disiplin: her beklenen madde ONCE korpusta var mi diye bakilir.
Olmayan maddeyi sormak erisimi degil ITHALATI olcer ve yanlis teshise
goturur.
"""
import re
import sys
import time

import main
from eval_erisim import K, TR2ASCII, olc
from qdrant_client.models import FieldCondition, Filter, MatchValue

SORULAR = [
    ("kasten yaralama suçunun cezası nedir", r"mevzuat-5237-madde-86\b"),
    ("hakaret suçu ve cezası", r"mevzuat-5237-madde-125\b"),
    ("nitelikli dolandırıcılık halleri", r"mevzuat-5237-madde-158\b"),
    ("tutuklama nedenleri nelerdir", r"mevzuat-5271-madde-100\b"),
    ("hükmün açıklanmasının geri bırakılması şartları",
     r"mevzuat-5271-madde-231\b"),
    ("yoksulluk nafakası hangi şartlarda bağlanır", r"mevzuat-4721-madde-175\b"),
    ("mirasçılık belgesi nasıl alınır", r"mevzuat-4721-madde-598\b"),
    ("borçlunun temerrüdü ve ifa etmemenin sonuçları",
     r"mevzuat-6098-madde-11[24]\b"),
    ("alacaklarda genel zamanaşımı süresi on yıl",
     r"mevzuat-6098-madde-146\b"),
    ("haksız fiil sorumluluğunun şartları", r"mevzuat-6098-madde-49\b"),
    ("fazla çalışma ücreti nasıl hesaplanır", r"mevzuat-4857-madde-41\b"),
    ("feshin geçerli bir sebebe dayandırılması zorunluluğu",
     r"mevzuat-4857-madde-18\b"),
    ("dava dilekçesinde bulunması gereken hususlar",
     r"mevzuat-6100-madde-119\b"),
    ("bilirkişiye hangi hallerde başvurulur", r"mevzuat-6100-madde-266\b"),
    ("üçüncü kişilerdeki alacakların haczi haciz ihbarnamesi",
     r"mevzuat-2004-madde-89\b"),
    ("haczedilemeyen mallar ve haklar nelerdir", r"mevzuat-2004-madde-82\b"),
    ("ruhsatsız yapı hakkında yapılacak işlem", r"mevzuat-3194-madde-32\b"),
    ("ilgili kişinin veri sorumlusuna başvuru hakları",
     r"mevzuat-6698-madde-11\b"),
    ("idari davalarda dava açma süresi altmış gün",
     r"mevzuat-2577-madde-7\b"),
    ("devlet memurlarına verilecek disiplin cezaları",
     r"mevzuat-657-madde-125\b"),
]


def korpusta_var_mi(desen: str) -> bool:
    """Desenin karsiligi bir docId korpusta var mi? Desen 'mevzuat-X-madde-Y'
    kalibinda; alternatifli desenler (11[24]) icin her ihtimal denenir."""
    ham = desen.replace(r"\b", "")
    adaylar = [ham]
    m = re.search(r"\[(\d+)\]", ham)
    if m:
        adaylar = [ham.replace(m.group(0), rakam) for rakam in m.group(1)]
    for aday in adaylar:
        pts, _ = main.client.scroll(
            main.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="docId", match=MatchValue(value=aday))]
            ),
            limit=1, with_payload=False, with_vectors=False,
        )
        if pts:
            return True
    return False


if __name__ == "__main__":
    ascii_mod = len(sys.argv) > 1 and sys.argv[1] == "ascii"

    print("== Beklenen maddeler korpusta mi? ==")
    gecerli = []
    for soru, desen in SORULAR:
        if korpusta_var_mi(desen):
            gecerli.append((soru, desen))
        else:
            print(f"  ATLANDI (madde korpusta yok): {desen} — {soru[:45]}")
    print(f"gecerli soru: {len(gecerli)}/{len(SORULAR)}\n")

    sorular = gecerli
    baslik = "TÜRKÇE"
    if ascii_mod:
        sorular = [(q.translate(TR2ASCII), d) for q, d in gecerli]
        baslik = "ASCII"

    print(f"DOGRULAMA SETI — {len(sorular)} soru, k={K}, dil: {baslik}")
    olc(sorular, main.corpus_rank, f"{baslik} / corpus_rank (URETIM)")
