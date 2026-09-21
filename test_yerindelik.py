"""ATFIN YERINDELIGI — atif VAR MI degil, DOGRU YERE mi?

test_atif.py bir onceki sorusu yanitlar: cevaptaki madde/karar korpusta
gercekten var mi (uydurma orani %0 cikti). Ama "var olan bir maddeye
alakasiz yerde atif" o olcumden TEMIZ gecer. Avukat icin ikisi de hatali.

Bu dosya uc seyi ayri ayri olcer:

1. DAYANAK (deterministik): cevapta anilan her kanun maddesi, o soruda
   modele SUNULAN kaynaklar arasinda var mi? Yoksa model onu baglamdan
   degil kendi ezberinden yazmistir — korpusta bulunsa bile risklidir
   (mulga/degisik metin olabilir, hat onu dogrulamamistir).
2. ISARET GECERLILIGI (deterministik): metindeki [n] isaretleri kaynak
   listesinin disina tasiyor mu ([7] varken 6 kaynak sunulmussa uydurma).
3. YERINDELIK (LLM hakem, istege bagli): [n] iceren her cumle ile o
   kaynagin korpustaki GERCEK metni hakeme verilir: pasaj bu cumleyi
   destekliyor mu? EVET / KISMEN / HAYIR.

Kosma:
    docker exec legafetch-api python /app/test_yerindelik.py         # 1+2
    HAKEM=1 docker exec ... python /app/test_yerindelik.py           # 1+2+3
Hakem ~0,01 $ mertebesinde tutar (gpt-4o-mini, cumle basina tek cagri).
"""
import json
import os
import re
import urllib.request

import main
from qdrant_client.models import FieldCondition, Filter, MatchValue

API = "http://localhost:8000/api/chat"
ANAHTAR = os.environ.get("X_API_KEY", "")
HAKEM = os.environ.get("HAKEM", "") not in ("", "0", "hayir")
HAKEM_MODEL = os.environ.get("HAKEM_MODEL", "gpt-4o-mini")

SORULAR = [
    "işçinin kıdem tazminatı hesabında giydirilmiş ücret nasıl bulunur",
    "kiracının tahliyesi için hangi sebeplere dayanılabilir",
    "itirazın iptali davası hangi sürede açılır",
    "yoksulluk nafakası hangi şartlarda bağlanır",
    "ayıplı malda tüketicinin seçimlik hakları nelerdir",
    "istinaf başvuru süresi kaç haftadır",
]

MADDE_DESEN = re.compile(
    r"(\d{3,4})\s*[Ss]ay[ıi]l[ıi][^.\n]{0,60}?(?:madde|m\.)\s*(\d+)")
# "6502 ... 11. maddesi" bicimi
MADDE_DESEN2 = re.compile(
    r"(\d{3,4})\s*[Ss]ay[ıi]l[ıi][^.\n]{0,60}?(\d+)\s*\.\s*madde")
ISARET_DESEN = re.compile(r"\[(\d+)\]")
KAYNAK_MADDE = re.compile(r"^(\d{3,4})\s*Sayılı\s*(.*?)\s*—\s*MADDE\s*(\d+)", re.IGNORECASE)
# "Türk Borçlar Kanunu'nun 350. maddesi" — numara yazilmadan yapilan atif.
# Kanun ADI -> NUMARA eslemesi o cevapta sunulan kaynaklardan uretilir; boylece
# tablo elle guncellenmez ve korpusta olmayan bir ada yanlis numara atanmaz.
MADDE_SON = r"(?:(\d+)\s*\.\s*madde|(?:madde|m\.)\s*(\d+))"


def sor(soru):
    istek = urllib.request.Request(
        API, data=json.dumps({"query": soru, "jurisdiction": "TR"}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": ANAHTAR})
    with urllib.request.urlopen(istek, timeout=180) as r:
        return json.load(r)


def kaynak_maddeleri(kaynaklar):
    """Sunulan kaynaklardan (kanun_no, madde_no) ikilileri ve ad->no eslemesi."""
    ikili, adlar = set(), {}
    for k in kaynaklar:
        m = KAYNAK_MADDE.match(k)
        if m:
            no, ad, madde = m.group(1), m.group(2), m.group(3)
            ikili.add((no, madde))
            ad = re.sub(r"\s*\(.*?\)", "", ad).strip()  # "(mülga — m.14 yürürlükte)"
            if len(ad) > 8:
                adlar.setdefault(ad, set()).add(no)
    # 🔴 Ayni ad birden fazla numaraya denk geliyorsa (1475 ve 4857 ikisi de
    #    "Is Kanunu") o addan numara TURETILEMEZ; atfi yanlis kanuna yazmaktansa
    #    hic sayma. Ilk kosuda tam bu yuzden sahte bir "dayanaksiz" uretilmisti.
    tek = {ad: list(nos)[0] for ad, nos in adlar.items() if len(nos) == 1}
    return ikili, tek


def numarasiz_atiflar(metin, adlar):
    """'Türk Borçlar Kanunu'nun 350. maddesi' -> ('6098', '350')."""
    bulunan = set()
    for ad, no in adlar.items():
        for m in re.finditer(re.escape(ad) + r"[^.\n]{0,20}?" + MADDE_SON, metin):
            madde = m.group(1) or m.group(2)
            if madde:
                bulunan.add((no, madde))
    return bulunan


def sunulan_pasajlar(soru):
    """Modelin O SORUDA gercekten gordugu pasajlar, [n] sirasiyla.

    🔴 Ilk surumde hakeme, atif yapilan KARARIN korpustaki rastgele 4 parcasi
    veriliyordu. Kararlar parcali saklaniyor (bir parca ~100 karakter) ve scroll
    sirasi rastgele: hakem, modelin hic gormedigi bir metin uzerinden "destekliyor
    mu" diye yargiliyordu — yerindelik degil gurultu olculur. Simdi uretim
    hattinin kendi siralamasi (corpus_rank + authority_score) tekrar kosuluyor
    ve llm_cevap'in modele verdigi 900 karakterlik ayni kesit kullaniliyor.
    """
    docs = main.corpus_rank(soru)
    ranked = sorted(docs, key=lambda d: d.metadata.get("authority_score", 50), reverse=True)
    return [(d.metadata.get("source", ""), (d.page_content or "")[:900]) for d in ranked]


def govde_metni(metin):
    """Cevabin sonundaki 'Kaynaklar:' listesi cumle degildir.

    API yaniti = uretilen metin + "\n\nKaynaklar:\n[1] ...". O satirlar
    "[4] Istanbul Bolge Adliye Mahkemesi 12." diye cumle gibi gorunup hakeme
    gidiyor ve haksiz KISMEN uretiyordu.
    """
    return re.split(r"\n\s*Kaynaklar:\s*\n", metin)[0]


def cumleler(metin):
    for ham in re.split(r"(?<=[.!?])\s+|\n+", metin):
        c = ham.strip()
        if len(c) > 25 and ISARET_DESEN.search(c):
            yield c


def hakem_sor(cumle, pasaj):
    # Imajda `openai` paketi YOK; main.py da uretici katmani duz HTTP ile
    # cagiriyor. Olcum araci uretim hattiyla ayni sozlesmeyi kullansin.
    istem = (
        "Asagida bir hukuki cevaptan alinmis CUMLE ve o cumlenin atif yaptigi "
        "KAYNAK PASAJ var. Pasaj bu cumledeki hukuki iddiayi destekliyor mu?\n"
        "Yalniz tek kelime yaz: EVET (pasaj iddiayi acikca destekliyor), "
        "KISMEN (ilgili konu ama iddiayi tam karsilamiyor), "
        "HAYIR (pasaj baska bir konuda, atif yersiz).\n\n"
        f"CUMLE: {cumle}\n\nKAYNAK PASAJ: {pasaj}\n\nCEVAP:"
    )
    govde = json.dumps({
        "model": HAKEM_MODEL, "max_tokens": 4, "temperature": 0,
        "messages": [{"role": "user", "content": istem}],
    }).encode()
    istek = urllib.request.Request(
        f"{main.OPENAI_BASE_URL}/chat/completions", data=govde,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {main.OPENAI_API_KEY}"})
    with urllib.request.urlopen(istek, timeout=60) as r:
        y = json.load(r)
    s = (y["choices"][0]["message"]["content"] or "").strip().upper()
    for etiket in ("EVET", "KISMEN", "HAYIR"):
        if s.startswith(etiket):
            return etiket
    return "?"


t_atif = t_dayanaksiz = t_isaret = t_tasan = 0
hakem_sayac = {"EVET": 0, "KISMEN": 0, "HAYIR": 0, "?": 0, "pasaj_yok": 0}

for soru in SORULAR:
    try:
        cevap = sor(soru)
    except Exception as e:
        print(f"❌ ISTEK HATASI: {soru[:40]} -> {e}")
        continue
    metin = cevap.get("text") or ""
    kaynaklar = [(k.get("source") or "") if isinstance(k, dict) else str(k)
                 for k in (cevap.get("sources") or [])]
    print(f"\n{'='*72}\nSORU: {soru[:62]}")
    if not metin:
        print("  ⚠️  cevap BOS — LLM katmani kapali olabilir")
        continue
    sunulan, adlar = kaynak_maddeleri(kaynaklar)
    pasajlar = sunulan_pasajlar(soru) if HAKEM else []

    # 1) dayanak
    anilan = (set(MADDE_DESEN.findall(metin)) | set(MADDE_DESEN2.findall(metin))
              | numarasiz_atiflar(metin, adlar))
    for kanun, madde in sorted(anilan):
        t_atif += 1
        if (kanun, madde) in sunulan:
            print(f"  ✅ {kanun} m.{madde} — sunulan kaynakta (dayanakli)")
        else:
            t_dayanaksiz += 1
            print(f"  🔴 {kanun} m.{madde} — SUNULAN KAYNAKTA YOK (ezberden yazilmis)")

    # 2) isaret gecerliligi
    for n in {int(x) for x in ISARET_DESEN.findall(metin)}:
        t_isaret += 1
        if n < 1 or n > len(kaynaklar):
            t_tasan += 1
            print(f"  🔴 [{n}] isareti kaynak listesinin disinda (kaynak: {len(kaynaklar)})")

    # 3) yerindelik
    if not HAKEM:
        continue
    for c in cumleler(govde_metni(metin)):
        for n in {int(x) for x in ISARET_DESEN.findall(c)}:
            if not (1 <= n <= len(kaynaklar)):
                continue
            # [n] uretim siralamasindaki n. pasaj; kaynak adi tutmuyorsa
            # olcum kaymistir, o cumleyi sayma.
            if n > len(pasajlar) or pasajlar[n - 1][0] != kaynaklar[n - 1]:
                hakem_sayac["pasaj_yok"] += 1
                continue
            pasaj = pasajlar[n - 1][1]
            if not pasaj:
                hakem_sayac["pasaj_yok"] += 1
                continue
            karar = hakem_sor(c, pasaj)
            hakem_sayac[karar] += 1
            if karar != "EVET":
                print(f"  ⚠️  {karar}: «{c[:70]}…» → [{n}] {kaynaklar[n-1][:50]}")

print(f"\n{'='*72}")
print(f"DAYANAK  : {t_atif} madde atfi, sunulan kaynakta OLMAYAN {t_dayanaksiz}"
      + (f" (%{100*t_dayanaksiz/t_atif:.0f})" if t_atif else ""))
print(f"ISARET   : {t_isaret} farkli [n], listeyi TASAN {t_tasan}")
if HAKEM:
    top = sum(v for k, v in hakem_sayac.items() if k in ("EVET", "KISMEN", "HAYIR"))
    print(f"YERINDELIK ({HAKEM_MODEL}): {hakem_sayac}"
          + (f" | yerinde oran %{100*hakem_sayac['EVET']/top:.0f}" if top else ""))
