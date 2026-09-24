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

---

# Dense çekim (A) teşhisi — 2026-09-24

`teshis_dense.py` 15 kayıp soruyu altı koldan ölçtü (12 sn):

- **var: 15/15 OK** — ithalat suçsuz.
- **ayna: hepsi @1** — hedef maddenin kendi metni sorgu yapılınca 1. sırada;
  vektörler kusursuz, gömme tarafında bozukluk yok.
- **13 soru**: k=24'te zaten çekiliyor → kota düzeltmesiyle hatta düşmüşler.
- **2 soru "sadece k"**: 6102-553 (mevcut YOK, k48→@44, k96→@49) ve
  6098-112/114 (mevcut YOK, k48→@53, k96→@61). Anahtar probe ve BM25 de
  göremiyor (bm25 kolonunda ikisi de YOK).

**Karar:** `CORPUS_MEVZUAT_FETCH_K` 24 → 48. Ayna kanıtına göre sorun
vektör değil pencere; pencereyi büyütmek yeterli. Rerank dilimi (8) değişmediği
için maliyet yalnızca Qdrant fetch boyutu.

Doğrulama: değişiklik sonrası üç set yeniden koşulmalı (61/70 bazına karşı).

---

# FETCH_K 24 vs 48 — aynı gün A/B — 2026-09-24

`CORPUS_MEVZUAT_FETCH_K=48` canlıya alındı, üç set koşuldu; ardından aynı
külliyatla 24'e dönülüp tekrar koşuldu. Zemin: `teshis_dense.py` çıktısı —
6102-553 ve 6098-112/114 k=24 penceresinde YOK (k=48'de @44/@53), ayna probe
ile kendi metinleri @1 → vektörler sağlam, sorun çekim derinliği + D aşaması.

| set | baz (09-21) | fetch=24 (bugün) | fetch=48 (bugün) |
|---|---|---|---|
| erişim | 17 | 17 | 17 |
| doğrulama | 18 | 18 | 18 |
| kapsam | 26 | 25 | 25 |
| **toplam** | **61 (%87)** | **60 (%86)** | **60 (%86)** |

**Okuma:** 24 ve 48 bugün birebir aynı; baz farkı (−1) külliyat büyümesinden
(9.86M→9.87M içtihat), düğmeden değil.

**Karar:** 48'de kal. Hedeflenen 2 soru 24'te havuza hiç giremiyor — D
aşaması (rerank/kota) düzeltilse bile 24'te kurtarılamazlardı. 48 onların
havuza girmesini sağlar; D düzeltmesiyle kurtulabilirler.

**Sıradaki teşhis:** D aşaması — aynı kanunun komşu maddeleri rerank'ta öne
geçiyor: 6102-553→395, 6102-376→633, 6458-54→53, 2004-257→258, 6356-41→44.
`eval_laya.py` (23 Eyl entegrasyonu) Laya'nın bu kayıpları kurtarıp
kurtaramadığını ölçer.

---

# Laya/Jev sıralayıcı kıyası — 2026-09-24 (kapsam seti, 30 soru)

`eval_laya.py` üç kolon koştu (MEVCUT = bge + anahtar boost + kapılar —
canlı hat; LAYA = aynı hat, sıralama `laya_mevzuat.sirala`; JEV =
`jev_mevzuat.sirala`). Laya servisi Hetzner'de, ai-tunnel (172.18.0.1:8100)
üzerinden. Jev bir koşuda 30 sn timeout'u aşan çağrıyla takıldı — ayrı kusur.

| kolon | hit@5 | MRR | sn/sorgu |
|---|---|---|---|
| MEVCUT (canlı) | 25/30 (%83) | 0,778 | 3,9 |
| LAYA | **16/30 (%53)** | 0,431 | 15,0 |
| JEV | 26/30 (%87) | 0,783 | 11,9 |

**Okuma:**
- Laya (mevcut prompt ile) komşu-madde ayrımında bge'den belirgin kötü: −7 soru,
  MRR −0,35, 4× gecikme. Üretim adayı değil.
- Jev +1 soru getiriyor ama 3× gecikme + sorgu başı maliyet + takılma kusuru —
  premium/derin-araştırma modu adayı, varsayılan hat değil.

**Karar:** Sıralayıcı bge'de kalır; 23 Eyl laya/jev bağlantı commit'leri (c44ad10,
79f1d57) imajda değil ve deploy EDİLMEYECEK. D aşaması kayıplarının düzeltmesi
sıralayıcı değişikliği değil: kenar başlığı / madde no eşleşme sinyalleri,
kota ve MEVZUAT_K ayarı — her adım `teshis_madde.py` ile ölçülecek.

---

# Dilim teşhisi + hit_orani dilimi — 2026-09-24 (üçüncü tur)

`teshis_d.py` (Jev kapalı, bge hattı, 70 soru) 9 kayıbın kırılımı:
**7/9'da hedef rerank havuzuna giremiyordu** — dense'de @10-44'te duran madde
K=8'lik dilime giremiyordu; 2/9'da havuzda var ama GARANTI kotası yetmiyordu.
(Jev'in canlıda açık olduğu da bu turda netleşti: eval_48 logunda 496 jev
satırı — yani o ölçümler Jev'li hattın; Jev LLM olduğu için koşudan koşuya
±1 oynuyor. bge hattı tek başına 61/70, 3,7 sn.)

## Grid (üç set × 70 soru, Jev kapalı)
| konfig | erişim | doğrulama | kapsam | toplam | sn/sorgu |
|---|---|---|---|---|---|
| A: dense dilim, K=8 (baz) | 17 | 18 | 25 | 61 (%87) | 3,7 |
| **B: hit_orani dilim, K=8** | **18** | **19** | **28** | **65 (%93)** | **3,1** |
| C: hit_orani dilim, K=16 | 18 | 19 | 27 | 64 (%91) | 4,0 |
| D: dense dilim, K=16 | 17 | 19 | 28 | 64 (%91) | 4,1 |

## Regresyon kontrolleri (aynı gün A/B)
- içtihat: konu@1 %96 → **%96 (DEĞİŞMEDİ)** — ilk okumada −1 sanıldı ama bu
  ölçüm HATASIydı: eval_ictihat tek koşuşta İKİ bölüm basıyor (ÜRETİM + saf
  dense), iki farklı bölüm kıyaslanmıştı. Doğru A/B: her iki konfigde ÜRETİM
  konu@1 = 27/28 (%96), konu@5 ort 0,95, merci %92.
- gürültü: kırmızı 6 → 6 (DEĞİŞMEDİ)
- gecikme: 3,7 → 3,1 sn

## Yayına alma + kabul (canlı konfig, override yok — 2026-09-24)
- `MEVZUAT_DILIM_HIT=1` (kod default'u da 1), imaj rebuild edildi.
- **Jev kapatıldı** (`JEV_SIRALAMA=0`): yeni dilimle Jev'in katkısı ölçüsüz,
  3× gecikme (10+ sn), dış API maliyeti ve takılma kusuru vardı; bge hattı
  65/70'i zaten sağlıyor. Tek env ile geri açılabilir.
- Kabul koşusu (canlı): erişim **18/20 (%90)** MRR 0,733 · doğrulama
  **19/20 (%95)** MRR 0,842 · kapsam **28/30 (%93)** MRR 0,778 · içtihat
  konu@1 **%96** · gürültü 6 · **3,1 sn/sorgu, deterministik.**

**Karar:** `MEVZUAT_DILIM_HIT=1` + `JEV_SIRALAMA=0` yayında. Toplam
**65/70 (%93)** — baz %87'nin üzerinde +4 soru, 3× hızlanma.

---

# Yedek + restore testi + deploy otomasyonu — 2026-09-24 (dördüncü tur)

## deploy.sh
Tek komut: git push + rsync + `docker compose build api` + up + health beklemesi
(300 sn tavan), `--eval` ile kabul ölçümü. İlk gerçek koşu test edildi, yeşil.
Kullanım: repo kökünde `./deploy.sh` (opsiyonel `--eval`).

## Yedek
- 20 Eylül yedeği (36,7 GB) göç gününden kalma ve bayatlamıştı.
- **Yeni snapshot alındı: 24 Eyl 08:27, 37,1 GB, checksum'lu** (iki koşuda
  ikinci kez üretildi; diskte toplam ~110 GB yedek, 839 GB boş alan).
- Not: 3 snapshot var (20 Eyl + 2× 24 Eyl) — eskiyi silmek için ayrı onay.

## Restore testi (izole, prod'a dokunmadan)
- Throwaway qdrant (mem_limit 6g, 127.0.0.1:6335, snapshots rw-mount).
- İlk deneme read-only mount'la takıldı: qdrant recover, snapshots/tmp'ye
  yazmak istiyor → **rw mount gerekiyor** (kusur kaydedildi).
- İkinci deneme 400: recover `location` yolu `snapshots/<koleksiyon>/`
  alt dizinini içermeli.
- **Sonuç: BAŞARILI** — test koleksiyonu `green`, `points_count = 9 876 424`
  = üretimle birebir. Vektör araması test konteynerinde timeout oldu (6g
  mmap kıtlığı — üretim 24g'de bu sorun yok; aramayı ölçmez, bütünlüğü ölçer).
- Gerçek restore kanıtı zaten tarihte: 20 Eyl Hetzner→Netcup göçü bu sürecin
  kendisiydi.

**Kalan:** dış uptime izleme (VPS ölse kim fark eder?) — harici servis ya da
yerel cron önerisi ayrı karar.
