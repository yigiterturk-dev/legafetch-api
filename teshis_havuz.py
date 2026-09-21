"""HAVUZ TEŞHİSİ — beklenen madde rerank havuzuna giriyor mu?

Neden: Jev'i (ya da herhangi bir yeniden sıralayıcıyı) hatta koymadan önce
cevaplanması gereken tek soru var — kaçırılan madde ADAY HAVUZUNDA var mı?
Varsa sıralama sorunudur, düzeltilebilir. Yoksa erişim/ithalat sorunudur ve
sıralayıcı hiçbir şey kurtaramaz (bkz. "reranker zayıf" teşhisinin çürümesi).

Kullanım: docker exec -i legafetch-api python /app/teshis_havuz.py
"""
import re
from concurrent.futures import ThreadPoolExecutor

import main
from eval_erisim import SORULAR


def havuz_kur(query):
    """corpus_rank'in mevzuat aday havuzunu birebir yeniden kurar."""
    k = main.CORPUS_K
    with ThreadPoolExecutor(max_workers=3) as h:
        f_aday = h.submit(main.corpus_search, query, max(k, main.CORPUS_FETCH_K), None)
        f_mev = h.submit(main.corpus_search_mevzuat, query, main.CORPUS_MEVZUAT_FETCH_K, None)
        f_bm25 = (h.submit(main._mevzuat_bm25_ara, query, main.CORPUS_MEVZUAT_BM25_K, None)
                  if main.CORPUS_MEVZUAT_BM25_K > 0 else None)
        aday = f_aday.result()
        mev_ham = f_mev.result()
        mev_bm25 = f_bm25.result() if f_bm25 is not None else []
    genis = main.mevzuat_havuz_daralt(query, mev_ham)
    mev_aday = genis[:main.CORPUS_MEVZUAT_K]
    mev_aday = main.mevzuat_havuz_daralt(
        query, [d for d in aday if d.metadata.get("tur") == "mevzuat"] + mev_aday)
    mev_aday = main._tekillestir(mev_aday + mev_bm25)
    return mev_ham, genis, mev_aday


def docid(d):
    return d.metadata.get("docId", "") or d.metadata.get("source", "")


print(f"CORPUS_MEVZUAT_FETCH_K={main.CORPUS_MEVZUAT_FETCH_K} "
      f"CORPUS_MEVZUAT_K={main.CORPUS_MEVZUAT_K} "
      f"MEVZUAT_GARANTI={main.MEVZUAT_GARANTI} "
      f"MIN_ANAHTAR={main.MEVZUAT_MIN_ANAHTAR_ORANI}")

ozet = {"ham": 0, "daralt": 0, "rerank_havuz": 0, "yok": 0}
for soru, desen in SORULAR:
    rx = re.compile(desen)
    ham, genis, aday = havuz_kur(soru)
    yer = lambda liste: next((i for i, d in enumerate(liste, 1) if rx.search(docid(d))), 0)
    p_ham, p_genis, p_aday = yer(ham), yer(genis), yer(aday)
    if p_aday:
        durum = f"havuzda @{p_aday}/{len(aday)}"
        ozet["rerank_havuz"] += 1
        d = aday[p_aday - 1]
        oran = main._anahtar_hit_orani(soru, d.page_content)
        durum += f"  anahtar_orani={oran:.2f}"
    elif p_genis:
        durum = f"DARALTMADA var @{p_genis} ama havuza GİRMEDİ (kota {main.CORPUS_MEVZUAT_K})"
        ozet["daralt"] += 1
    elif p_ham:
        durum = f"dense'te @{p_ham} ama DARALTMA ELEDİ"
        ozet["ham"] += 1
    else:
        durum = f"HİÇ YOK (dense {len(ham)} aday)"
        ozet["yok"] += 1
    print(f"{soru[:50]:<52} | {durum}")

print(f"\nÖZET: rerank havuzunda {ozet['rerank_havuz']}/{len(SORULAR)} | "
      f"daraltmada kaldı {ozet['daralt']} | daraltma eledi {ozet['ham']} | hiç yok {ozet['yok']}")
