"""D ASAMASI (SIRALAMA/KOTA) TEŞHİSİ — bge hattında komşu madde kimden önde?

Kapsam: eval üç setinin TAMAMI (70 soru). Kaçanlar için kırılım basar:

  havuz       daraltma + MEVZUAT_K dilimi + rerank sonrasi mevzuat adaylari
  mev-sıra    boost'lu skora gore (bge + MEVZUAT_KW_BOOST x hit_orani)
              hedef maddenin mevzuat havuzundaki sirasi
  kapı/kota   hedef MIN_ANAHTAR_ORANI'na takildi mi / GARANTI kotasina giremedi mi
  final       corpus_rank'in uretim siralamasi (hedef @N veya YOK)

Jev kapali kosar (JEV_SIRALAMA=0): deterministik, 3x hizli bge hatti
ölçülür — düzeltme oraya yapilacak, Jev zaten +1'i 3x maliyetle aliyor.

Kullanım (stack ayaktayken):
  docker exec -e PYTHONPATH=/app -w /app -e JEV_SIRALAMA=0 \
      legafetch-api python teshis_d.py
"""
import re
import time

import main
import eval_laya  # havuz() ve _metin() buradan — eval ile ayni yol

from eval_erisim import SORULAR as E
from eval_dogrulama import SORULAR as D
from eval_kapsam import SORULAR as K


def _docid(d):
    return str((d.metadata or {}).get("docId") or "")


def _bul(docs, rx):
    for i, d in enumerate(docs, 1):
        if re.search(desen_rx, _docid(d)):
            return i, d
    return 0, None


if __name__ == "__main__":
    t0 = time.time()
    print(f"D TEŞHİSİ — JEV_SIRALAMA={main.JEV_SIRALAMA} (0=bge hatti)  "
          f"KW_BOOST={main.MEVZUAT_KW_BOOST}  GARANTI={main.MEVZUAT_GARANTI}  "
          f"hit_min={main.MEVZUAT_MIN_ANAHTAR_ORANI}\n")
    toplam, kayip = 0, 0
    for set_adi, SORULAR in (("erisim", E), ("dogrulama", D), ("kapsam", K)):
        print(f"########## {set_adi} ({len(SORULAR)} soru) ##########")
        for soru, desen in SORULAR:
            toplam += 1
            desen_rx = re.compile(desen)
            son = main.corpus_rank(soru, 5)
            sira, _ = _bul(son, desen_rx)
            if sira:
                continue  # isabet — dökme
            kayip += 1
            # --- kirim: mevzuat kolunu aynen oynat (rerank cift kere yapilmaz) ---
            skorlu = eval_laya.havuz(soru)
            mev = []
            for d, s in skorlu:
                if d.metadata.get("tur") != "mevzuat":
                    continue
                ham = s if s is not None else 0.0
                hit = main._anahtar_hit_orani(soru, d.page_content)
                mev.append((d, ham, hit, ham + main.MEVZUAT_KW_BOOST * hit))
            mev.sort(key=lambda t: t[3], reverse=True)
            mev_sira, hedef_k = 0, None
            for i, (d, ham, hit, b) in enumerate(mev, 1):
                if re.search(desen_rx, _docid(d)):
                    mev_sira, hedef_k = i, (ham, hit, b)
            kazanan = mev[0] if mev else None
            print(f"\n✗ {soru[:64]}")
            if hedef_k:
                print(f"  hedef: mev-havuz @ {mev_sira}/{len(mev)} | "
                      f"bge={hedef_k[0]:.3f} hit={hedef_k[1]:.2f} boostlu={hedef_k[2]:.3f}")
            else:
                print(f"  hedef: MEVZUAT HAVUZUNA GIRREMEDI ({len(mev)} aday)")
            if kazanan:
                kd, kh, khit, kskor = kazanan
                print(f"  kazanan: {_docid(kd)} bge={kh:.3f} hit={khit:.2f} boostlu={kskor:.3f}")
            print(f"  final 5: " + " | ".join(
                f"{_docid(d)[:28] or d.metadata.get('source','')[:28]}"
                for d in son))
    print(f"\n=== {toplam} soru, {kayip} kayip — Jev'siz bge hatti ===")
