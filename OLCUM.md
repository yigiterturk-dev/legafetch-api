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
docker exec -e PYTHONPATH=/app -w /app legafetch-api python teshis_madde.py
docker exec -e PYTHONPATH=/app -w /app legafetch-api python teshis_dense.py
python3 kanun_envanter.py     # VPS'te: külliyattaki kanun + madde sayısı dökümü
```

---

# Madde seçimi teşhisi ve düzeltme — 2026-09-21 (aynı gün, ikinci tur)

`teshis_madde.py` 15 kayıp sorunun hangi aşamada düştüğünü ölçer:

| aşama | ne yapar | kaç kayıp |
|---|---|---|
| A dense çekim | `corpus_search_mevzuat(q, 24)` | 2 |
| B kanun-no daraltma | `mevzuat_havuz_daralt` | **0 — suçsuz** |
| C rerank dilimi | `[:CORPUS_MEVZUAT_K=8]` | 6 |
| D rerank + kota | nihai listeye girme | 7 |

**D yapısaldı:** `corpus_rank` nihai cevaba en fazla **2** kanun maddesi
koyuyordu (`len(mev_eniyi) == 2`). Kural mevzuat 19 kanunken konmuştu; 73
kanunda doğru madde sık sık üçüncü sıraya düşüp cevaba hiç giremiyordu —
havuzda @2'de duran madde bile eleniyordu.

**Düzeltme:** kota `MEVZUAT_GARANTI` ile ayarlanabilir, varsayılan **4**.
`CORPUS_K` 6 → 8 (dayanak artarken içtihat sayısı 4'te kalsın).

| set | kota 2 | **kota 4** |
|---|---|---|
| kapsam (30) | 23 (%77) | **26 (%87)** |
| erişim (20) | 15 (%75) | **17 (%85)** |
| doğrulama (20) | 17 (%85) | **18 (%90)** |
| **toplam (70)** | **55 (%79)** | **61 (%87)** |
| içtihat konu@1 (28) | %96 | %96 (değişmedi) |

Üç setin üçünde de kazandı — parametre yalnız kapsam setinde tarandı,
diğer ikisi görülmemiş doğrulamadır. İçtihat kalitesi bozulmadı.

**Denendi, kazandırmadı:** `CORPUS_MEVZUAT_K` 8 → 16 veya 24 yalnız +1 soru
getirdi (+1,2 sn) çünkü dilime giren madde D aşamasında yine eleniyordu.
Kota düzeldikten sonra yeniden ölçülmeli.

**Kalan 9 kayıp:** 2'si dense çekimin hiç getirmediği (A) sorular —
gömme/sorgu tarafı. Sıradaki teşhis orada.
