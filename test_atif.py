"""CEVAP DOGRULUGU — uretilen metindeki atiflar GERCEK mi?

Erisim olcumleri (eval_erisim/eval_dogrulama) "dogru madde listeye geldi
mi" sorusunu yanitlar. Bu dosya baska bir seyi olcer: /api/chat'in YAZDIGI
cevaptaki atiflar uydurma mi?

Avukat icin en pahali hata budur: olmayan bir kanun maddesine ya da
olmayan bir Yargitay kararina atif. Musteriye acmadan once olculmeli.

Yontem: cevap metninden atif desenlerini cikar, her birini (a) sunulan
kaynaklarda, (b) korpusta ara. Ikisinde de yoksa UYDURMA.
"""
import json
import os
import re
import urllib.request

import main
from qdrant_client.models import FieldCondition, Filter, MatchValue

API = "http://localhost:8000/api/chat"
ANAHTAR = os.environ.get("X_API_KEY", "")

SORULAR = [
    "işçinin kıdem tazminatı hesabında giydirilmiş ücret nasıl bulunur",
    "kiracının tahliyesi için hangi sebeplere dayanılabilir",
    "itirazın iptali davası hangi sürede açılır",
    "yoksulluk nafakası hangi şartlarda bağlanır",
    "ayıplı malda tüketicinin seçimlik hakları nelerdir",
    "istinaf başvuru süresi kaç haftadır",
]

# "4857 sayılı Kanun'un 53. maddesi", "m.14", "madde 344", "İİK 67"
MADDE_DESEN = re.compile(
    r"(?:(\d{3,4})\s*say[ıi]l[ıi][^.]{0,40}?)?"
    r"(?:madde|m\.)\s*(\d+)", re.IGNORECASE)
KARAR_DESEN = re.compile(r"E\.?\s*(\d{4})/(\d+)[^\w]{0,6}K\.?\s*(\d{4})/(\d+)")


def korpusta_madde_var(kanun_no, madde_no):
    doc_id = f"mevzuat-{kanun_no}-madde-{madde_no}"
    pts, _ = main.client.scroll(
        main.collection_name,
        scroll_filter=Filter(must=[FieldCondition(key="docId", match=MatchValue(value=doc_id))]),
        limit=1, with_payload=False, with_vectors=False)
    return bool(pts)


def korpusta_karar_var(esas, karar):
    pts, _ = main.client.scroll(
        main.collection_name,
        scroll_filter=Filter(must=[
            FieldCondition(key="esasNo", match=MatchValue(value=esas)),
            FieldCondition(key="kararNo", match=MatchValue(value=karar)),
        ]),
        limit=1, with_payload=False, with_vectors=False)
    return bool(pts)


toplam_atif = uydurma = 0
for soru in SORULAR:
    istek = urllib.request.Request(
        API, data=json.dumps({"query": soru, "jurisdiction": "TR"}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": ANAHTAR})
    try:
        with urllib.request.urlopen(istek, timeout=180) as r:
            cevap = json.load(r)
    except Exception as e:
        print(f"❌ ISTEK HATASI: {soru[:40]} -> {e}")
        continue

    metin = cevap.get("answer") or cevap.get("cevap") or ""
    kaynaklar = cevap.get("sources") or cevap.get("kaynaklar") or []
    kaynak_metni = " ".join(
        (k.get("source") or k.get("kaynak") or "") if isinstance(k, dict) else str(k)
        for k in kaynaklar)

    print(f"\n{'='*72}\nSORU: {soru[:60]}")
    print(f"  cevap uzunlugu: {len(metin)} | sunulan kaynak: {len(kaynaklar)}")
    if not metin:
        print("  ⚠️  cevap metni BOS (LLM katmani kapali olabilir)")
        continue

    # kanun maddesi atiflari
    gorulen = set()
    for kanun_no, madde_no in MADDE_DESEN.findall(metin):
        if not kanun_no:
            continue  # kanun numarasi olmayan "m.5" tek basina dogrulanamaz
        anahtar = (kanun_no, madde_no)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        toplam_atif += 1
        korpusta = korpusta_madde_var(kanun_no, madde_no)
        kaynakta = f"MADDE {madde_no}" in kaynak_metni and kanun_no in kaynak_metni
        if korpusta:
            print(f"  ✅ {kanun_no} m.{madde_no} — korpusta var"
                  f"{' (sunulan kaynakta da)' if kaynakta else ''}")
        else:
            uydurma += 1
            print(f"  🔴 {kanun_no} m.{madde_no} — KORPUSTA YOK (uydurma riski)")

    # yargi karari atiflari
    for e_y, e_n, k_y, k_n in KARAR_DESEN.findall(metin):
        toplam_atif += 1
        esas, karar = f"{e_y}/{e_n}", f"{k_y}/{k_n}"
        if korpusta_karar_var(esas, karar):
            print(f"  ✅ karar E.{esas} K.{karar} — korpusta var")
        else:
            uydurma += 1
            print(f"  🔴 karar E.{esas} K.{karar} — KORPUSTA YOK (uydurma riski)")

print(f"\n{'='*72}")
print(f"TOPLAM dogrulanabilir atif: {toplam_atif} | korpusta BULUNAMAYAN: {uydurma}")
if toplam_atif:
    print(f"uydurma orani: %{100*uydurma/toplam_atif:.0f}")
