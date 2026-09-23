"""Laya'lı mevzuat seçimi — eval_jev.py ile aynı ölçüm çerçevesi, yan yana.

Kullanım (stack ayaktayken):
  docker exec -i legafetch-api python /app/eval_laya.py [erisim|dogrulama|kapsam]
Jev kolonu yalnızca JEV_AI_API_KEY konteynerde tanımlıysa koşar (masrafsız değil).
"""
import re
import sys
import time

import main
import laya_mevzuat

K = 5


def _docid(d):
    return d.metadata.get("docId", "") or d.metadata.get("source", "")


def _metin(d):
    baslik = d.metadata.get("source", "") or ""
    return f"{baslik}\n{d.page_content or ''}"


def havuz(query):
    k = main.CORPUS_K
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as h:
        f_aday = h.submit(main.corpus_search, query, max(k, main.CORPUS_FETCH_K), None)
        f_mev = h.submit(main.corpus_search_mevzuat, query, main.CORPUS_MEVZUAT_FETCH_K, None)
        aday = f_aday.result()
        mev_ham = f_mev.result()
    mev_aday = main.mevzuat_havuz_daralt(query, mev_ham)[:main.CORPUS_MEVZUAT_K]
    mev_aday = main.mevzuat_havuz_daralt(
        query, [d for d in aday if d.metadata.get("tur") == "mevzuat"] + mev_aday)
    mev_aday = main._tekillestir(mev_aday)
    ictihat_aday = [d for d in aday if d.metadata.get("tur") != "mevzuat"]
    return main.rerank_scored(query, main._tekillestir(ictihat_aday + mev_aday))


def _mevzuat_tekil(query, skorlu):
    """bge skoru + anahtar boost ile sıralı, TEKİL mevzuat adayları."""
    mev = []
    for d, s in skorlu:
        if d.metadata.get("tur") != "mevzuat":
            continue
        ham = s if s is not None else 0.0
        oran = main._anahtar_hit_orani(query, d.page_content)
        mev.append((d, ham + main.MEVZUAT_KW_BOOST * oran))
    mev.sort(key=lambda x: x[1], reverse=True)
    tekil, gorulen = [], set()
    for d, _ in mev:
        kaynak = d.metadata.get("source", "")
        if kaynak in gorulen:
            continue
        gorulen.add(kaynak)
        tekil.append(d)
    return tekil


def hat_laya(query, k=K):
    """corpus_rank ile aynı, tek fark: mevzuat sıralamasını LAYA yapar."""
    skorlu = havuz(query)
    tekil = _mevzuat_tekil(query, skorlu)
    secim = laya_mevzuat.sirala(query, tekil, _metin)[:main.MEVZUAT_GARANTI]
    ictihat = [d for d, _ in skorlu if d.metadata.get("tur") != "mevzuat"]
    return secim + ictihat[:max(0, k - len(secim))]


def hat_jev(query, k=K):
    """aynı hat, sıralayıcı olarak jev_mevzuat — doğrudan kıyas için."""
    import jev_mevzuat
    skorlu = havuz(query)
    tekil = _mevzuat_tekil(query, skorlu)
    secim = jev_mevzuat.sirala(query, tekil, _metin)[:main.MEVZUAT_GARANTI]
    ictihat = [d for d, _ in skorlu if d.metadata.get("tur") != "mevzuat"]
    return secim + ictihat[:max(0, k - len(secim))]


def olc(sorular, yol, etiket):
    hit, rr, sure, satir = 0, 0.0, [], []
    for soru, desen in sorular:
        t0 = time.time()
        try:
            docs = yol(soru, K)[:K]
        except Exception as e:
            satir.append(("HATA", soru[:52], str(e)[:60]))
            continue
        sure.append(time.time() - t0)
        rx = re.compile(desen)
        s = next((i for i, d in enumerate(docs, 1) if rx.search(_docid(d))), 0)
        if s:
            hit += 1
            rr += 1.0 / s
            satir.append((f"  ✓ @{s}", soru[:52], docs[s-1].metadata.get("source", "")[:58]))
        else:
            ilk = docs[0].metadata.get("source", "")[:58] if docs else "(boş)"
            satir.append(("  ✗   ", soru[:52], f"1.: {ilk}"))
    n = len(sorular)
    print(f"\n--- {etiket} ---")
    for s in satir:
        print(f"{s[0]} | {s[1]:<54} | {s[2]}")
    print(f"  => hit@{K} = {hit}/{n} (%{100*hit/n:.0f})   MRR@{K} = {rr/n:.3f}   "
          f"ort. {sum(sure)/len(sure) if sure else 0:.1f} sn/sorgu")
    return hit, rr / n


if __name__ == "__main__":
    hangi = sys.argv[1] if len(sys.argv) > 1 else "dogrulama"
    if hangi == "dogrulama":
        from eval_dogrulama import SORULAR
    elif hangi == "kapsam":
        from eval_kapsam import SORULAR
    else:
        from eval_erisim import SORULAR
    print(f"Laya kıyası — set={hangi}, {len(SORULAR)} soru, "
          f"LAYA_ADAY={laya_mevzuat.LAYA_ADAY} LAYA_ESIK={laya_mevzuat.LAYA_ESIK} "
          f"URL={laya_mevzuat.LAYA_URL} MEVZUAT_K={main.CORPUS_MEVZUAT_K} GARANTI={main.MEVZUAT_GARANTI}")
    olc(SORULAR, main.corpus_rank, "MEVCUT (bge + anahtar boost + gürültü kapıları)")
    olc(SORULAR, hat_laya, "LAYA (mevzuat sıralaması Laya'da, kapılar aynı)")
    try:
        import jev_mevzuat
        if jev_mevzuat.yapilandirildi():
            olc(SORULAR, hat_jev, "JEV (aynı hat, sıralayıcı Jev)")
        else:
            print("\n--- JEV kolonu atlandı (JEV_AI_API_KEY yok) ---")
    except Exception as e:
        print(f"\n--- JEV kolonu atlandı ({e}) ---")
