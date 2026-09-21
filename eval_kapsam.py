"""KAPSAM SETİ — 30 soru, mevzuat 73 kanuna çıktıktan sonra eklenen kanunlar.

Neden üçüncü set: eval_erisim.py (20 soru) ve eval_dogrulama.py (20 soru)
külliyat 19 kanunken yazıldı ve ikisi birlikte bugünkü 73 kanunun yalnız
14'üne dokunuyor (4857, 6098, 634, 2004, 6100, 4721, 6502, 6698, 3194,
5237, 5271, 2577, 657, 1475). Geri kalan 59 kanunun erişimi HİÇ ölçülmedi.
Bu set onlardan 30 tanesini hedefler; kanun başına en çok bir soru.

Hukuki doğrulama (2026-09-21, tek tek yapıldı):
  1. Beklenen docId külliyatta var mı? -> 35 adayın 35'i VAR.
  2. Pasajın METNİ sorunun cevabını veriyor mu? -> gözle okundu; metni
     soruyla örtüşmeyen 5 aday (5510-80, 193-94, 3065-29, 5684-30,
     5651-9) sete ALINMADI.
Olmayan/örtüşmeyen maddeyi sormak erişimi değil ithalatı ölçer.

Sorgular Türkçe diakritikle yazılır — korpus diakritikli, e5 gömmesi
duyarlı (bkz. eval_erisim.py başlığı).

Kullanım:
  docker exec -e PYTHONPATH=/app -w /app legafetch-api \
      python loglar/eval_kapsam.py [ascii]
"""
import sys

import main  # noqa: F401  (üretim hattı)
from eval_dogrulama import korpusta_var_mi
from eval_erisim import K, TR2ASCII, olc

# (soru, beklenen docId deseni) — docId: mevzuat-<kanun>-madde-<no>
SORULAR = [
    ("anonim şirkette sermaye kaybı ve borca batıklık halinde yönetim kurulunun yükümlülüğü",
     r"mevzuat-6102-madde-376\b"),
    ("anonim şirket yönetim kurulu üyelerinin hukuki sorumluluğu",
     r"mevzuat-6102-madde-553\b"),
    ("limited şirkette ortağın şirketten çıkması ve çıkarılması",
     r"mevzuat-6102-madde-638\b"),
    ("kimler sigortalı sayılır, hizmet akdiyle çalışanlar",
     r"mevzuat-5510-madde-4\b"),
    ("yaşlılık aylığına hak kazanma şartları ve prim gün sayısı",
     r"mevzuat-5510-madde-28\b"),
    ("vergi kaçakçılığı suçları ve cezaları, sahte belge düzenleme",
     r"mevzuat-213-madde-359\b"),
    ("vergi alacağında tarh zamanaşımı süresi beş yıl",
     r"mevzuat-213-madde-114\b"),
    ("trafik kazasında araç işletenin hukuki sorumluluğu",
     r"mevzuat-2918-madde-85\b"),
    ("avukatlık ücret sözleşmesi ve ücretin belirlenmesi",
     r"mevzuat-1136-madde-164\b"),
    ("marka tescilinde nispi ret nedenleri, önceki markayla karıştırılma ihtimali",
     r"mevzuat-6769-madde-6\b"),
    ("marka hakkına tecavüz sayılan fiiller nelerdir",
     r"mevzuat-6769-madde-29\b"),
    ("hak arama hürriyeti ve adil yargılanma hakkı anayasal güvencesi",
     r"mevzuat-2709-madde-36\b"),
    ("koşullu salıverilme için infaz edilmesi gereken ceza oranı",
     r"mevzuat-5275-madde-107\b"),
    ("açık ihale usulü nedir, bütün isteklilerin teklif vermesi",
     r"mevzuat-4734-madde-19\b"),
    ("eser sahibinin yazılı izni olmadan kullanımda üç kat tazminat",
     r"mevzuat-5846-madde-68\b"),
    ("amme alacağının cebren tahsil şekilleri nelerdir",
     r"mevzuat-6183-madde-54\b"),
    ("yabancı hakkında sınır dışı etme kararı hangi hallerde alınır",
     r"mevzuat-6458-madde-54\b"),
    ("işsizlik ödeneğine hak kazanmanın şartları",
     r"mevzuat-4447-madde-51\b"),
    ("tebliğ imkansızlığı ve tebellüğden imtina halinde tebligat nasıl yapılır",
     r"mevzuat-7201-madde-21\b"),
    ("kadına karşı şiddette hâkimin vereceği önleyici tedbir kararları",
     r"mevzuat-6284-madde-5\b"),
    ("riskli yapının tahliyesi ve yıktırılması süreci",
     r"mevzuat-6306-madde-5\b"),
    ("kamulaştırma bedelinin mahkemece tespiti ve tescil davası",
     r"mevzuat-2942-madde-10\b"),
    ("kabahatlerde idari para cezasının belirlenmesi",
     r"mevzuat-5326-madde-17\b"),
    ("toplu iş sözleşmesi yapma yetkisi ve işkolu barajı",
     r"mevzuat-6356-madde-41\b"),
    ("işçinin ciddi ve yakın tehlike halinde çalışmaktan kaçınma hakkı",
     r"mevzuat-6331-madde-13\b"),
    ("türk vatandaşlığının yetkili makam kararıyla kazanılmasında aranan şartlar",
     r"mevzuat-5901-madde-11\b"),
    ("hâkim durumun kötüye kullanılması yasağı",
     r"mevzuat-4054-madde-6\b"),
    ("transfer fiyatlandırması yoluyla örtülü kazanç dağıtımı",
     r"mevzuat-5520-madde-13\b"),
    ("arabuluculukta tarafların anlaşması ve icra edilebilirlik şerhi",
     r"mevzuat-6325-madde-18\b"),
    ("önemli nitelikteki işlemlerde pay sahibinin ayrılma hakkı",
     r"mevzuat-6362-madde-24\b"),
]

if __name__ == "__main__":
    ascii_mod = len(sys.argv) > 1 and sys.argv[1] == "ascii"

    print("== Beklenen maddeler korpusta mı? ==")
    gecerli = []
    for soru, desen in SORULAR:
        if korpusta_var_mi(desen):
            gecerli.append((soru, desen))
        else:
            print(f"  ATLANDI (madde korpusta yok): {desen} — {soru[:45]}")
    print(f"geçerli soru: {len(gecerli)}/{len(SORULAR)}\n")

    sorular = gecerli
    baslik = "TÜRKÇE"
    if ascii_mod:
        sorular = [(q.translate(TR2ASCII), d) for q, d in gecerli]
        baslik = "ASCII"

    print(f"KAPSAM SETİ — {len(sorular)} soru, k={K}, dil: {baslik}")
    olc(sorular, main.corpus_rank, f"{baslik} / corpus_rank (ÜRETİM)")
