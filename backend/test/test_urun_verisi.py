# test_urun_verisi.py — Finansman/katılım ürün verisi katmanının birim testleri.
#
# Bu testler MongoDB'ye BAĞLANMAZ: normalize edilmiş kayıtlar elle kurulur.
# Amaç, ekran görüntülerinde yakalanan iki hatanın bir daha dönmemesi:
#   1) Mevduat (katılım hesabı) sorusunun kredi taksit hesabına düşmesi,
#   2) Kullanıcının cümlesindeki oranın aylık kredi oranı sanılıp
#      100.000 TL'yi bir ayda 125.990 TL'ye çıkarması.
# Ayrıca sayı ayrıştırma ve filtre davranışı kilitleniyor.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chatbot.urun_verisi import (  # noqa: E402
    _sayi, kayitlari_daralt, finansman_baglami, katilim_baglami,
)
from chatbot.intent import niyet_bul  # noqa: E402


# --------------------------------------------------------------------------
# Sayı ayrıştırma — Türkçe binlik/ondalık ayracı
# --------------------------------------------------------------------------

def test_sayi_turkce_bicim():
    assert _sayi("32.648,38") == 32648.38      # binlik nokta + ondalık virgül
    assert _sayi("1.000.000") == 1000000.0     # saf binlik ayracı
    assert _sayi("2,89") == 2.89
    assert _sayi("125990") == 125990.0
    assert _sayi("%25,99") == 25.99            # yüzde işareti temizlenir
    assert _sayi(None) == 0.0
    assert _sayi("") == 0.0
    assert _sayi("yok") == 0.0


# --------------------------------------------------------------------------
# Niyet yönlendirmesi — ekran görüntülerindeki iki soru
# --------------------------------------------------------------------------

KATILIM_SORUSU = (
    "Vakıf Katılım'ın 100.000 TL tutarındaki 32 gün / 1 Ay vadeli katılım hesabı "
    "kâr payı getirisini (%25.99 net kâr oranı, 2,207.01 TL net getiri) diğer "
    "katılım bankalarıyla ve sektör ortalamasıyla karşılaştırarak analiz et."
)
FINANSMAN_SORUSU = (
    "Dünya Katılım'ın 1.000.000 TL tutarındaki 84 ay vadeli konut finansmanını "
    "(%2,89 kâr oranı, aylık 32.648,38 TL taksit) diğer katılım bankalarının aynı "
    "koşuldaki teklifleriyle karşılaştırarak değerlendir."
)


def test_mevduat_sorusu_krediye_dusmez():
    """Regresyon: bu soru 'hesaplama' niyetine düşüp 'Aylık Taksit 125.990 TL'
    üretiyordu. Mevduatta taksit/geri ödeme diye bir şey yoktur."""
    n = niyet_bul(KATILIM_SORUSU)
    assert n.tur == "katilim", f"beklenen 'katilim', gelen {n.tur!r}"
    assert n.banka_kodu == "vakif_katilim"
    assert n.kiyas_genis is True, "sektör kıyası istendi; banka filtresi kapanmalı"


def test_konut_finansmani_veriye_yonlenir():
    """Regresyon: bu soruya 'elimdeki veritabanı sadece kredi kartı taksit
    kampanyalarını içermektedir' cevabı veriliyordu."""
    n = niyet_bul(FINANSMAN_SORUSU)
    assert n.tur == "finansman", f"beklenen 'finansman', gelen {n.tur!r}"
    assert n.banka_kodu == "dunya_katilim"
    assert n.vade == 84
    assert n.kiyas_genis is True


def test_hesaplama_niyeti_kaldirildi():
    """Artık hiçbir soru taksit hesaplayıcısına gitmiyor; hesap yerine veri."""
    n = niyet_bul("50000 tl 24 ay 3.5 oranla hesapla")
    assert n.tur == "finansman"


def test_kampanya_sorulari_etkilenmedi():
    """Ürün desenleri kampanya akışını çalmamalı — 'katılım bankası' ifadesi
    tek başına mevduat sorusu DEĞİLDİR."""
    for soru in ("katılım bankalarının kampanyalarını listele",
                 "Albaraka Türk kampanyaları neler",
                 "12 taksit fırsatı olan kampanyalar"):
        n = niyet_bul(soru)
        assert n.tur not in ("finansman", "katilim"), f"{soru!r} -> {n.tur}"


# --------------------------------------------------------------------------
# Bağlam üreticileri
# --------------------------------------------------------------------------

FINANSMAN_KAYITLARI = [
    {"banka": "Dünya Katılım", "banka_kodu": "dunya_katilim", "urun": "Konut Finansmanı",
     "tutar": 1000000.0, "vade": 84.0, "oran": 2.89, "aylik_taksit": 32648.38,
     "toplam_geri_odeme": 2742464.0, "tahsis_ucreti": 5000.0, "url": ""},
    {"banka": "Kuveyt Türk", "banka_kodu": "kuveyt_turk", "urun": "Konut Finansmanı",
     "tutar": 1000000.0, "vade": 84.0, "oran": 2.45, "aylik_taksit": 30120.0,
     "toplam_geri_odeme": 2530080.0, "tahsis_ucreti": 0.0, "url": ""},
    {"banka": "Ziraat Katılım", "banka_kodu": "ziraat_katilim", "urun": "Taşıt Finansmanı",
     "tutar": 500000.0, "vade": 36.0, "oran": 3.39, "aylik_taksit": 21500.0,
     "toplam_geri_odeme": 774000.0, "tahsis_ucreti": 1250.0, "url": ""},
]

KATILIM_KAYITLARI = [
    {"banka": "Vakıf Katılım", "banka_kodu": "vakif_katilim", "tutar": 100000.0,
     "vade": "32 Gün", "brut_oran": 28.10, "net_oran": 25.99,
     "brut_kar": 2386.0, "net_kar": 2207.01, "toplam": 102207.01, "url": ""},
    {"banka": "Albaraka Türk", "banka_kodu": "albaraka", "tutar": 100000.0,
     "vade": "32 Gün", "brut_oran": 30.00, "net_oran": 27.75,
     "brut_kar": 2547.9, "net_kar": 2356.8, "toplam": 102356.8, "url": ""},
]


def test_finansman_baglami_hesaplama_yapmaz():
    """Taksit ve toplam, kayıttaki değerin AYNISI olmalı — türetilmemeli."""
    chart, ctx = finansman_baglami(FINANSMAN_KAYITLARI)
    assert chart is not None
    # En düşük oran başa gelir (kıyasın doğal sıralaması).
    assert chart["labels"][0] == "Kuveyt Türk"
    # Değer sütunu = kayıttaki aylık taksit, birebir.
    assert 30120.0 in chart["values"]
    assert 32648.38 in chart["values"]
    # 100.000 x (1+oran) türü bir "hesap" izine rastlanmamalı.
    assert "32.648,38" in ctx
    assert chart["stats"]["min"] == 2.45
    assert chart["stats"]["max"] == 3.39


def test_katilim_baglami_mevduat_dili_kullanir():
    """Bağlam, modele bunun mevduat olduğunu açıkça söylemeli; aksi hâlde
    model yine 'geri ödeme' diline kayıyor."""
    chart, ctx = katilim_baglami(KATILIM_KAYITLARI)
    assert chart is not None
    assert "MEVDUAT" in ctx
    assert "taksit" not in ctx.lower(), "mevduat bağlamında taksit dili olmamalı"
    # En yüksek net getiri başa gelir.
    assert chart["labels"][0] == "Albaraka Türk"
    assert chart["values"][0] == 2356.8
    # Net getiri kayıttaki değerin aynısı.
    assert 2207.01 in chart["values"]


def test_bos_kayit_cokmez():
    assert finansman_baglami([]) == (None, "")
    assert katilim_baglami([]) == (None, "")


# --------------------------------------------------------------------------
# Filtreleme
# --------------------------------------------------------------------------

def test_urun_tipi_filtresi():
    konut = kayitlari_daralt(FINANSMAN_KAYITLARI, [], "konut finansmanı oranları")
    assert {k["urun"] for k in konut} == {"Konut Finansmanı"}

    tasit = kayitlari_daralt(FINANSMAN_KAYITLARI, [], "taşıt finansmanı")
    assert {k["urun"] for k in tasit} == {"Taşıt Finansmanı"}


def test_filtre_bos_birakmaz():
    """Hiç eşleşme yoksa filtre UYGULANMAZ — kullanıcıya boş tablo yerine
    daha geniş bir kesit göstermek doğru."""
    sonuc = kayitlari_daralt(FINANSMAN_KAYITLARI, ["olmayan_banka"], "konut")
    assert len(sonuc) > 0


def test_kiyasta_tutar_vade_tek_banka_birakmaz():
    """Regresyon: 1.000.000 TL / 84 ay kombinasyonu yalnızca Dünya Katılım'da
    var. Kıyas istendiğinde bu filtre uygulanırsa tabloda tek satır kalıyor ve
    model 'karşılaştırma yapılamamaktadır' diyordu."""
    dar = kayitlari_daralt(FINANSMAN_KAYITLARI, [], "konut finansmanı",
                           tutar=1000000.0, vade=84, kiyas=True)
    assert len({k["banka"] for k in dar}) >= 2, "kıyas için en az iki banka kalmalı"

    # Kıyas İSTENMEDİĞİNDE filtre normal çalışmaya devam eder.
    dar2 = kayitlari_daralt(FINANSMAN_KAYITLARI, [], "konut finansmanı",
                            tutar=1000000.0, vade=84, kiyas=False)
    assert len(dar2) == 2  # iki bankanın da 1M/84 ay konut kaydı var


def test_vade_metninde_ikinci_sayi_de_eslesir():
    """Regresyon: Vakıf Katılım vadesi '32 gün / 1 Ay'. Yalnızca ilk sayıya
    (32) bakmak, 1 aylık sorguda kullanıcının sorduğu bankayı siliyordu."""
    dar = kayitlari_daralt(KATILIM_KAYITLARI + [
        {"banka": "Vakıf Katılım", "banka_kodu": "vakif_katilim", "tutar": 100000.0,
         "vade": "32 gün / 1 Ay", "brut_oran": 31.5, "net_oran": 25.99,
         "brut_kar": 2386.0, "net_kar": 2207.01, "toplam": 102207.01, "url": ""},
    ], [], "katılım hesabı", tutar=100000.0, vade=1, urun_filtresi=False)
    assert any("32 gün" in str(k["vade"]) for k in dar), "çok sayılı vade eşleşmeli"


def test_tekrarli_kayitlar_tekillestirilir():
    """`katilim_hesap` koleksiyonunda her kayıt üç kez duruyor (kazıyıcı upsert
    yerine insert yapıyor); tabloda aynı satır üç kez görünmemeli."""
    ucer = KATILIM_KAYITLARI * 3
    dar = kayitlari_daralt(ucer, [], "katılım hesabı", urun_filtresi=False)
    assert len(dar) == len(KATILIM_KAYITLARI)


def test_banka_filtresi_calisir():
    sonuc = kayitlari_daralt(FINANSMAN_KAYITLARI, ["kuveyt_turk"], "konut finansmanı")
    assert [k["banka"] for k in sonuc] == ["Kuveyt Türk"]


if __name__ == "__main__":
    import traceback
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    basarisiz = 0
    for t in testler:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except Exception:
            basarisiz += 1
            print(f"  HATA {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(testler) - basarisiz}/{len(testler)} gecti")
    sys.exit(1 if basarisiz else 0)
