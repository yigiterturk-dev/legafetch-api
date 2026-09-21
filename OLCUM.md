# LegaFetch erişim ölçümü — 2026-09-21

Külliyat: **73 kanun / 15.479 mevzuat pasajı** (+ ~9,86M içtihat pasajı).
Hat: `main.corpus_rank` (iki kol + rerank + zorla mevzuat enjeksiyonu), k=5.
Sorgular Türkçe diakritikle. Ölçüm: konteyner içinde, canlı imaj.

| set | soru | hit@5 | MRR@5 | önceki (19 kanun) |
|---|---|---|---|---|
| `eval_erisim.py` | 20 | 15 (%75) | 0,700 | %80 · 0,725 |
| `eval_dogrulama.py` | 20 | 17 (%85) | 0,800 | %85 · 0,825 |
| `eval_kapsam.py` **(yeni)** | 30 | 23 (%77) | 0,700 | — |
| **toplam** | **70** | **55 (%79)** | — | — |

**Külliyat 19→73 kanuna çıkarken erişim bozulmadı**: eski iki set birlikte
32/40 → 32/40 (erişimde −1, doğrulamada ±0; gürültü seviyesinde).

Saf dense (`corpus_search`, enjeksiyonsuz) aynı sette **6/20 (%30)** —
zorla mevzuat enjeksiyonu hâlâ hattın taşıyıcı parçası, kaldırılmamalı.

## Yeni set nasıl kuruldu (hukuki doğrulama)
35 aday soru, kanun başına en çok bir tane, yalnızca eski setlerin
dokunmadığı kanunlardan. Her aday iki kapıdan geçirildi:
1. beklenen `docId` külliyatta VAR mı → 35/35 var;
2. pasajın **metni** sorunun cevabını veriyor mu → gözle okundu, örtüşmeyen
   5 aday (5510-80, 193-94, 3065-29, 5684-30, 5651-9) elendi.
Kalan 30 soru sete alındı. Olmayan/örtüşmeyen maddeyi sormak erişimi değil
ithalatı ölçer.

## Kapsam setinde kaçırılan 7 soru — hepsi KOMŞU MADDE
| soru | beklenen | gelen 1. |
|---|---|---|
| sermaye kaybı / borca batıklık | 6102-376 | 6102-633 |
| yönetim kurulu sorumluluğu | 6102-553 | 6102-338 |
| koşullu salıverilme oranı | 5275-107 | 3713-17 |
| sınır dışı etme kararı | 6458-54 | 6458-53 |
| önleyici tedbir kararları | 6284-5 | 6284 (başka madde) |
| toplu iş sözleşmesi yetkisi | 6356-41 | 6356-Gecici-6 |
| vatandaşlığın kazanılma şartları | 5901-11 | 5901-10 |

Yani hat doğru KANUNU bulup yanlış MADDEyi seçiyor (7'nin 5'inde aynı
kanun). Sıradaki teşhis burada: madde seçimi, kanun seçimi değil.

## Çalıştırma
```
docker exec -e PYTHONPATH=/app -w /app legafetch-api python eval_erisim.py
docker exec -e PYTHONPATH=/app -w /app legafetch-api python eval_dogrulama.py
docker exec -e PYTHONPATH=/app -w /app legafetch-api python loglar/eval_kapsam.py
python3 kanun_envanter.py     # VPS'te: külliyattaki kanun + madde sayısı dökümü
```
