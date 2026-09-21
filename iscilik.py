"""Işçilik alacağı hesabı — SGK hizmet dökümü + fesih belgesinden kıdem/ihbar.

Tasarım kararı: ARİTMETİK BURADA, LLM'DE DEĞİL. Dil modeli yalnızca belgeden
satır çıkarır (dönem, prim günü, kazanç, eksik gün kodu); tutarı bu modül
hesaplar. Avukata rakam veren bir üründe modelin çarpma yapmasına izin vermek
sessiz hata üretir; burada her adım denetlenebilir.

İkinci karar: kıdem tavanı gömülü DEĞİL. `kidem_tavani.json` içinde ve yalnız
"dogrulandi": true satırlar hesapta kullanılır. Eski bir tavan, yanlış olduğunu
söylemeden yanlış sonuç verir.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime

DAMGA_ORANI = 0.00759  # binde 7,59 — kıdem tazminatından yalnız bu kesilir

_TAVAN_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "kidem_tavani.json")

# SGK eksik gün nedenleri. Sadece kıdeme etkisi bilinenler burada; listede
# olmayan kod "belirsiz" sayılır ve elle bakılması istenir. Yanlış kod eşlemesi
# doğrudan yanlış tazminat demek, o yüzden liste dar tutuldu.
EKSIK_GUN_KODLARI = {
    "01": ("İstirahat", "dahil"),
    "12": ("Birden fazla neden", "belirsiz"),
    "13": ("Diğer nedenler", "belirsiz"),
    "21": ("Diğer ücretsiz izin", "dusulur"),
    "24": ("Ücretsiz doğum izni", "dusulur"),
    "25": ("Ücretsiz yol izni", "dusulur"),
}

ETKI_ACIKLAMA = {
    "dahil": "kıdem süresine dahil",
    "dusulur": "kıdem süresinden düşülür",
    "belirsiz": "tek başına ücretsiz izni kanıtlamaz — izin ve rapor kayıtları gerekli",
}


# --------------------------------------------------------------------------
# tarih / süre
# --------------------------------------------------------------------------

def _tarih(d) -> date:
    if isinstance(d, date):
        return d
    s = str(d).strip()
    for kalip in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, kalip).date()
        except ValueError:
            continue
    raise ValueError(f"tarih okunamadı: {d!r}")


def hizmet_gunu(giris, cikis) -> int:
    """Takvim günü farkı. Yargıtay uygulaması fiilî takvim süresini esas alır;
    360 günlük ticari yıl kullanılmaz."""
    g, c = _tarih(giris), _tarih(cikis)
    if c <= g:
        return 0
    return (c - g).days


def sure_metni(gun: int, giris=None) -> str:
    """Takvim ayları eşit değil; giriş tarihi verilirse süre gerçek takvimden
    çıkarılır (365/30 yaklaşıklığı birkaç gün kaydırıyor)."""
    if giris is not None:
        g = _tarih(giris)
        bitis = date.fromordinal(g.toordinal() + gun)
        yil = bitis.year - g.year
        ay = bitis.month - g.month
        kalan_gun = bitis.day - g.day
        if kalan_gun < 0:
            ay -= 1
            onceki_ay = (bitis.month - 1) or 12
            onceki_yil = bitis.year if bitis.month > 1 else bitis.year - 1
            import calendar
            kalan_gun += calendar.monthrange(onceki_yil, onceki_ay)[1]
        if ay < 0:
            yil -= 1
            ay += 12
        return f"{yil} yıl {ay} ay {kalan_gun} gün"
    yil, kalan = divmod(gun, 365)
    ay, kalan_gun = divmod(kalan, 30)
    return f"{yil} yıl {ay} ay {kalan_gun} gün"


# --------------------------------------------------------------------------
# kıdem tavanı
# --------------------------------------------------------------------------

def tavan_tablosu(dosya: str | None = None) -> list[dict]:
    try:
        with open(dosya or _TAVAN_DOSYA, encoding="utf-8") as f:
            return json.load(f).get("donemler", [])
    except Exception:
        return []


def tavan_bul(fesih, dosya: str | None = None) -> dict:
    """Fesih tarihindeki tavanı arar.

    Döner: {"deger": float|None, "kullanilabilir": bool, "oneri": float|None,
            "not": str}. Doğrulanmamış satır ASLA "deger" olarak dönmez."""
    f = _tarih(fesih)
    for d in tavan_tablosu(dosya):
        if _tarih(d["baslangic"]) <= f <= _tarih(d["bitis"]):
            if d.get("dogrulandi"):
                return {"deger": float(d["tavan"]), "kullanilabilir": True,
                        "oneri": None,
                        "not": f"Tavan tablodan: {d['tavan']} TL ({d.get('kaynak') or 'kaynak yazılmamış'})."}
            return {"deger": None, "kullanilabilir": False,
                    "oneri": float(d["tavan"]),
                    "not": (f"Tabloda {d['tavan']} TL yazıyor ama doğrulanmamış. "
                            "Hesapta kullanılmadı — yürürlükteki tavanı girin.")}
    return {"deger": None, "kullanilabilir": False, "oneri": None,
            "not": "Fesih tarihi tavan tablosunda yok — tavanı elle girin."}


# --------------------------------------------------------------------------
# hesaplar
# --------------------------------------------------------------------------

@dataclass
class KidemSonuc:
    gun: int
    dusulen_gun: int
    kidem_gun: int
    sure: str
    esas_ucret: float
    tavan_uygulandi: bool
    brut: float
    damga: float
    net: float


def kidem_hesapla(giris, cikis, giydirilmis_aylik: float,
                  tavan: float | None = None, dusulen_gun: int = 0) -> KidemSonuc:
    """1475 s. Kanun m.14 — her tam hizmet yılı için 30 günlük giydirilmiş brüt
    ücret, artan süre oranlı. Tavan varsa aylık ücret yerine tavan esas alınır."""
    gun = hizmet_gunu(giris, cikis)
    kidem_gun = max(gun - max(dusulen_gun, 0), 0)
    esas = giydirilmis_aylik
    tavanli = False
    if tavan and tavan > 0 and giydirilmis_aylik > tavan:
        esas, tavanli = tavan, True
    brut = esas * kidem_gun / 365
    damga = brut * DAMGA_ORANI
    return KidemSonuc(
        gun=gun, dusulen_gun=max(dusulen_gun, 0), kidem_gun=kidem_gun,
        sure=sure_metni(kidem_gun, giris), esas_ucret=round(esas, 2),
        tavan_uygulandi=tavanli, brut=round(brut, 2), damga=round(damga, 2),
        net=round(brut - damga, 2),
    )


def ihbar_hafta(gun: int) -> int:
    """4857 s. Kanun m.17 bildirim süreleri."""
    if gun < 183:
        return 2
    if gun < 548:
        return 4
    if gun < 1095:
        return 6
    return 8


def ihbar_hesapla(giris, cikis, giydirilmis_aylik: float,
                  fesheden: str = "isveren") -> dict:
    """İhbar tazminatı. Feshi işçi yaptıysa — haklı fesih olsa bile — ihbar
    tazminatına hak kazanılmaz; bu durumda 0 döner ve gerekçe yazılır."""
    gun = hizmet_gunu(giris, cikis)
    hafta = ihbar_hafta(gun)
    if fesheden == "isci":
        return {"hak_var": False, "hafta": hafta, "brut": 0.0, "net": 0.0,
                "gerekce": ("Feshi işçi yaptığı için, fesih haklı bulunsa bile "
                            "ihbar tazminatına hak kazanılmaz.")}
    brut = (giydirilmis_aylik / 30) * hafta * 7
    # İhbar tazminatı gelir vergisine tabidir; oran dilime bağlı, burada
    # hesaplanmaz — brüt verilir, net için bordro gerekir.
    return {"hak_var": True, "hafta": hafta, "brut": round(brut, 2),
            "net": None,
            "gerekce": ("Net tutar gelir vergisi dilimine bağlı; bordro olmadan "
                        "hesaplanmadı.")}


def yillik_izin_hak_gun(gun: int) -> int:
    """4857 m.53 — 1-5 yıl 14, 5-15 yıl 20, 15 yıl ve üzeri 26 gün."""
    yil = gun / 365
    if yil < 1:
        return 0
    if yil <= 5:
        return 14
    if yil < 15:
        return 20
    return 26


# --------------------------------------------------------------------------
# hizmet dökümü satırları
# --------------------------------------------------------------------------

@dataclass
class DokumSatiri:
    donem: str = ""          # "2026-07" ya da belgedeki haliyle
    isyeri: str = ""
    prim_gun: int = 0
    kazanc: float = 0.0
    eksik_gun: int = 0
    eksik_kod: str = ""
    uyari: str = ""


def _metinde_var(deger: str, metin: str) -> bool:
    """Sayı belgede gerçekten geçiyor mu? Modelin uydurduğu rakamı yakalamanın
    en ucuz yolu: tutarın ham metinde birebir bulunması."""
    if not deger:
        return True
    d = deger.strip()
    return d in metin or d.replace(".", "").replace(",", ".") in metin


def satirlari_dogrula(satirlar: list[dict], ham_metin: str) -> list[DokumSatiri]:
    """LLM'in çıkardığı satırları biçim ve belgede-geçme yönünden denetler."""
    metin = re.sub(r"[ \t]+", " ", ham_metin or "")
    cikti: list[DokumSatiri] = []
    for s in satirlar or []:
        uyarilar = []
        try:
            prim = int(float(s.get("prim_gun") or 0))
        except (TypeError, ValueError):
            prim, _ = 0, uyarilar.append("prim günü okunamadı")
        if not 0 <= prim <= 31:
            uyarilar.append(f"prim günü aralık dışı: {prim}")
            prim = max(0, min(prim, 31))
        try:
            kazanc = float(str(s.get("kazanc") or 0).replace(".", "").replace(",", "."))
        except ValueError:
            kazanc, _ = 0.0, uyarilar.append("kazanç okunamadı")
        if kazanc < 0:
            uyarilar.append("kazanç negatif")
            kazanc = 0.0
        ham_kazanc = str(s.get("kazanc") or "").strip()
        if ham_kazanc and not _metinde_var(ham_kazanc, metin):
            uyarilar.append("bu kazanç belgede birebir bulunamadı — teyit edin")
        kod = re.sub(r"\D", "", str(s.get("eksik_kod") or ""))[:2]
        cikti.append(DokumSatiri(
            donem=str(s.get("donem") or "").strip(),
            isyeri=str(s.get("isyeri") or "").strip(),
            prim_gun=prim, kazanc=round(kazanc, 2),
            eksik_gun=max(int(float(s.get("eksik_gun") or 0)), 0),
            eksik_kod=kod, uyari="; ".join(uyarilar),
        ))
    return cikti


def eksik_gun_ozeti(satirlar: list[DokumSatiri]) -> dict:
    """Kıdemden düşülmesi gereken / tartışmalı günleri ayırır."""
    kesin = belirsiz = 0
    kalemler = []
    for s in satirlar:
        if s.eksik_gun <= 0:
            continue
        ad, etki = EKSIK_GUN_KODLARI.get(s.eksik_kod, ("Bilinmeyen kod", "belirsiz"))
        if etki == "dusulur":
            kesin += s.eksik_gun
        elif etki == "belirsiz":
            belirsiz += s.eksik_gun
        kalemler.append({"donem": s.donem, "gun": s.eksik_gun,
                         "kod": s.eksik_kod, "ad": ad, "etki": etki,
                         "aciklama": ETKI_ACIKLAMA[etki]})
    return {"kesin_dusulecek": kesin, "tartismali": belirsiz,
            "kalemler": kalemler}


def senaryolar(giris, cikis, giydirilmis_aylik: float, tavan: float | None,
               ozet: dict) -> list[dict]:
    """Ücretsiz izin belirsizliği tutarı değiştirir; tek rakam vermek yerine
    alt/üst sınır verilir — avukat hangisinin savunulabilir olduğunu bilir."""
    kesin, tartismali = ozet["kesin_dusulecek"], ozet["tartismali"]
    adaylar = [("Hiç süre düşülmeden", 0)]
    if kesin:
        adaylar.append((f"Kesin ücretsiz izin ({kesin} gün) düşülürse", kesin))
    if tartismali:
        adaylar.append((f"Tartışmalı günler de ({kesin + tartismali} gün) düşülürse",
                        kesin + tartismali))
    cikti = []
    for ad, dusum in adaylar:
        s = kidem_hesapla(giris, cikis, giydirilmis_aylik, tavan, dusum)
        cikti.append({"varsayim": ad, **asdict(s)})
    return cikti
