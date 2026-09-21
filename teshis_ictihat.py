# -*- coding: utf-8 -*-
"""eval_ictihat.py'de kacan sorularin GERCEKTEN mi kactigini gosterir.

Olcut sozcuksel; "kacirdi" dedigi vaka yanlis negatif de olabilir. Karar
metninin basini gozle gormeden "erisim bozuk" denmez.
"""
import re
import sys

import main

SORULAR = sys.argv[1:] or [
    "sigortasız çalıştırılan işçinin hizmet tespiti davası nasıl görülür",
    "tahliye taahhüdüne dayalı tahliye davasında taahhüdün geçerlilik şartları",
    "çocuğun velayetinin belirlenmesinde üstün yararı ilkesi",
]

for soru in SORULAR:
    print("\n=== %s" % soru)
    docs = [d for d in main.corpus_rank(soru, 15) if d.metadata.get("tur") != "mevzuat"]
    for i, d in enumerate(docs[:3], 1):
        metin = re.sub(r"\s+", " ", d.page_content or "")
        print("  %d. %s" % (i, (d.metadata.get("source") or "")[:60]))
        print("     %s" % metin[:260])
