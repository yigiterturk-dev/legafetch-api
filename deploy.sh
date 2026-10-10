#!/usr/bin/env bash
# LegaFetch tek komutluk deploy — kullanım (repo kökünde):
#   ./deploy.sh            kodu VPS'e taşı + imajı yeniden kur + health bekle
#   ./deploy.sh --eval     deploy sonrası hızlı kabul ölçümü (eval_erisim)
# Ön koşul: 'netcup' ssh host takma adı kurulu olmalı (bkz. DEPLOY.md).
set -euo pipefail
cd "$(dirname "$0")"

HOST="${DEPLOY_HOST:-netcup}"
HEDEF="${DEPLOY_TARGET:-/opt/legafetch/api}"
SERVICES="${DEPLOY_SERVICES:-gateway}"
case "$SERVICES" in
  gateway|"api gateway") ;;
  *) echo "HATA: DEPLOY_SERVICES yalnızca 'gateway' veya 'api gateway' olabilir" >&2; exit 2 ;;
esac
# Not: '.[e]nv' rsync deseni gizli değişken dosyasını eşler — VPS'teki
# üretim değişken dosyası asla üzerine yazılmasın diye hariç tutulur.
EXCLUDES=(--exclude venv --exclude qdrant_storage --exclude .git
          --exclude '.[e]nv' --exclude __pycache__ --exclude web --exclude gateway
          --exclude loglar --exclude gateway/node_modules
          --exclude gateway/dist --exclude web/node_modules --exclude web/.next)

if [ "${CI:-}" != "true" ]; then
  echo "1/5  git push"
  git push origin main 2>&1 | tail -1 || true
else
  echo "1/5  CI deploy — git push skipped"
fi

echo "2/5  rsync -> $HOST:$HEDEF"
rsync -az "${EXCLUDES[@]}" ./ "$HOST:$HEDEF/"
rsync -az --exclude node_modules --exclude dist gateway/ "$HOST:/opt/legafetch/gateway/"
rsync -az --exclude node_modules --exclude .next web/ "$HOST:/opt/legafetch/web/"
rsync -az compose.yaml "$HOST:/opt/legafetch/compose.yaml"
ssh "$HOST" 'mkdir -p /opt/legafetch/caddy'
rsync -az caddy/Caddyfile "$HOST:/opt/legafetch/caddy/Caddyfile"

echo "3/5  mevcut imajları koru + build ($SERVICES)"
ssh "$HOST" "set -e; for image in legafetch-api legafetch-gateway; do docker image inspect \"\$image:latest\" >/dev/null 2>&1 && docker tag \"\$image:latest\" \"\$image:rollback\" || true; done; cd /opt/legafetch; docker compose build $SERVICES 2>&1 | tail -8; docker compose up -d $SERVICES web caddy 2>&1 | tail -4; docker compose restart caddy >/dev/null"

echo "4/5  API + gateway health bekleniyor (tavan 300 sn)"
for i in $(seq 1 30); do
  api_durum=$(ssh "$HOST" 'curl -s -m 5 http://127.0.0.1:8000/health || true')
  gateway_durum=$(ssh "$HOST" 'docker exec legafetch-gateway wget -qO- -T 5 http://127.0.0.1:3001/ready || true')
  if echo "$api_durum" | grep -q '"status":"ok"' && echo "$gateway_durum" | grep -q '"status":"ready"'; then
    echo "     API CANLI: $api_durum"
    echo "     GATEWAY CANLI: $gateway_durum"
    if [ "${1:-}" = "--eval" ]; then
      echo "--- kabul ölçümü: eval_erisim ---"
      ssh "$HOST" 'docker exec -e PYTHONPATH=/app -w /app legafetch-api python eval_erisim.py 2>&1 | grep -a -E "=> |✗" | head -10'
    fi
    exit 0
  fi
  sleep 10
done
echo "5/5  HATA: 300 sn içinde health dönmedi" >&2
echo "     rollback: önceki api/gateway imajları geri alınıyor" >&2
ssh "$HOST" 'for image in legafetch-api legafetch-gateway; do docker image inspect "$image:rollback" >/dev/null 2>&1 && docker tag "$image:rollback" "$image:latest" || true; done; cd /opt/legafetch && docker compose up -d --no-build api gateway web caddy && docker compose ps && docker logs --tail=80 legafetch-api && docker logs --tail=80 legafetch-gateway' >&2 || true
exit 1
