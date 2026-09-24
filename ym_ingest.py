"""YÖNETMELİK İNGEST (Batch 1) — 282 aday PDF → madde chunk → e5 → qdrant.

Kaynak: /opt/etl/yonetmelik-adaylari.txt (mevzuat.gov.tr adayları)
Şema:   docId=mevzuat-<no>-madde-<n> | kaynak="<AD> — MADDE <n>"
        belgeSinifi=mevzuat, tur=yonetmelik, sentetik=false
Idempotent: qdrant id = uuid5("legafetch-" + docId) → tekrar koşum güvenli.
Kullanım (api konteynerinde, PDF'ler /tmp/yonetmelik-pdf/):
  docker exec -e PYTHONPATH=/app -w /app legafetch-api python ym_ingest.py
"""
import os
import re
import sys
import time
import uuid

import main
from qdrant_client.models import PointStruct

PDF_DIZIN = os.environ.get("YM_PDF", "/tmp/yonetmelik-pdf")
BATCH = 64
MIN_UZUNLUK = 60


def adaylari_oku(path):
    """no -> (baslik, rg_tarih)"""
    cikti = {}
    for satir in open(path, encoding="utf-8"):
        m = re.search(r"no=(\d+)\s+tertip=(\d+)\s+turKodu=(\d+)\s+rg=([\d.]+)\s+url=\S+\s+(.*)", satir)
        if m:
            cikti[m.group(1)] = (re.sub(r"<[^>]+>", "", m.group(5)).strip(), m.group(4))
    return cikti


def metni_cikar(yol):
    from pypdf import PdfReader
    try:
        r = __import__("pypdf", fromlist=["PdfReader"]).PdfReader(yol)
        return " ".join((p.extract_text() or "") for p in r.pages)
    except Exception as e:
        print(f"  [pdf-hata] {os.path.basename(yol)}: {e}", flush=True)
        return ""


def maddelere_bol(metin, no, baslik):
    """MADDE n- bloklarına ayır; öncesi 'giris' chunk'ı olur."""
    norm = re.sub(r"\s+", " ", metin).strip()
    pozlar = [(m.start(), m.group(1)) for m in re.finditer(r"(?i)MADDE\s+(\d+)\s*[-–—]?", norm)]
    cikti = []
    if pozlar:
        giris = norm[: pozlar[0][0]].strip()
        if len(giris) > MIN_UZUNLUK:
            cikti.append((f"mevzuat-{no}-giris", giris, None))
        for i, (bas, n) in enumerate(pozlar):
            son = pozlar[i + 1][0] if i + 1 < len(pozlar) else len(norm)
            parca = norm[bas:son].strip()
            if len(parca) > MIN_UZUNLUK:
                cikti.append((f"mevzuat-{no}-madde-{n}", parca, n))
    return cikti


if __name__ == "__main__":
    t0 = time.time()
    adaylar = adaylari_oku("/tmp/yonetmelik-adaylari.txt")
    print(f"{len(adaylar)} aday, PDF dizini: {PDF_DIZIN}", flush=True)
    nokta, belge_say, hata = [], 0, 0
    for dosya in sorted(os.listdir(PDF_DIZIN)):
        if not dosya.endswith(".pdf"):
            continue
        no = dosya[:-4]
        baslik, rg = adaylar.get(no, ("Yönetmelik", ""))
        chunks = maddelere_bol(metni_cikar(f"{PDF_DIZIN}/{dosya}"), no, baslik)
        if not chunks:
            hata += 1
            continue
        for doc_id, metin, n in chunks:
            kay = f"{baslik} — {'GİRİŞ' if n is None else 'MADDE ' + n}"
            payload = {
                "docId": doc_id, "source": kay[:200], "metin": metin[:2000],
                "baslik": baslik[:200], "tur": "yonetmelik", "belgeSinifi": "mevzuat",
                "tarih": rg, "sentetik": False, "jurisdiction": "TR",
            }
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, "legafetch-" + doc_id))
            nokta.append((pid, payload, metin[:2000]))
        belge_say += 1
    print(f"{belge_say} belge → {len(nokta)} madde chunk (hata: {hata})", flush=True)
    limit = int(os.environ.get("YM_LIMIT", "0"))
    if limit:
        nokta = nokta[:limit]
        print(f"PILOT MODU: {limit} chunk ile sınırlandı", flush=True)

    yuklenen = 0
    for i in range(0, len(nokta), BATCH):
        dilim = nokta[i : i + BATCH]
        vecs = main.embeddings.embed_documents([m for _, _, m in dilim])
        puanlar = [
            PointStruct(id=pid, vector=v, payload=p)
            for (pid, p, _), v in zip(dilim, vecs)
        ]
        main.client.upsert(main.collection_name, points=puanlar)
        yuklenen += len(dilim)
        if (i // BATCH) % 10 == 0:
            print(f"  {yuklenen}/{len(nokta)} upsert ({time.time()-t0:.0f} sn)", flush=True)
    print(f"BITTI: {yuklenen} chunk yüklendi — {time.time()-t0:.0f} sn", flush=True)
