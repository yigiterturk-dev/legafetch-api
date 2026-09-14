# LegaFetch API — VPS Deploy (Hetzner, 89.167.52.36)

## Mimari
- `legafetch-api` container → `lexordo_default` docker ağı → `http://qdrant:6333`
  (lexordo'nun `lexordo_pasajlar` koleksiyonu, ~8.3M içtihat chunk, salt-okunur)
- TLS: lexordo'nun Caddy'si (`/opt/lexordo/app/deploy/Caddyfile`) → `api.legafetch.com`
- Web: Vercel (`legafetch-web` projesi) → `API_BACKEND_URL=https://api.legafetch.com`

## Dosyalar (VPS)
- `/opt/legafetch-api/` — kod + `compose.yaml` + `.env.production` (chmod 600)
- `.env.production`: `X_API_KEY`, `QDRANT_URL=http://qdrant:6333`, `QDRANT_API_KEY`,
  `QDRANT_COLLECTION=lexordo_pasajlar`, `CORPUS_K=6`, `CORPUS_MAX_PER_BELGE=2`,
  `CORS_ORIGINS`, `RATE_LIMIT_PER_MIN=120`

## Komutlar
```bash
ssh root@89.167.52.36
cd /opt/legafetch-api
docker compose up -d --build   # güncelleme (rsync sonrası)
docker logs -f legafetch-api
```

## Güncelleme akışı (lokal → VPS)
```bash
git push origin main
rsync -az --exclude venv --exclude qdrant_storage --exclude .git --exclude .env \
  -e ssh ./ root@89.167.52.36:/opt/legafetch-api/
ssh root@89.167.52.36 'cd /opt/legafetch-api && docker compose up -d --build'
```

## Uyarılar
- VPS RAM'i dar (15GB): qdrant ~4GB + ithalat ~3.7GB koşarken API `mem_limit: 1200m`
  ile sınırlı. İthalat bitince ONNX embedding'e geçip image'ı küçült (şu an 9.9GB torch-CUDA).
- Qdrant API key'i rotate edilirse `.env.production`'u da güncelle + `docker compose up -d`.
