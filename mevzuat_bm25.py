"""Mevzuat icin bellek ici BM25 indeksi — dense aramanin sozcuksel karsi kolu.

NEDEN BELLEKTE, NEDEN QDRANT'TA DEGIL:
  Qdrant'ta `lexordo_sparse` (6,24M nokta, modifier=idf) duruyor ama onu
  dolduran script hicbir yerde yok; vektor degerleri ham TF, indeksler
  bilinmeyen bir 32-bit hash (fnv1a/java/crc32 denendi, hicbiri tutmadi
  2026-09-21). Sorgu tarafinda ayni hash'i uretemeden o koleksiyon
  kullanilamaz. Mevzuat ise TOPLAM ~8.4K pasaj (~15 MB) — bellege sigar,
  kendi indeksimizi kurmak hem bagimliliksiz hem milisaniyelik.

UC OLCULMUS TASARIM KARARI (2026-09-21):

1. DIAKRITIK NORMALIZASYONU. e5 gomme diakritige duyarli, korpus
   diakritikli: Turkce sorguda hit@5 %75 iken ASCII yazimda %50'ye
   dusuyordu. Burada sorgu da dokuman da AYNI normalizasyondan gectigi
   icin BM25 kolu diakritiksiz yazimda da calisir.

2. BIGRAM (FRAZ) TOKENLERI. Hukuk dili cok kelimeli kaliplardan olusur.
   Olculdu: "itirazin iptali davasi hangi surede acilir" sorgusu İİK
   m.67'yi GETIRMIYORDU — oysa m.67 metninde ifade birebir geciyor ve
   sozlukte 'itirazin' df=58. Sebep: saf unigram BM25 terimleri tek tek
   toplayip fraz butunlugunu gormuyor, kisa ve alakasiz maddeler (TMK
   m.576) uzunluk normalizasyonu sayesinde one geciyordu. Ardisik token
   ciftleri ayri terim olarak indekslenir.

3. ES ANLAMLI SOZLUGU. Avukat dili ile kanun dili ayrisir: 4857 m.17
   metninde "ihbar" kelimesi HIC gecmez, kanun "bildirim suresi" der.
   Terim boslugunu ne BM25 ne dense kendiliginden koprulerdi. Sozluk
   YALNIZ sorgu tarafinda genisletme yapar (dokuman indeksi kirlenmez).
"""
import math
import os
import re
import threading
import time

# Parametreler 2026-09-21 tarandi (grid_bm25.py, 20 soruluk olcum seti):
# b=0.75 -> 0.3 en buyuk kazanci verdi (MRR 0.463 -> 0.577). Varsayilan
# uzunluk normalizasyonu kanun maddelerinde yanlis: uzun maddeleri
# haksiz cezalandiriyordu. Bigram faydali ama YALNIZ dusuk agirlikta
# (2.0 denendi: MRR 0.325 — tarananlarin en kotusu).
BM25_K1 = float(os.environ.get("MEVZUAT_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("MEVZUAT_BM25_B", "0.3"))
# Fraz eslesmesi tek sozcukten daha guclu bir sinyal: bigram terimlerin
# katkisi agirliklandirilir.
BIGRAM_AGIRLIK = float(os.environ.get("MEVZUAT_BM25_BIGRAM_AGIRLIK", "0.25"))

# Indeks kurulumu ilk kullanimda (lazy) yapilir: /health ve acilis gecikmesin.
_indeks = None
_kilit = threading.Lock()

TR2ASCII = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")

# Turkcede cok gecen, ayirt etmeyen sozcukler. Kanun metinlerinde "madde",
# "kanun", "fikra" her pasajda var — IDF zaten baskilar ama listeden dusurmek
# havuzu kucultur.
DURAK = frozenset("""
ve veya ile ise ki de da bu su o bir icin gibi kadar daha cok az en
olan olarak olup ancak fakat ama yani hem her hic hangi nedir nasil
""".split())

# Avukat dili -> kanun dili. Sol taraf sorguda gecerse sag taraftaki
# terimler sorguya EKLENIR (cikarma yok, ikisi de aranir).
# Her giris olculmus bir bosluga dayanir; tahminle buyutmeyin.
ES_ANLAMLI = {
    # 4857 m.17 metninde "ihbar" hic gecmez; kanun "bildirim suresi" der.
    "ihbar oneli": ["bildirim suresi", "bildirim sureleri"],
    "ihbar tazminati": ["bildirim suresine ait ucret"],
    "ihbar": ["bildirim"],
    "onel": ["sure"],
    # Avukat "kidem tazminati" der; 1475 m.14 kenar basligi yok, metin
    # "kidem tazminati" der ama 4857 m.120 atif yapar.
    "isten cikarma": ["fesih"],
    "isten cikarilma": ["fesih"],
    "tahliye": ["kira sozlesmesini sona erdirme", "sozlesmeyi sona erdirebilir"],
    "ev sahibi": ["kiraya veren"],
    "kiraci": ["kiralayan", "kiraci"],
    # Icra dili
    "odeme emri": ["odeme emri"],
    "borca itiraz": ["itiraz"],
    # Usul dili
    "istinaf": ["istinaf yoluna basvurma"],
    "temyiz suresi": ["temyiz yoluna basvurma"],
    "zamanasimi": ["zamanasimi"],
    "hak dusurucu sure": ["hak dusurucu sure"],
}


def normalize(metin: str) -> str:
    return metin.translate(TR2ASCII).lower()


def _kelimeler(t: str) -> list:
    return [w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 1 and w not in DURAK]


def tokenize(metin: str, sorgu_mu: bool = False) -> list:
    """Diakritik soy, kucult, sozcuklere ayir, duraklari at.

    - Ardisik kelime ciftleri 'a_b' bigram tokeni olarak eklenir (fraz).
    - Madde numaralari ('MADDE 344', 'm.14') 'madde344' tokeni olur.
    - sorgu_mu=True ise es anlamli genisletme uygulanir.
    """
    t = normalize(metin)
    if sorgu_mu:
        for avukat, kanun in ES_ANLAMLI.items():
            if avukat in t:
                t = t + " " + " ".join(kanun)
    kelimeler = _kelimeler(t)
    toks = list(kelimeler)
    # bigramlar: fraz butunlugu sinyali
    for a, b in zip(kelimeler, kelimeler[1:]):
        toks.append(a + "_" + b)
    # "madde 344" / "m 14" -> "madde344" birlesik tokeni (tam eslesme sinyali)
    for m in re.finditer(r"\b(?:madde|m)\s*\.?\s*(\d+)\b", t):
        toks.append("madde" + m.group(1))
    return toks


class BM25Indeks:
    def __init__(self, dokumanlar):
        """dokumanlar: [(anahtar, metin, payload)] listesi."""
        self.dokumanlar = dokumanlar
        self.df = {}
        self.tf = []
        self.uzunluk = []
        for _, metin, _ in dokumanlar:
            toks = tokenize(metin)
            sayac = {}
            for w in toks:
                sayac[w] = sayac.get(w, 0) + 1
            self.tf.append(sayac)
            # Uzunluk normalizasyonunda yalniz unigramlar sayilir: bigramlar
            # token sayisini iki katina cikarip kisa maddeleri haksiz
            # avantajli hale getirmesin.
            self.uzunluk.append(sum(1 for w in toks if "_" not in w) or 1)
            for w in sayac:
                self.df[w] = self.df.get(w, 0) + 1
        self.n = len(dokumanlar) or 1
        self.ort_uzunluk = sum(self.uzunluk) / self.n

    def ara(self, sorgu: str, k: int):
        q = tokenize(sorgu, sorgu_mu=True)
        if not q:
            return []
        skorlar = {}
        for w in set(q):
            df = self.df.get(w)
            if not df:
                continue
            idf = math.log(1 + (self.n - df + 0.5) / (df + 0.5))
            agirlik = BIGRAM_AGIRLIK if "_" in w else 1.0
            for i, sayac in enumerate(self.tf):
                f = sayac.get(w)
                if not f:
                    continue
                payda = f + BM25_K1 * (
                    1 - BM25_B + BM25_B * self.uzunluk[i] / self.ort_uzunluk
                )
                skorlar[i] = skorlar.get(i, 0.0) + agirlik * idf * (f * (BM25_K1 + 1)) / payda
        ilk = sorted(skorlar.items(), key=lambda x: x[1], reverse=True)[:k]
        return [(self.dokumanlar[i][2], s) for i, s in ilk]


def _mevzuati_cek(client, collection_name):
    """Tum mevzuat pasajlarini scroll ile ceker (vektorsuz, ~8.4K kayit)."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    cikti = []
    offset = None
    while True:
        noktalar, offset = client.scroll(
            collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="belgeSinifi", match=MatchValue(value="mevzuat")),
                    FieldCondition(key="sentetik", match=MatchValue(value=False)),
                ]
            ),
            limit=512,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for p in noktalar:
            pl = p.payload or {}
            metin = pl.get("metin") or ""
            baslik = pl.get("kaynak") or pl.get("baslik") or ""
            if not metin:
                continue
            # Baslik metne katilir: "6100 Sayili HMK — MADDE 345" sorgudaki
            # kanun adi/numarasiyla eslessin.
            cikti.append((pl.get("docId", ""), baslik + "\n" + metin, pl))
        if offset is None:
            break
    return cikti


def indeks_al(client, collection_name):
    """Lazy kurulum; surec omrunce bellekte kalir."""
    global _indeks
    if _indeks is not None:
        return _indeks
    with _kilit:
        if _indeks is not None:
            return _indeks
        t0 = time.time()
        dok = _mevzuati_cek(client, collection_name)
        _indeks = BM25Indeks(dok)
        print(
            f"[mevzuat-bm25] {len(dok)} pasaj indekslendi "
            f"({time.time() - t0:.1f} sn, {len(_indeks.df)} terim)",
            flush=True,
        )
    return _indeks


BM25_ENABLED = os.environ.get("MEVZUAT_BM25_ENABLED", "1").strip() == "1"


def skor_sozlugu(client, collection_name, sorgu: str, k: int = 60) -> dict:
    """docId -> BM25 skoru. Secim asamasinda DENSE kolundan gelen adaylar da
    sozcuksel skor alsin diye: yalniz BM25 kolundan gelenlere boost vermek
    adaletsiz olur ve ayni maddeyi iki kolun bulmasini odullendirmez."""
    idx = indeks_al(client, collection_name)
    return {
        pl.get("docId", ""): skor
        for pl, skor in idx.ara(sorgu, k)
    }
