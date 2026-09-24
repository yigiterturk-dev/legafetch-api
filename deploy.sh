#!/usr/bin/env bash
# LegaFetch tek komutluk deploy — kullanım (repo kökünde):
#   ./deploy.sh            kodu VPS'e taşı + imajı yeniden kur + health bekle
#   ./deploy.sh --eval     deploy sonrası hızlı kabul ölçümü (eval_erisim)
# Ön koşul: 'netcup' ssh host takma adı kurulu olmalı (bkz. DEPLOY.md).
set -euo pipefail
cd "$(dirname "$0")"

HOST=netcup
HEDEF=/opt/legafetch/api
# Not: '.[e]nv' rsync deseni gizli değişken dosyasını eşler — VPS'teki
# üretim değişken dosyası asla üzerine yazılmasın diye hariç tutulur.
EXCLUDES=(--exclude venv --exclude qdrant_storage --exclude .git
          --exclude '.[e]nv' --exclude __pycache__ --exclude web
          --exclude loglar)

echo "1/4  git push"
git push origin main 2>&1 | tail -1 || true

echo "2/4  rsync -> $HOST:$HEDEF"
rsync -az "${EXCLUDES[@]}" ./ "$HOST:$HEDEF/"

echo "3/4  imaj kurulumu (build + up)"
ssh "$HOST" 'cd /opt/legafetch && docker compose build api 2>&1 | tail -2 && docker compose up -d api 2>&1 | tail -1'

echo "4/4  health bekleniyor (tavan 300 sn)"
for i in $(seq 1 30); do
  durum=$(ssh "$HOST" 'curl -s -m 5 http://127.0.0.1:8000/health || true')
  if echo "$durum" | grep -q '"status":"ok"'; then
    echo "     CANLI: $durum"
    if [ "${1:-}" = "--eval" ]; then
      echo "--- kabul ölçümü: eval_erisim ---"
      ssh "$HOST" 'docker exec -e PYTHONPATH=/app -w /app legafetch-api python eval_erisim.py 2>&1 | grep -a -E "=> |✗" | head -10'
    fi
    exit 0
  fi
  sleep 10
done
echo "HATA: 300 sn içinde health dönmedi — ssh netcup && docker logs legafetch-api" >&2
exit 1
