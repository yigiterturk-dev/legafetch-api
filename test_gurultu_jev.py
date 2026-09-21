"""GÜRÜLTÜ TESTİ — alakasız soruda Jev mevzuat basmayı reddedebiliyor mu?

Mevcut hattı koruyan şey `MEVZUAT_MIN_ANAHTAR_ORANI` sözcüksel kapısı.
Jev sıralamayı devralırsa o kapı ne olacak? Burada Jev'in kendi alaka
olasılığının kapı görevi görüp göremediği ölçülür.
"""
import sys

import main
import jev_mevzuat
import eval_jev

# test_gurultu.py ile aynı mantık: hukukla ilgisiz sorular
GURULTU = [
    "en iyi tatil yerleri neresi",
    "akşam yemeğine ne pişirsem",
    "hava yarın nasıl olacak",
    "python'da liste nasıl sıralanır",
    "bitcoin fiyatı ne olur",
    "futbol maçı kaçta başlıyor",
    "gemi adamı disiplin cezası",
]

print(f"Gürültü testi — {len(GURULTU)} alakasız soru, JEV_ADAY={jev_mevzuat.JEV_ADAY}")
print(f"{'soru':<34} | mevcut hat | Jev en yüksek alaka | Jev >= esik sayisi")
for q in GURULTU:
    mevcut = [d for d in main.corpus_rank(q, 5) if d.metadata.get("tur") == "mevzuat"]
    skorlu = eval_jev.havuz(q)
    adaylar = eval_jev._mevzuat_sirali(q, skorlu)
    skor = jev_mevzuat.alaka_skorla(q, adaylar, eval_jev._metin)
    en_yuksek = max(skor.values()) if skor else 0.0
    for esik in (0.5,):
        ustu = sum(1 for v in skor.values() if v >= esik)
    print(f"{q[:32]:<34} | {len(mevcut):^10} | {en_yuksek:^19.2f} | {ustu} (>=0.5)")
