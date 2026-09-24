# LegaFetch — Netcup VPS Deploy (tek makine yığını)

> 2026-09-20'de Hetzner'den Netcup'a taşındı. Eski adres (89.167.52.36) geçersiz.
> Bu doküman 2026-09-24'te canlı health + repo yapısına göre doğrulandı.

## Sunucu
- **Netcup VPS 4000 G12**: 31 GB RAM, 12 vCPU, 1 TB — `159.195.158.36`
- DNS: `legafetch.com`, `www.legafetch.com`, `api.legafetch.com` → hepsi bu makineye A kaydı.
- Hetzner'de 15,6 GB RAM'de Qdrant 14g tavaniyla host'u dibe çekiyordu; burada tek iş
  bu makinede, qdrant tavani **24g**.

## Yığın (tek compose, 5 konteyner)
Kök dizin: `/opt/legafetch/` — `compose.yaml` + `api/` + `web/` + `caddy/Caddyfile` + `qdrant.env`

| konteyner | iş | limit | not |
|---|---|---|---|
| `legafetch-qdrant` | vektör DB (`qdrant/qdrant:v1.18.2`) | 24g | `127.0.0.1:6333` (dışarıya kapalı), autoheal |
| `legafetch-api` | FastAPI (`main.py`, port 8000) | 6g | `hf-cache` volume, gerçek sorgu logları `./api/loglar` |
| `legafetch-web` | Next.js frontend (port 3000) | 1g | `/login` healthcheck |
| `legafetch-caddy` | TLS + reverse proxy (80/443) | — | Caddyfile `/opt/legafetch/caddy/Caddyfile` |
| `legafetch-autoheal` | sağlıksız konteyneri restart eder | 64m | 60 sn aralıkla tarar |

- `api.legafetch.com` → `api:8000`, `legafetch.com` + `www` → `web:3000` (aynı Caddyfile).
- HSTS açık, `Server` başlığı kaldırılmış, zstd/gzip.
- Web'in ayrıca Vercel projesi var (`legafetch-web`), ama birincil yayın **Netcup**'tan; Vercel yedek.

## Qdrant / korpus
- Koleksiyon: `lexordo_pasajlar` (env: `QDRANT_COLLECTION`), e5 çok dilli gömme.
- 2026-09-24 itibarıyla **~9,87M vektör** (`/health` `vector_count`).
- Snapshot'lar: `/opt/legafetch/snapshots`, veri: `/opt/legafetch/qdrant-storage`.
- `CORPUS_K=8` (kota düzeltmesi sonrası; ölçüm için `OLCUM.md`).

## Komutlar
```bash
ssh root@159.195.158.36
cd /opt/legafetch
docker compose ps                      # yığın durumu
docker compose up -d --build           # güncelleme (rsync sonrası)
docker logs -f legafetch-api           # canlı log
```

## Güncelleme akışı (lokal → VPS)
```bash
git push origin main
rsync -az --exclude venv --exclude qdrant_storage --exclude .git \
  --exclude .env --exclude .next --exclude node_modules \
  -e ssh ./ root@159.195.158.36:/opt/legafetch/api/
ssh root@159.195.158.36 'cd /opt/legafetch && docker compose up -d --build api'
```
(web için aynı akış `web/` hedefine; `--build web`.)

## Durum kontrolü (VPS'e girmeden)
```bash
curl -s https://api.legafetch.com/health     # {"status":"ok", ...}
curl -s -o /dev/null -w '%{http_code}\n' https://legafetch.com
# korumalı uç anahtarsız 401 dönmeli (fail-closed):
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://api.legafetch.com/api/chat
```

## Uyarılar
- Qdrant API key rotate edilirse `api/.env.production` + `qdrant.env`'i birlikte güncelle,
  sonra `docker compose up -d api qdrant`.
- Qdrant 6333 yalnız `127.0.0.1`'de yayınlanıyor — makine dışından erişim yok, böyle kalsın.
- `autoheal` etiketli konteynerler healthcheck'i 60 sn üst üste geçmezse restart eder;
  qdrant'ın `start_period`'ı 300 sn (büyük restore sonrası panik yapma).
