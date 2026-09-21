"""İşçilik hesabı birim testleri — Qdrant/LLM gerektirmez."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import iscilik as i


# Saha vakası: 16.11.2020 giriş, 01.09.2026 fesih, tavan 73.729,87.
GIRIS, CIKIS, TAVAN = "2020-11-16", "2026-09-01", 73729.87


def test_hizmet_suresi_takvimden():
    assert i.hizmet_gunu(GIRIS, CIKIS) == 2115
    assert i.sure_metni(2115, GIRIS) == "5 yıl 9 ay 16 gün"


def test_kidem_tavan_uygulanir():
    s = i.kidem_hesapla(GIRIS, CIKIS, 94195.38, TAVAN)
    assert s.tavan_uygulandi
    assert round(s.brut) == 427229
    assert round(s.net) == 423987


def test_ucretsiz_izin_dusumu_tutari_dusurur():
    s = i.kidem_hesapla(GIRIS, CIKIS, 94195.38, TAVAN, dusulen_gun=105)
    assert s.kidem_gun == 2010
    assert round(s.brut) == 406019


def test_tavan_altinda_ucret_tavansiz_hesaplanir():
    s = i.kidem_hesapla("2023-01-01", "2024-01-01", 30000, TAVAN)
    assert not s.tavan_uygulandi and s.esas_ucret == 30000


def test_isci_feshinde_ihbar_yok():
    r = i.ihbar_hesapla(GIRIS, CIKIS, 94195.38, "isci")
    assert r["hak_var"] is False and r["brut"] == 0.0


def test_isveren_feshinde_8_hafta():
    r = i.ihbar_hesapla(GIRIS, CIKIS, 30000, "isveren")
    assert r["hafta"] == 8 and round(r["brut"]) == round(30000 / 30 * 56)


def test_dogrulanmamis_tavan_hesaba_girmez():
    t = i.tavan_bul("2025-03-01")
    assert t["kullanilabilir"] is False and t["deger"] is None
    assert t["oneri"] is not None


def test_tablo_disi_tarihte_tavan_yok():
    t = i.tavan_bul("2019-01-01")
    assert t["deger"] is None and t["oneri"] is None


def test_belgede_olmayan_kazanc_isaretlenir():
    ham = "2026/07 ... 94.195,38 ..."
    s = i.satirlari_dogrula(
        [{"donem": "2026-07", "prim_gun": 30, "kazanc": "94.195,38"},
         {"donem": "2026-06", "prim_gun": 30, "kazanc": "12.345,67"}], ham)
    assert s[0].uyari == ""
    assert "birebir bulunamadı" in s[1].uyari


def test_prim_gunu_araligi_zorlanir():
    s = i.satirlari_dogrula([{"donem": "2026-07", "prim_gun": 45}], "")
    assert s[0].prim_gun == 31 and "aralık dışı" in s[0].uyari


def test_eksik_gun_kesin_ve_tartismali_ayrilir():
    satirlar = i.satirlari_dogrula([
        {"donem": "2023-07", "prim_gun": 17, "eksik_gun": 13, "eksik_kod": "21"},
        {"donem": "2025-04", "prim_gun": 28, "eksik_gun": 2, "eksik_kod": "12"},
        {"donem": "2024-11", "prim_gun": 20, "eksik_gun": 10, "eksik_kod": "01"},
    ], "")
    o = i.eksik_gun_ozeti(satirlar)
    assert o["kesin_dusulecek"] == 13 and o["tartismali"] == 2
    assert len(o["kalemler"]) == 3


def test_senaryolar_alt_ust_sinir_verir():
    satirlar = i.satirlari_dogrula([
        {"donem": "2023-07", "eksik_gun": 13, "eksik_kod": "21"},
        {"donem": "2025-02", "eksik_gun": 92, "eksik_kod": "12"},
    ], "")
    sen = i.senaryolar(GIRIS, CIKIS, 94195.38, TAVAN, i.eksik_gun_ozeti(satirlar))
    assert len(sen) == 3
    assert sen[0]["brut"] > sen[1]["brut"] > sen[2]["brut"]
    assert round(sen[2]["net"]) == 402938


def test_yillik_izin_kademeleri():
    assert i.yillik_izin_hak_gun(400) == 14
    assert i.yillik_izin_hak_gun(2115) == 20
    assert i.yillik_izin_hak_gun(365 * 16) == 26


def test_son_kazanc_en_son_donemden_secilir():
    """Ölçülen hata: model dökümün SON SATIRINI son kazanç sanıyordu."""
    satirlar = i.satirlari_dogrula([
        {"donem": "2026-07", "kazanc": "94.195,38"},
        {"donem": "2023-07", "kazanc": "12.300,00"},
    ], "")
    s = i.son_kazanc_sec(satirlar)
    assert s is not None and s.donem == "2026-07" and s.kazanc == 94195.38


def test_donemi_okunamayan_satir_ucret_secimine_girmez():
    satirlar = i.satirlari_dogrula([{"donem": "", "kazanc": "99.999,00"}], "")
    assert i.son_kazanc_sec(satirlar) is None
