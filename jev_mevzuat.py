"""JEV ile mevzuat seçimi — bge-reranker'ın sıralayamadığı yerde son karar.

Neden: ölçüldü (2026-09-21) — beklenen kanun maddesi rerank havuzuna 18/20
giriyor, havuz genişletilince ~20/20 oluyor, AMA hit@5 %85'te çakılı kalıyor.
Havuzu büyütmek "ihtiyati haciz"i düzeltip "itirazın iptali"ni bozdu: net sıfır.
Yani darboğaz erişim değil SIRALAMA; bge-reranker-base kısa kanun maddelerinde
ayırt edemiyor. Jev tam burada devreye girer: metin üretmez, her aday için
"bu madde soruyu cevaplıyor mu" olasılığı döner.

🔴 Jev aritmetik yapmıyor — buraya ham skor/eşik VERİLMEZ, yalnız soru ve
madde metni gider. Eşik/sıralama kararı bu dosyada, KODDA.
"""
import json
import os
import urllib.error
import urllib.request

JEV_URL = os.environ.get("JEV_AI_BASE_URL", "https://api.typesafe.ai").rstrip("/") + "/v1/systemone"
JEV_MODEL = os.environ.get("JEV_AI_MODEL", "jev-latest")
JEV_TIMEOUT = float(os.environ.get("JEV_TIMEOUT", "20"))
JEV_ADAY = int(os.environ.get("JEV_ADAY", "10"))        # Jev'e sorulacak aday sayısı
JEV_ESIK = float(os.environ.get("JEV_ESIK", "0.0"))     # altı elenir (0 = eleme yok)
JEV_METIN = int(os.environ.get("JEV_METIN", "700"))     # madde metni kırpma


def yapilandirildi() -> bool:
    return bool(os.environ.get("JEV_AI_API_KEY", "").strip())


def _cagir(state: dict, questions: dict) -> dict:
    req = urllib.request.Request(
        JEV_URL,
        data=json.dumps({"model": JEV_MODEL, "state": state, "questions": questions}).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + os.environ["JEV_AI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=JEV_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def alaka_skorla(soru: str, adaylar: list, metin_al) -> dict:
    """{aday_index: noul} — Jev'e TEK çağrıda tüm adaylar sorulur.

    Hata durumunda BOŞ sözlük döner: çağıran taraf mevcut bge sıralamasıyla
    devam eder. Jev patlarsa arama bozulmaz, sadece iyileşme olmaz.
    """
    adaylar = adaylar[:JEV_ADAY]
    if not adaylar or not yapilandirildi():
        return {}
    state = {"hukuki_soru": soru}
    questions = {}
    for i, d in enumerate(adaylar):
        state[f"madde_{i}"] = (metin_al(d) or "")[:JEV_METIN]
        questions[f"m{i}"] = {
            "type": "noul",
            "instructions": (
                f"madde_{i} alanındaki kanun maddesi, hukuki_soru alanındaki soruya "
                f"DOĞRUDAN hukuki dayanak oluşturuyor mu? Aynı konu alanında olması "
                f"yetmez; sorulan hakkı, süreyi veya şartı bu madde düzenlemelidir."
            ),
        }
    try:
        yanit = _cagir(state, questions)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as e:
        print(f"[jev] alaka skorlaması atlandı: {e}", flush=True)
        return {}
    out = {}
    for i in range(len(adaylar)):
        a = (yanit.get("answers") or {}).get(f"m{i}") or {}
        if a.get("type") == "noul" and isinstance(a.get("noul"), (int, float)):
            out[i] = float(a["noul"])
    return out


def sirala(soru: str, adaylar: list, metin_al) -> list:
    """Adayları Jev alakasına göre yeniden sırala. Jev yoksa liste aynen döner."""
    skor = alaka_skorla(soru, adaylar, metin_al)
    if not skor:
        return adaylar
    bas = adaylar[:JEV_ADAY]
    kuyruk = adaylar[JEV_ADAY:]
    esikli = [(i, d) for i, d in enumerate(bas) if skor.get(i, 0.0) >= JEV_ESIK]
    elenen = [d for i, d in enumerate(bas) if skor.get(i, 0.0) < JEV_ESIK]
    esikli.sort(key=lambda t: skor.get(t[0], 0.0), reverse=True)
    return [d for _, d in esikli] + kuyruk + elenen
