#!/bin/bash
# DEMO MODU — denemeden hemen once calistir:
#   /opt/legafetch-api/demo-modu.sh
# Qdrant saglikli anini bekler, API'yi isitir, GO/NO-GO verir.
set -u
KEY=$(grep -m1 "^QDRANT_API_KEY=" /opt/legafetch-api/.env.production | cut -d= -f2)
echo "1) Qdrant saglik bekleniyor (max 6 dk)..."
for i in $(seq 1 36); do
  H=$(docker inspect -f "{{.State.Health.Status}}" lexordo-qdrant-1 2>/dev/null)
  K=$(curl -s -m 5 -o /dev/null -w "%{http_code}" http://localhost:6333/ 2>/dev/null)
  if [ "$H" = "healthy" ] && [ "$K" = "200" ]; then echo "   OK: qdrant healthy"; break; fi
  [ $((i % 4)) -eq 0 ] && echo "   ... bekleniyor ($i/36) restart=$(docker inspect -f '{{.RestartCount}}' lexordo-qdrant-1 2>/dev/null)"
  sleep 10
done
ST=$(docker inspect -f "{{.State.Health.Status}}" lexordo-qdrant-1 2>/dev/null)
[ "$ST" != "healthy" ] && { echo "NO-GO: qdrant kalkmadi — 5-10 dk sonra tekrar dene"; exit 1; }

echo "2) Koleksiyon durumu:"
DURUM=$(curl -s -m 10 -H "Authorization: Bearer $KEY" http://localhost:6333/collections/lexordo_pasajlar | python3 -c 'import json,sys; d=json.load(sys.stdin)["result"]; print(d["status"], d["points_count"])' 2>/dev/null || echo "bilinemiyor")
echo "   $DURUM"

echo "3) API isi tasiyor (2 test sorgusu)..."
docker exec -i legafetch-api python - <<'PY' 2>/dev/null
import os, json, urllib.request, time
for q in ["kidem tazminati sartlari", "kira artisi tavani"]:
    req = urllib.request.Request(
        "http://localhost:8000/api/chat",
        data=json.dumps({"query": q, "jurisdiction": "TR"}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": os.environ["X_API_KEY"]},
    )
    try:
        t0 = time.time()
        d = json.loads(urllib.request.urlopen(req, timeout=120).read())
        print("   OK: %d kaynak, %.1fs" % (len(d["sources"]), time.time() - t0))
    except Exception as e:
        print("   HATA:", e)
PY

echo "4) Public kontrol:"
KOD=$(curl -s -o /dev/null -m 20 -w "%{http_code}" https://api.legafetch.com/health)
echo "   api.legafetch.com/health -> $KOD"
[ "$KOD" = "200" ] && echo "=== GO — denemeye hazir ===" || echo "=== NO-GO — 5 dk sonra bu scripti tekrar calistir ==="
