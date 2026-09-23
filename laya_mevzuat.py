"""LAYA ile mevzuat seçimi — jev_mevzuat ile BİREBİR aynı arayüz.

Neden: jev_mevzuat.py'nin yaptığı işi (bge-reranker'ın ayırt edemediği yerde
son karar) yerel Laya servisiyle, anahtarsız, veri sunucudan çıkmadan yapar.
API şekli aynı: state + questions -> noul. Jev patlarsa çağıran taraf
bge sırasıyla devam eder (aynı güvenli fallback).

Env:
  LAYA_URL      (default http://172.17.0.1:8000 — host köprüsünden laya servisi)
  LAYA_ADAY     (default 10)
  LAYA_ESIK     (default 0.0 — eleme yok)
  LAYA_METIN    (default 700 — madde metni kırpma)
  LAYA_TIMEOUT  (default 30)

🔴 Laya da aritmetik yapmaz — eşik/sıralama kararı KODDA (jev_mevzuat ile aynı).
"""
import json
import os
import urllib.error
import urllib.request

LAYA_URL = os.environ.get("LAYA_URL", "http://172.17.0.1:8000").rstrip("/")
LAYA_ADAY = int(os.environ.get("LAYA_ADAY", "10"))
LAYA_ESIK = float(os.environ.get("LAYA_ESIK", "0.0"))
LAYA_METIN = int(os.environ.get("LAYA_METIN", "700"))
LAYA_TIMEOUT = float(os.environ.get("LAYA_TIMEOUT", "30"))


def yapilandirildi() -> bool:
    return True  # yerel servis; anahtar yok, port ayakta mı diye bakılır


def _cagir(state: dict, questions: dict) -> dict:
    req = urllib.request.Request(
        LAYA_URL + "/predict",
        data=json.dumps({"state": state, "questions": questions}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=LAYA_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def alaka_skorla(soru: str, adaylar: list, metin_al) -> dict:
    """{aday_index: noul} — Laya'ya TEK çağrıda tüm adaylar sorulur.

    Hata durumunda BOŞ sözlük döner: çağıran taraf mevcut bge sıralamasıyla
    devam eder. jev_mevzuat.alaka_skorla ile birebir aynı davranır.
    """
    adaylar = adaylar[:LAYA_ADAY]
    if not adaylar:
        return {}
    state = {"hukuki_soru": soru}
    questions = {}
    for i, d in enumerate(adaylar):
        state[f"madde_{i}"] = (metin_al(d) or "")[:LAYA_METIN]
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
        print(f"[laya] alaka skorlaması atlandı: {e}", flush=True)
        return {}
    out = {}
    for i in range(len(adaylar)):
        a = (yanit.get("answers") or {}).get(f"m{i}") or {}
        if a.get("type") == "noul" and isinstance(a.get("noul"), (int, float)):
            out[i] = float(a["noul"])
    return out


def sirala(soru: str, adaylar: list, metin_al) -> list:
    """Adayları Laya alakasına göre yeniden sırala. Laya yoksa liste aynen döner."""
    skor = alaka_skorla(soru, adaylar, metin_al)
    if not skor:
        return adaylar
    bas = adaylar[:LAYA_ADAY]
    kuyruk = adaylar[LAYA_ADAY:]
    esikli = [(i, d) for i, d in enumerate(bas) if skor.get(i, 0.0) >= LAYA_ESIK]
    elenen = [d for i, d in enumerate(bas) if skor.get(i, 0.0) < LAYA_ESIK]
    esikli.sort(key=lambda t: skor.get(t[0], 0.0), reverse=True)
    return [d for _, d in esikli] + kuyruk + elenen
