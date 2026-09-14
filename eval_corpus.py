"""
LegaFetch korpus kalite testi (REMOTE_MODE korpusu uzerinde).
Kullanim:
  QDRANT_URL=... QDRANT_API_KEY=... ./venv/bin/python eval_corpus.py [orneklem]
Kontrol:
  A) oz-kaynakli geri-getirme (self-retrieval) hit@5 + gecikme
  B) gercek dunya sorgularinda sonuc donmesi + turcesli gozlem
"""
import os, re, sys, time, random
import main  # noqa: E402  (uygulama baslatilir, corpus_search gercek urun yolunu test eder)
from qdrant_client.models import Filter, FieldCondition, MatchValue  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402

random.seed(7)
K = 5

# Karar başlığı / bölüm işareti parçaları ("III. İLK DERECE MAHKEMESİ KARARI",
# "II. CEVAP ...") 25 bin kararın hepsinde yapısal olarak aynıdır; saf vektör
# benzerliği bunları kaynağından ayırt edemez. Ölçüm dışı bırakılır.
YAPISAL = re.compile(r"^(TEMYİZ|CEVAP|İLK DERECE|İNCELEME|UYUŞMAZLIK|HUKUKİ DEĞERLENDİRME|İLGİLİ MEVZUAT|KARAR|DAVA VE HUKUKİ|\*\*\d+\. Hukuk|Sayın çoğunluk|Taraflar arasındaki davanın|Kararın taraf vekillerince)", re.I)

print("== A) Oz-kaynakli geri-getirme testi ==")
# 1) 60 nokta tara, 40 tanesini test sec
src_client = QdrantClient(url=os.environ["QDRANT_URL"],
                          api_key=os.environ.get("QDRANT_API_KEY") or None, timeout=120)
pts = src_client.scroll(main.collection_name, limit=24,
                        scroll_filter=Filter(
                            must=[FieldCondition(key="sentetik", match=MatchValue(value=False))]),
                        with_payload=True, with_vectors=False)[0]
ornekler = random.sample(pts, min(20, len(pts)))
hits, miss, lat = [], [], []
for p in ornekler:
    # TAM parça metni sorgulanır. Kesik (180 karakterlik) parça sorgusu e5
    # uzayında parçanın kendisinden kopar ve yapay düşüş üretir: tam parça
    # hit@5 %100 iken önek sorgusu %30'a düşer. Gerçek ürün sorgusu da
    # bütün sorudur; kesik önek gerçekçi bir senaryo değildir.
    metin = (p.payload.get("metin") or "").replace("\n", " ").strip()
    doc_id = p.payload.get("docId", "")
    if len(metin) < 120 or YAPISAL.match(metin[:200]):
        continue
    t0 = time.time()
    docs = main.corpus_search(metin, K)
    lat.append(time.time() - t0)
    print(f"  [{len(hits)+len(miss)+1}/20] {time.time()-t0:.2f}s", flush=True)
    donen = [d.metadata.get("docId") for d in docs]
    (hits if (doc_id and doc_id in donen) else miss).append(p.payload.get("kaynak", "")[:60])
toplam_n = len(hits) + len(miss)
oran = 100 * len(hits) / max(1, toplam_n)
print(f"orneklem: {toplam_n} | hit@{K}: {len(hits)} (%{oran:.0f}) | ort. gecikme: {sum(lat)/max(1,len(lat)):.2f}s")
for m in miss[:5]:
    print("  MISS:", m)

print()
print("== B) Gercek dunya sorgulari ==")
sorgular = [
    "iscinin haber vermeden isten ayrilmasi kidem tazminati alabilir mi",
    "kira artisi yuzde 25 tavani hangi donemde uygulanir",
    "tuketici sozlesmesindeki haksiz madde iptali davasi",
    "icra takibine itiraz eden borclu icin 7 gun sure",
    "iscinin iadesi ve bos gecen sure tazminati hesabi",
    "arabuluculuga basvurmadan is davasina bakilabilir mi",
    "kati tasarruf davasinda zamanaasimi suresi",
    "tazminat davasinda faiz baslangici karar tarihi mi",
    "haciz yolundan maruz kalan borclunun itiraz sureleri",
    "kentsel donusumde pay sahibinin haklari",
]
for s in sorgular:
    t0 = time.time()
    docs = main.corpus_search(s, 3)
    sure = time.time() - t0
    ilk = docs[0].metadata if docs else {}

    print(f"  [{sure*1000:5.0f}ms] {s[:48]:48s} -> {ilk.get('source','YOK')[:60]}")
