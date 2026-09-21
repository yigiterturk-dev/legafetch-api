#!/bin/bash
# Kalite denetimi: uretim hattindan (/api/chat) temsilci sorgular -> kaynak + pasaj basi
docker exec -i legafetch-api python - <<'PY'
import os, json, time, urllib.request

SORULAR = [
    "iscinin haber vermeden isten ayrilmasi kidem tazminati alabilir mi",
    "kira artisi yuzde 25 tavani hangi donemde uygulanir",
    "tuketici sozlesmesindeki haksiz madde iptali davasi",
    "icra takibine itiraz eden borclu icin 7 gun sure",
    "arabuluculuga basvurmadan is davasina bakilabilir mi",
    "yillik ucretli izin hakki kac gundur",
    "tazminat davasinda faiz karar tarihinden mi isler",
    "haciz yolundan maruz kalan borclunun itiraz sureleri",
    "kentsel donusumde pay sahibinin rizasi olmadan yikim olur mu",
    "nafaka alim talebi hangi sartlarla kabul edilir",
]
for q in SORULAR:
    req = urllib.request.Request(
        "http://localhost:8000/api/chat",
        data=json.dumps({"query": q, "jurisdiction": "TR"}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": os.environ["X_API_KEY"]},
    )
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=180)
        d = json.loads(r.read())
    except Exception as e:
        print(f"SORU: {q}\n  HATA: {e}\n", flush=True)
        continue
    print(f"SORU: {q}  [%.1fs]" % (time.time() - t0), flush=True)
    for i, s in enumerate(d["sources"][:4]):
        print(f"  [{i+1}] {s['source'][:72]}", flush=True)
    print(flush=True)
PY
