"""MADDE SEÇİMİ TEŞHİSİ — doğru madde hangi aşamada düşüyor?

2026-09-21 ölçümünde 70 sorunun 15'i kaçtı ve çoğunda doğru KANUN bulunup
yanlış MADDE seçildi. Hattın mevzuat kolu dört aşamalı:

  A. dense çekim      corpus_search_mevzuat(q, CORPUS_MEVZUAT_FETCH_K=24)
  B. kanun-no daraltma mevzuat_havuz_daralt(...)
  C. rerank dilimi     [:CORPUS_MEVZUAT_K=8]   <- pahalı olduğu için kırpılır
  D. rerank + boost    corpus_rank(...) nihai sıra

Beklenen madde hangi aşamada kayboluyorsa düzeltme ORADA yapılır. Aşamayı
bilmeden parametre oynatmak körlemesine tarama olur (bkz. BM25 turu: her
ayarda kapalı olan kazandı).

Kullanım: docker exec -e PYTHONPATH=/app -w /app legafetch-api \
              python loglar/teshis_madde.py
"""
import re

import main

# 2026-09-21 ölçümünde KAÇAN sorular (üç setin tamamı).
KAYIPLAR = [
    # --- kapsam seti ---
    ("anonim şirkette sermaye kaybı ve borca batıklık halinde yönetim kurulunun yükümlülüğü", r"mevzuat-6102-madde-376\b"),
    ("anonim şirket yönetim kurulu üyelerinin hukuki sorumluluğu", r"mevzuat-6102-madde-553\b"),
    ("koşullu salıverilme için infaz edilmesi gereken ceza oranı", r"mevzuat-5275-madde-107\b"),
    ("yabancı hakkında sınır dışı etme kararı hangi hallerde alınır", r"mevzuat-6458-madde-54\b"),
    ("kadına karşı şiddette hâkimin vereceği önleyici tedbir kararları", r"mevzuat-6284-madde-5\b"),
    ("toplu iş sözleşmesi yapma yetkisi ve işkolu barajı", r"mevzuat-6356-madde-41\b"),
    ("türk vatandaşlığının yetkili makam kararıyla kazanılmasında aranan şartlar", r"mevzuat-5901-madde-11\b"),
    # --- erişim seti ---
    ("işçinin kıdem tazminatı hesabında giydirilmiş ücret nasıl bulunur", r"mevzuat-1475-madde-14\b"),
    ("belirsiz süreli iş sözleşmesinde ihbar öneli süreleri nedir", r"mevzuat-4857-madde-17\b"),
    ("itirazın iptali davası hangi sürede açılır", r"mevzuat-2004-madde-67\b"),
    ("ödeme emrine itiraz süresi kaç gündür", r"mevzuat-2004-madde-6[02]\b"),
    ("ihtiyati haciz kararı hangi şartlarda verilir", r"mevzuat-2004-madde-257\b"),
    # --- doğrulama seti ---
    ("borçlunun temerrüdü ve ifa etmemenin sonuçları", r"mevzuat-6098-madde-11[24]\b"),
    ("haksız fiil sorumluluğunun şartları", r"mevzuat-6098-madde-49\b"),
    ("fazla çalışma ücreti nasıl hesaplanır", r"mevzuat-4857-madde-41\b"),
]


def _docid(d) -> str:
    return str((d.metadata or {}).get("docId") or "")


def sira(docs, rx) -> int:
    """Desene uyan ilk belgenin 1'den başlayan sırası; yoksa 0."""
    for i, d in enumerate(docs, 1):
        if rx.search(_docid(d)):
            return i
    return 0


def yaz(n: int, toplam: int) -> str:
    return f"@{n}/{toplam}" if n else f"YOK/{toplam}"


if __name__ == "__main__":
    print(f"MADDE SEÇİMİ TEŞHİSİ — {len(KAYIPLAR)} kayıp soru")
    print(f"FETCH_K={main.CORPUS_MEVZUAT_FETCH_K}  MEVZUAT_K={main.CORPUS_MEVZUAT_K}  "
          f"KW_BOOST={main.MEVZUAT_KW_BOOST}  MIN_ANAHTAR_ORANI={main.MEVZUAT_MIN_ANAHTAR_ORANI}\n")
    print(f"{'soru':<46} | {'A dense':>10} | {'B daralt':>10} | {'C dilim':>9} | {'D nihai':>8}")
    print("-" * 96)
    sayim = {"A": 0, "B": 0, "C": 0, "D": 0, "tamam": 0}
    for soru, desen in KAYIPLAR:
        rx = re.compile(desen)
        ham = main.corpus_search_mevzuat(soru, main.CORPUS_MEVZUAT_FETCH_K)
        a = sira(ham, rx)
        dar = main.mevzuat_havuz_daralt(soru, ham)
        b = sira(dar, rx)
        dilim = dar[:main.CORPUS_MEVZUAT_K]
        c = sira(dilim, rx)
        son = main.corpus_rank(soru, 5)
        d = sira(son, rx)

        if not a:
            asama = "A"          # dense hiç getirmedi
        elif not b:
            asama = "B"          # kanun-no daraltması attı
        elif not c:
            asama = "C"          # ilk 8 dilimine giremedi
        elif not d:
            asama = "D"          # rerank/boost sıralamadan düşürdü
        else:
            asama = "tamam"
        sayim[asama] += 1
        print(f"{soru[:46]:<46} | {yaz(a, len(ham)):>10} | {yaz(b, len(dar)):>10} | "
              f"{yaz(c, len(dilim)):>9} | {yaz(d, 5):>8}  <- {asama}")

    print("\n--- hangi aşama kapattı ---")
    etiket = {
        "A": "A: dense çekim hiç getirmedi (gömme/sorgu sorunu)",
        "B": "B: kanun-no daraltması attı (daraltma kuralı)",
        "C": "C: ilk 8 dilimine giremedi (MEVZUAT_K kırpması)",
        "D": "D: rerank + boost sıralamadan düşürdü (skorlama)",
        "tamam": "hattın nihai 5'inde VAR (ölçüm k farkı)",
    }
    for k in ("A", "B", "C", "D", "tamam"):
        if sayim[k]:
            print(f"  {sayim[k]:>2}  {etiket[k]}")
