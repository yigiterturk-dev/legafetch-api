"""DENSE ÇEKİM (A) TEŞHİSİ — maddeyi dense hiç mi getirmiyor, k mı küçük?

teshis_madde.py'nin 2026-09-21 koşusunda 15 kayıptan 2'si A aşamasında
düştü: corpus_search_mevzuat (tam soru + anahtar probe, k=24) hedef maddeyi
hiç getirmedi. Aşamayı bilmeden düzeltme yapılmaz (bkz. BM25 turu).

Bu script aynı kayıp setinde A aşamasını altı koldan ölçer:

  0. VAR MI?       hedef docId külliyatta fiziksel olarak duruyor mu
                   (yoksa sorun embedding değil İTHALAT)
  1. mevcut hat    corpus_search_mevzuat(q, 24)  — baseline (iki probe)
  2. k yolu        aynı hat k=48 ve k=96 (en ucuz düğme)
  3. anahtar yolu  _anahtar_sorgu tek probe, k=48
  4. bm25 yolu     saf lexical (mevzuat_bm25), k=48 — dense körse lexical görür mü
  5. ayna probe    hedef maddenin KENDİ metni sorgu olarak
                   ("passage: ", "query: ", çıplak) — madde vektörü hiç mi
                   tutmuyor, yoksa yalnızca soru-embedding'i mi

Yorum anahtarı:
  ayna bile ıskalıysa -> veri/vektör sorunu (ithalat ya da gömme kalitesi)
  ayna tutuyor ama sorgular ıskalı -> SORGU tarafı (probe/çoklu-sorgu/bm25)
  k=48/96'da çıkıyor -> sorun sadece k; ucuz düğme yeterli

Kullanım (stack ayaktayken):
  docker exec -e PYTHONPATH=/app -w /app legafetch-api python teshis_dense.py
"""
import re
import time

import main
import mevzuat_bm25
from teshis_madde import KAYIPLAR, sira


def _pl_docid(pl: dict) -> str:
    return str(pl.get("docId") or "")


def sira_pl(payloads, rx) -> int:
    for i, pl in enumerate(payloads, 1):
        if rx.search(_pl_docid(pl)):
            return i
    return 0


def dense_bul(sorgu: str, k: int, suzgec=None):
    return main.corpus_search_mevzuat(sorgu, k, suzgec)


def ayna_ranklar(hedef_metin: str, hedef_rx) -> dict:
    """Hedef maddenin kendi metnini sorgu yap — vektörün varlığını test eder."""
    from qdrant_client.models import (
        FieldCondition, Filter, MatchValue,
    )

    suzgec = Filter(
        must=[
            FieldCondition(key="belgeSinifi", match=MatchValue(value="mevzuat")),
            FieldCondition(key="sentetik", match=MatchValue(value=False)),
        ]
    )
    cikti = {}
    for etiket, sorgu in (
        ("passage", "passage: " + hedef_metin),
        ("query", "query: " + hedef_metin),
        ("ciplak", hedef_metin),
    ):
        vec = main.embeddings.embed_query(sorgu)
        sonuc = main.client.query_points(
            main.collection_name,
            query=vec,
            limit=96,
            query_filter=suzgec,
            with_payload=True,
            with_vectors=False,
        )
        doclar = [
            pl for pt in sonuc.points for pl in [pt.payload or {}]
        ]
        cikti[etiket] = sira_pl(doclar, hedef_rx)
    return cikti


if __name__ == "__main__":
    t0 = time.time()
    print(f"DENSE ÇEKİM TEŞHİSİ — {len(KAYIPLAR)} kayıp soru")
    print(f"FETCH_K={main.CORPUS_MEVZUAT_FETCH_K}  MEVZUAT_K={main.CORPUS_MEVZUAT_K}\n")

    # 0. adım: külliyatı bir kez çek — varlık kontrolü + bm25 + ayna metni
    print("mevzuat külliyatı çekiliyor...")
    havuz = mevzuat_bm25._mevzuati_cek(main.client, main.collection_name)
    docid_set = {did for did, _, _ in havuz}
    print(f"  {len(havuz)} mevzuat pasajı\n")

    try:
        bm25 = mevzuat_bm25.BM25Indeks(havuz)
        print(f"[bm25] indeks hazır ({time.time() - t0:.0f} sn)\n")
        bm25_hazir = True
    except Exception as e:  # bm25 çökerse diğer kollar ölçülmeye devam etsin
        print(f"[bm25] kurulamadı: {e}\n")
        bm25_hazir = False

    print(f"{'soru':<44} | {'var':>4} | {'mevcut':>8} | {'k48':>7} | {'k96':>7} | "
          f"{'anahtar':>8} | {'bm25':>7} | {'ayna':>12}")
    print("-" * 118)

    sayim = {"yok": 0, "ayna_iskaladı": 0, "k_yolu": 0, "anahtar": 0, "bm25": 0, "zaten": 0, "kör": 0}
    for soru, desen in KAYIPLAR:
        rx = re.compile(desen)

        # 0. varlık
        var = any(rx.search(d) for d in docid_set)

        # 1-2. dense yolları
        m24 = sira(dense_bul(soru, 24), rx)
        m48 = sira(dense_bul(soru, 48), rx)
        m96 = sira(dense_bul(soru, 96), rx)

        # 3. anahtar probe
        a48 = sira(main._mevzuat_dense_ara(main._anahtar_sorgu(soru), 48), rx)

        # 4. bm25
        b48 = sira_pl([pl for pl, _ in bm25.ara(soru, 48)], rx) if bm25_hazir else -1

        # 5. ayna — hedefin kendi metni sorgu olarak
        hedef_pl = next((pl for did, _, pl in havuz if rx.search(did)), None)
        if hedef_pl:
            metin = (hedef_pl.get("metin") or "")[:600]
            ayna = ayna_ranklar(metin, rx)
            ayna_str = "/".join(f"{k}:{v or '-'}" for k, v in ayna.items())
            ayna_hit = any(ayna.values())
        else:
            ayna_str = "hedef yok"
            ayna_hit = False

        print(f"{soru[:44]:<44} | {('OK' if var else 'YOK'):>4} | "
              f"{('yok' if not m24 else m24):>8} | {('yok' if not m48 else m48):>7} | "
              f"{('yok' if not m96 else m96):>7} | {('yok' if not a48 else a48):>8} | "
              f"{('-' if b48 < 0 else ('yok' if not b48 else b48)):>7} | {ayna_str:>12}")

        if not var:
            sayim["yok"] += 1
        elif m24:
            sayim["zaten"] += 1
        elif not ayna_hit:
            sayim["ayna_iskaladı"] += 1
        elif m48 or m96:
            sayim["k_yolu"] += 1
        elif a48:
            sayim["anahtar"] += 1
        elif b48 and b48 > 0:
            sayim["bm25"] += 1
        else:
            sayim["kör"] += 1

    print(f"\n--- {time.time() - t0:.0f} sn'de bitti: ne kapatıyor ---")
    etiket = {
        "yok": "İTHALAT SORUNU: hedef docId külliyatta yok (dense suçlu değil)",
        "ayna_iskaladı": "VEKTÖR SORUNU: kendi metniyle bile bulunamıyor — gömme bozuk/eksik",
        "k_yolu": "sadece k: k=48/96'da çıkıyor — ucuz düğme yeterli",
        "anahtar": "anahtar probe ile çıkıyor — probe çeşitlendirmesi",
        "bm25": "yalnız lexical görüyor — BM25 kolunu A'ya bağla",
        "zaten": "mevcut hatta zaten VAR (ölçüm k farkı / kota sonrası düzelmiş)",
        "kör": "hiçbir kol görmedi — manuel inceleme gerekli",
    }
    for k in ("yok", "ayna_iskaladı", "k_yolu", "anahtar", "bm25", "zaten", "kör"):
        if sayim[k]:
            print(f"  {sayim[k]:>2}  {etiket[k]}")
