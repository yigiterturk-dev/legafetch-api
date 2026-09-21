"""/api/iscilik-hesabi uç testi. LLM yerine sabit çıkarım konur: ölçülen şey
modelin ne kadar iyi okuduğu değil, boru hattının doğru hesaplayıp doğru
çekinceyi yazması. Qdrant yüklendiği için yavaş."""
import json
import os
import sys

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

import main  # noqa: E402

API_KEY = os.environ.get("X_API_KEY", "")
if not API_KEY:
    pytest.skip("X_API_KEY .env dosyasinda tanimli olmali", allow_module_level=True)
KEY = {"X-API-Key": API_KEY}

DOKUM = (
    "SİGORTALI HİZMET DÖKÜMÜ\nİşyeri: MEDICANA SAĞLIK HİZMETLERİ A.Ş.\n"
    "İşe Giriş: 16.11.2020\n"
    "2026/07 30 94.195,38 0\n"
    "2023/07 17 12.300,00 13 21 - Diğer ücretsiz izin\n"
)
IHTAR = "İş akdi müvekkil tarafından 01.09.2026 tarihinde haklı nedenle feshedilmiştir."

CIKARIM = {
    "ise_giris": "2020-11-16", "isten_cikis": "2026-09-01",
    "fesih_tarihi": "2026-09-01", "fesheden": "isci",
    "fesih_gerekcesi": "Kreş açılmaması — 4857 m.24",
    "isyeri": "MEDICANA SAĞLIK HİZMETLERİ A.Ş.",
    "son_kazanc": "94.195,38", "son_kazanc_donemi": "2026-07",
    "satirlar": [
        {"donem": "2026-07", "prim_gun": 30, "kazanc": "94.195,38",
         "eksik_gun": 0, "eksik_kod": ""},
        {"donem": "2023-07", "prim_gun": 17, "kazanc": "12.300,00",
         "eksik_gun": 13, "eksik_kod": "21"},
    ],
    "notlar": [],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "llm_cagir",
                        lambda *a, **k: json.dumps(CIKARIM, ensure_ascii=False))
    with TestClient(main.app) as c:
        yield c


def _gonder(client, **veri):
    return client.post(
        "/api/iscilik-hesabi",
        files=[("files", ("dokum.txt", DOKUM.encode(), "text/plain")),
               ("files", ("ihtar.txt", IHTAR.encode(), "text/plain"))],
        data=veri, headers=KEY)


def test_tavanli_hesap_ve_senaryolar(client):
    r = _gonder(client, tavan="73729.87")
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["tespit"]["hizmet_gunu"] == 2115
    assert g["tespit"]["hizmet_suresi"] == "5 yıl 9 ay 16 gün"
    assert round(g["senaryolar"][0]["net"]) == 423987
    # 21 kodlu 13 gün kesin düşülür -> ikinci senaryo
    assert g["eksik_gun"]["kesin_dusulecek"] == 13
    assert round(g["senaryolar"][1]["net"]) == 421381


def test_isci_feshinde_ihbar_sifir(client):
    g = _gonder(client, tavan="73729.87").json()
    assert g["ihbar"]["hak_var"] is False and g["ihbar"]["brut"] == 0.0


def test_sgk_kazanci_kullanilinca_cekince_yazilir(client):
    g = _gonder(client, tavan="73729.87").json()
    assert any("SGK kazancı giydirilmiş ücretle aynı şey değildir" in c
               for c in g["cekinceler"])


def test_ucret_en_son_donemden_secilir_son_satirdan_degil(client):
    """Canlı ölçümde çıkan hata: döküm tarih sırasında değilse model son
    satırı ücret sanıyordu (423.987 yerine 70.732 TL)."""
    g = _gonder(client, tavan="73729.87").json()
    assert g["tespit"]["esas_alinan_ucret"] == 94195.38
    assert round(g["senaryolar"][0]["net"]) == 423987


def test_tavansiz_istekte_yuksek_cikma_uyarisi(client):
    g = _gonder(client).json()
    assert any("OLDUĞUNDAN YÜKSEK" in c for c in g["cekinceler"])


def test_tarih_okunamazsa_hesap_yapilmaz(client, monkeypatch):
    eksik = {**CIKARIM, "ise_giris": None, "isten_cikis": None,
             "fesih_tarihi": None}
    monkeypatch.setattr(main, "llm_cagir",
                        lambda *a, **k: json.dumps(eksik, ensure_ascii=False))
    r = _gonder(client, tavan="73729.87")
    assert r.status_code == 422


def test_okunamayan_belge_reddedilir(client):
    r = client.post("/api/iscilik-hesabi",
                    files=[("files", ("bos.txt", b"", "text/plain"))],
                    headers=KEY)
    assert r.status_code == 422
