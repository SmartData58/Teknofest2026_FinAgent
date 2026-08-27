# urun_verisi.py — Finansman ürünleri ve katılım hesaplarını chatbot bağlamına taşır.
#
# NEDEN VAR:
# generate_response.py yalnızca kampanya koleksiyonlarını okuyordu. Bu yüzden
# "Dünya Katılım'ın 1.000.000 TL / 84 ay vadeli konut finansmanını diğer katılım
# bankalarıyla karşılaştır" sorusuna chatbot "elimdeki veritabanı sadece kredi
# kartı taksit kampanyalarını içermektedir" cevabını veriyordu — oysa veri
# `finansman_urun` koleksiyonunda duruyordu. Aynı boşluk katılım hesapları
# (`katilim_hesap`) için de vardı.
#
# HESAPLAMA YAPILMIYOR — BİLİNÇLİ KARAR:
# Aylık taksit ve toplam geri ödeme, bankaların kendi sayfalarından kazınmış
# GERÇEK değerler olarak DB'de duruyor (`aylik_taksit_tutari`,
# `geri_odenecek_toplam_tutar`). Bunların üzerine annüite formülü uygulamak
# gerçek veriyi tahminle değiştirmek olurdu. Eski `gercek_finansman_hesapla`
# yolu tam da bu yüzden yanlış sonuç üretiyordu: kullanıcının cümlesindeki
# %25,99'u (bir mevduatın YILLIK net getirisi) AYLIK kredi oranı sanıp
# 100.000 TL için 125.990 TL "aylık taksit" yazmıştı.

import os
import re
from typing import Optional

from loguru import logger

from chatbot.intent import banka_adi_getir

# pymongo BİLEREK modül seviyesinde içe aktarılmıyor: bu modüldeki biçimlendirme
# ve filtreleme fonksiyonları veritabanı sürücüsüne ihtiyaç duymuyor ve onlar
# sürücü kurulu olmayan bir ortamda da (birim testleri) çalışabilmeli.


def _mongo_uri() -> str:
    return (os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
            or "mongodb://mongo:27017")


# Veritabanı adı: API katmanı da aynı veritabanını kullanıyor (api/campaing.py).
_DB_ADI = os.getenv("MONGO_DB", "smartdata")

_FINANSMAN_KOL = "finansman_urun"
_KATILIM_KOL = "katilim_hesap"


def _kod_eslemesi() -> dict:
    """API katmanındaki banka kodu eşlemesini ödünç alır.

    `finansman_urun` bankayı KOD olarak yazıyor ('vakif', 'ziraat') ama kanonik
    kodlar 'vakif_katilim' / 'ziraat_katilim'. `katilim_hesap` ise GÖRÜNEN AD
    yazıyor ('Vakıf Katılım'). Eşlemeyi burada tekrar tanımlamak iki ayrı
    doğruluk kaynağı yaratırdı; içe aktarım başarısız olursa boş sözlükle
    devam ediliyor (o hâlde banka_adi_getir'in kendi çözümü kullanılır).
    """
    try:
        from api.campaing import BANK_CODE_MAP
        return BANK_CODE_MAP
    except Exception:
        return {}


def _banka_adi(ham) -> str:
    """Ham banka değerini (kod ya da görünen ad) kullanıcıya gösterilecek ada çevirir."""
    metin = str(ham or "").strip()
    if not metin:
        return "Bilinmeyen Banka"
    kod = _kod_eslemesi().get(metin.lower(), metin)
    # banka_kodu VE ham_ad birlikte veriliyor: yalnız ham_ad ile çağrıldığında
    # 'dunya_katilim' gibi alt çizgili kodlar çözülemiyordu.
    return banka_adi_getir(banka_kodu=kod, ham_ad=metin)


def _sayi(ham) -> float:
    """Türkçe biçimli sayıyı float'a çevirir ('1.234,56' -> 1234.56).

    api/campaing.py::_parse_num ile aynı davranış: binlik noktası ile ondalık
    noktası ayırt edilir, aksi hâlde '32.648,38' 32,64 olarak okunurdu.
    """
    if ham is None:
        return 0.0
    if isinstance(ham, (int, float)):
        return float(ham)
    metin = str(ham).strip()
    if not metin:
        return 0.0
    metin = re.sub(r"[^\d.,\-]", "", metin)
    if not metin:
        return 0.0
    # Saf binlik ayracı: 1.000 / 1.234.567
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", metin):
        metin = metin.replace(".", "")
    elif "," in metin:
        metin = metin.replace(".", "").replace(",", ".")
    try:
        return float(metin)
    except ValueError:
        return 0.0


def _kayitlari_oku(koleksiyon: str, limit: int = 500) -> list:
    """Tek bir koleksiyonu okur. Bağlantı hatasında boş liste döner (chatbot
    akışı bu yüzden çökmemeli — veri yoksa model 'veri yok' der)."""
    try:
        # Paylaşılan havuz: her çağrıda yeni MongoClient açmak, istek başına
        # bağlantı kurulumu + sunucu keşfi maliyeti bindiriyordu.
        from chatbot.mongo_baglanti import veritabani
        db = veritabani(_mongo_uri(), _DB_ADI, zaman_asimi_ms=4000)
    except Exception as e:
        logger.warning(f"Mongo bağlantısı kurulamadı ({koleksiyon}): {e}")
        return []
    try:
        return list(db[koleksiyon].find({}).limit(limit))
    except Exception as e:
        logger.warning(f"'{_DB_ADI}.{koleksiyon}' okunamadı: {e}")
        return []


# -----------------------------------------------------------------------------
# FİNANSMAN ÜRÜNLERİ
# -----------------------------------------------------------------------------

def finansman_kayitlari() -> list:
    """`finansman_urun` kayıtlarını normalize edilmiş sözlükler olarak döner."""
    ham_kayitlar = _kayitlari_oku(_FINANSMAN_KOL)
    kayitlar = []
    for d in ham_kayitlar:
        banka_ham = d.get("banka", "")
        # 🚨 Oran iki farklı adla tutuluyor: `kar_orani` (kazıyıcıların çoğu) ya
        # da `kar_orani_aylik` (ziraat/albaraka/dünya taşıt + bazı konut
        # kayıtları). Yalnızca ilkini okumak, taşıt ve konut finansmanlarında
        # oranı 0 gösteriyordu (aynı hata API katmanında da vardı).
        oran = _sayi(d.get("kar_orani"))
        if oran <= 0:
            oran = _sayi(d.get("kar_orani_aylik"))
        kayitlar.append({
            "banka": _banka_adi(banka_ham),
            "banka_kodu": banka_ham,
            "urun": (d.get("urun") or "").strip() or "Finansman",
            "tutar": _sayi(d.get("finansman_tutari")),
            "vade": _sayi(d.get("vade")),
            "oran": oran,
            "aylik_taksit": _sayi(d.get("aylik_taksit_tutari")),
            "toplam_geri_odeme": _sayi(d.get("geri_odenecek_toplam_tutar")),
            "tahsis_ucreti": _sayi(d.get("tahsis_ucreti")),
            "url": d.get("url") or d.get("kaynak_url") or "",
        })
    return kayitlar


# -----------------------------------------------------------------------------
# KATILIM HESAPLARI
# -----------------------------------------------------------------------------

def katilim_kayitlari() -> list:
    """`katilim_hesap` kayıtlarını normalize edilmiş sözlükler olarak döner."""
    ham_kayitlar = _kayitlari_oku(_KATILIM_KOL)
    kayitlar = []
    for d in ham_kayitlar:
        banka_ham = d.get("banka", "")
        brut_kar = _sayi(d.get("brut_kar") or d.get("brut_getiri"))
        net_kar = _sayi(d.get("net_kar") or d.get("net_getiri"))
        tutar = _sayi(d.get("yatirilan_tutar"))
        toplam = _sayi(d.get("toplam"))
        if toplam <= 0 and tutar > 0:
            toplam = tutar + net_kar
        kayitlar.append({
            "banka": _banka_adi(banka_ham),
            "banka_kodu": banka_ham,
            "tutar": tutar,
            "vade": (d.get("vade") or "").strip() or "-",
            "brut_oran": _sayi(d.get("brut_oran")),
            "net_oran": _sayi(d.get("net_oran")),
            "brut_kar": brut_kar,
            "net_kar": net_kar,
            "toplam": toplam,
            "url": d.get("url") or d.get("kaynak_url") or "",
        })
    return kayitlar


# -----------------------------------------------------------------------------
# FİLTRELEME
# -----------------------------------------------------------------------------

def _urun_esles(urun_metni: str, soru: str) -> bool:
    """Soruda konut/taşıt/ihtiyaç geçiyorsa yalnızca o ürün tipini tut."""
    s = (soru or "").lower()
    u = (urun_metni or "").lower()
    istenen = []
    if re.search(r"konut|mortgage|ev\s+kredi|housing", s):
        istenen.append("konut")
    if re.search(r"ta[şs][ıi]t|ara[çc]|otomobil|vehicle|car\s+loan", s):
        istenen.append("taşıt")
    if re.search(r"iht[ıi]ya[çc]|personal|tüketici|tuketici", s):
        istenen.append("ihtiyaç")
    if not istenen:
        return True
    for kelime in istenen:
        # 'taşıt' kaydı 'tasit' diye de yazılmış olabilir.
        sade = kelime.replace("ş", "s").replace("ı", "i").replace("ç", "c")
        if kelime in u or sade in u.replace("ş", "s").replace("ı", "i").replace("ç", "c"):
            return True
    return False


def kayitlari_daralt(kayitlar: list, bankalar: list, soru: str,
                     tutar: Optional[float] = None,
                     vade: Optional[float] = None,
                     urun_filtresi: bool = True,
                     kiyas: bool = False) -> list:
    """Bankaya / ürün tipine / tutara / vadeye göre daraltır.

    Bir filtre HİÇ kayıt bırakmıyorsa uygulanmaz: kullanıcıya boş tablo
    göstermektense daha geniş bir kesit göstermek doğru. (Kıyas sorularında
    tutar/vade genelde tek bankanın teklifini tarif eder; onu tüm bankalara
    dayatmak diğer bankaları listeden siler — kullanıcı tam da onları istiyordu.)
    """
    sonuc = list(kayitlar)

    if bankalar:
        kodlar = {str(b).lower() for b in bankalar}
        suzulen = [k for k in sonuc
                   if str(k.get("banka_kodu", "")).lower() in kodlar
                   or any(kod in str(k.get("banka", "")).lower() for kod in kodlar)]
        # Tek banka soruldu ama kıyas isteniyorsa (aşağıdaki çağıran karar verir)
        # yine de boş bırakmıyoruz.
        if suzulen:
            sonuc = suzulen

    if urun_filtresi:
        suzulen = [k for k in sonuc if _urun_esles(k.get("urun", ""), soru)]
        if suzulen:
            sonuc = suzulen

    # 🛠️ KIYAS İSTENDİĞİNDE TUTAR/VADE FİLTRESİ TEK BANKA BIRAKAMAZ.
    #
    # "Dünya Katılım'ın 1.000.000 TL / 84 ay konut finansmanını DİĞER katılım
    # bankalarının aynı koşuldaki teklifleriyle karşılaştır" sorusunda bu tam
    # kombinasyon yalnızca Dünya Katılım'da var. Filtre uygulanınca tabloda tek
    # satır kalıyor ve model "karşılaştırma teknik olarak yapılamamaktadır"
    # diyordu — kullanıcının istediğinin tam tersi. Kıyas modunda bu iki filtre
    # ancak GERİYE EN AZ İKİ BANKA bırakıyorsa uygulanır.
    _kiyas_oncesi = list(sonuc)

    if tutar and tutar > 0:
        suzulen = [k for k in sonuc if abs(_sayi(k.get("tutar")) - tutar) < 1]
        if suzulen:
            sonuc = suzulen

    if vade and vade > 0:
        def _vade_esles(k):
            v = k.get("vade")
            if isinstance(v, str):
                # 🛠️ Vade metni serbest biçimli ve BİRDEN ÇOK sayı taşıyabiliyor:
                # Vakıf Katılım kayıtlarında "32 gün / 1 Ay" yazıyor. Yalnızca
                # İLK sayıya bakmak (32) 1 aylık sorguyla eşleşmiyor ve
                # kullanıcının sorduğu bankayı tablodan siliyordu — soru
                # Vakıf Katılım hakkındayken tabloda yalnızca Ziraat kalmıştı.
                return any(abs(int(s) - vade) < 1 for s in re.findall(r"\d+", v))
            return abs(_sayi(v) - vade) < 1
        suzulen = [k for k in sonuc if _vade_esles(k)]
        if suzulen:
            sonuc = suzulen

    if kiyas and len({k.get("banka") for k in sonuc}) < 2:
        sonuc = _kiyas_oncesi

    return _tekillestir(sonuc)


def _tekillestir(kayitlar: list) -> list:
    """Aynı kaydın tekrarlarını atar.

    `katilim_hesap` koleksiyonunda her kayıt ÜÇ kez duruyor (kazıyıcı upsert
    yerine insert yapıyor): 12 kaydın yalnızca 4'ü benzersiz. Tekrarlar tabloda
    aynı satırı üç kez gösteriyor ve ortalama/istatistikleri de bozmuyor ama
    kullanıcıya yanlış bir "kayıt sayısı" izlenimi veriyor. Asıl çözüm boru
    hattında; burada görüntüyü savunmacı biçimde temizliyoruz.
    """
    gorulen, benzersiz = set(), []
    for k in kayitlar:
        anahtar = (k.get("banka"), k.get("urun"), k.get("tutar"),
                   str(k.get("vade")), k.get("oran"), k.get("net_oran"),
                   k.get("net_kar"), k.get("aylik_taksit"))
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        benzersiz.append(k)
    return benzersiz


# -----------------------------------------------------------------------------
# LLM BAĞLAMI + TABLO YÜKÜ
# -----------------------------------------------------------------------------

def _tl(deger: float) -> str:
    return f"{deger:,.2f} TL".replace(",", "@").replace(".", ",").replace("@", ".")


def finansman_baglami(kayitlar: list, dil: str = "tr") -> tuple:
    """(chart_data, db_context) üretir. Değer sütunu = aylık taksit."""
    kayitlar = [k for k in kayitlar if k.get("tutar", 0) > 0 or k.get("aylik_taksit", 0) > 0]
    # En düşük kâr oranı önce: kıyas sorularının doğal sıralaması.
    kayitlar.sort(key=lambda k: (k["oran"] <= 0, k["oran"]))

    satirlar, etiketler, alt_etiketler, degerler, kategoriler, urller = [], [], [], [], [], []
    for k in kayitlar:
        vade_metni = f"{int(k['vade'])} ay" if k["vade"] else "-"
        oran_metni = f"%{k['oran']:.2f}".replace(".", ",") if k["oran"] > 0 else "belirtilmemiş"
        detay = (f"{k['urun']} — {_tl(k['tutar'])} / {vade_metni} / kâr oranı {oran_metni}")
        etiketler.append(k["banka"])
        alt_etiketler.append(detay)
        degerler.append(round(k["aylik_taksit"], 2))
        kategoriler.append(k["urun"])
        urller.append(k["url"])
        satirlar.append(
            f"- {k['banka']} | {k['urun']} | Tutar: {_tl(k['tutar'])} | Vade: {vade_metni} "
            f"| Kâr oranı: {oran_metni} | Aylık taksit: {_tl(k['aylik_taksit'])} "
            f"| Toplam geri ödeme: {_tl(k['toplam_geri_odeme'])}"
            + (f" | Tahsis ücreti: {_tl(k['tahsis_ucreti'])}" if k["tahsis_ucreti"] > 0 else "")
        )

    if not satirlar:
        return None, ""

    oranli = [k["oran"] for k in kayitlar if k["oran"] > 0]
    chart_data = {
        "type": "tablo",
        "title": "Finansman Ürünleri" if dil != "en" else "Financing Products",
        "subtitle": (f"{len(kayitlar)} finansman kaydı — bankaların yayımladığı "
                     f"gerçek taksit ve toplam geri ödeme tutarları"
                     if dil != "en" else
                     f"{len(kayitlar)} financing records — real installment figures"),
        "prefix": "", "suffix": " TL",
        "labels": etiketler, "sub_labels": alt_etiketler, "values": degerler,
        "source_indices": list(range(len(satirlar))),
        "full_texts": satirlar, "categories": kategoriler, "urls": urller,
        "stats": ({"avg": round(sum(oranli) / len(oranli), 2),
                   "min": min(oranli), "max": max(oranli)} if oranli else None),
        "stats_birim": "%",
        "stats_karisik": False,
        "stats_kapsam": len(oranli),
        "deger_sutunu": True,
    }
    db_context = (
        "FİNANSMAN ÜRÜNLERİ (finansman_urun koleksiyonu — bankaların yayımladığı "
        "gerçek değerler; taksit/toplam tutarlar HESAPLANMADI, olduğu gibi alındı):\n"
        + "\n".join(satirlar)
    )
    return chart_data, db_context


def katilim_baglami(kayitlar: list, dil: str = "tr") -> tuple:
    """(chart_data, db_context) üretir. Değer sütunu = net getiri (TL)."""
    kayitlar = [k for k in kayitlar if k.get("tutar", 0) > 0]
    # En yüksek net getiri önce: mevduatta kullanıcının aradığı yön bu.
    kayitlar.sort(key=lambda k: k["net_kar"], reverse=True)

    satirlar, etiketler, alt_etiketler, degerler, kategoriler, urller = [], [], [], [], [], []
    for k in kayitlar:
        net_oran_metni = f"%{k['net_oran']:.2f}".replace(".", ",") if k["net_oran"] > 0 else "belirtilmemiş"
        brut_oran_metni = f"%{k['brut_oran']:.2f}".replace(".", ",") if k["brut_oran"] > 0 else "-"
        detay = (f"{_tl(k['tutar'])} / {k['vade']} — net kâr oranı {net_oran_metni}")
        etiketler.append(k["banka"])
        alt_etiketler.append(detay)
        degerler.append(round(k["net_kar"], 2))
        kategoriler.append(k["vade"])
        urller.append(k["url"])
        satirlar.append(
            f"- {k['banka']} | Yatırılan: {_tl(k['tutar'])} | Vade: {k['vade']} "
            f"| Brüt oran: {brut_oran_metni} | Net oran: {net_oran_metni} "
            f"| Brüt getiri: {_tl(k['brut_kar'])} | Net getiri: {_tl(k['net_kar'])} "
            f"| Vade sonu toplam: {_tl(k['toplam'])}"
        )

    if not satirlar:
        return None, ""

    oranli = [k["net_oran"] for k in kayitlar if k["net_oran"] > 0]
    chart_data = {
        "type": "tablo",
        "title": "Katılım Hesapları" if dil != "en" else "Participation Accounts",
        "subtitle": (f"{len(kayitlar)} katılım hesabı kaydı — bankaların yayımladığı "
                     f"gerçek getiri tutarları"
                     if dil != "en" else
                     f"{len(kayitlar)} participation account records"),
        "prefix": "", "suffix": " TL",
        "labels": etiketler, "sub_labels": alt_etiketler, "values": degerler,
        "source_indices": list(range(len(satirlar))),
        "full_texts": satirlar, "categories": kategoriler, "urls": urller,
        "stats": ({"avg": round(sum(oranli) / len(oranli), 2),
                   "min": min(oranli), "max": max(oranli)} if oranli else None),
        "stats_birim": "%",
        "stats_karisik": False,
        "stats_kapsam": len(oranli),
        "deger_sutunu": True,
    }
    db_context = (
        "KATILIM HESAPLARI (katilim_hesap koleksiyonu — bankaların yayımladığı "
        "gerçek getiri değerleri; HESAPLANMADI, olduğu gibi alındı).\n"
        "DİKKAT: Bunlar MEVDUAT ürünüdür — müşteri para YATIRIR ve kâr payı "
        "KAZANIR. Kredi/finansman gibi 'geri ödeme' söz konusu değildir:\n"
        + "\n".join(satirlar)
    )
    return chart_data, db_context
