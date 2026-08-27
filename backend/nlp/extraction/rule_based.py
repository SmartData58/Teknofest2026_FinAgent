"""
Katılım Bankacılığı Kampanya Bilgi Çıkarımı
-------------------------------------------
Regex tabanlı yüksek kesinlikli alan çıkarımı.

Tasarım:
    HAM METİN
       ↓
    Regex çıkarıcılar
       ↓
    Normalize edilmiş AlanBulgusu
       ↓
    Hybrid katmanında eksik/düşük güvenli alanlar için LLM

Not:
- Regex yalnızca yüksek kesinlikli sinyaller için kullanılır.
- Aynı alanda birden fazla aday varsa ilk aday yerine güven skoru
  ve bağlam dikkate alınır.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Any, List, Set


# 🛠️ ÇİFT YOL: bu modül iki farklı kökten çalıştırılıyor — pipeline.py depo
# kökünden `backend.*` diye, backend konteyneri ise WORKDIR /app (yani
# backend/) içinden `nlp.*` diye import ediyor. Tek biçim kullanmak diğerinde
# ModuleNotFoundError veriyordu; bu yüzden geçici bir symlink gerekiyordu.
# agents.py'deki yerleşik kalıp buraya da uygulandı.
try:
    from backend.nlp.normalizasyon.money import para_normalize
    from backend.nlp.normalizasyon.date import tarih_normalize
    from backend.nlp.normalizasyon.duration import vade_normalize
    from backend.nlp.normalizasyon.percentage import yuzde_normalize
    from backend.nlp.classification.campaign_classifier import siniflandir
except ModuleNotFoundError:
    from nlp.normalizasyon.money import para_normalize
    from nlp.normalizasyon.date import tarih_normalize
    from nlp.normalizasyon.duration import vade_normalize
    from nlp.normalizasyon.percentage import yuzde_normalize
    from nlp.classification.campaign_classifier import siniflandir


# =============================================================================
# VERİ MODELİ
# =============================================================================

@dataclass
class AlanBulgusu:
    deger: Any
    ham_metin: str
    kural: str
    yontem: str = "regex"
    guven: float = 1.0
    kanit_metni: str = ""
    baslangic_konum: Optional[int] = None
    bitis_konum: Optional[int] = None
    birim: str = "metin"


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================


# =============================================================================
# 🚨 TÜRKÇE "İ" KÜÇÜLTME TUZAĞI
#
# Python'da "İ".lower() tek harf DEĞİL, İKİ kod noktası üretir:
#     "İ".lower() == "i̇"   (i + BİRLEŞEN NOKTA)
# Bu yüzden `.lower()` ile küçültülmüş bir metinde "İndirim" -> "i̇ndirim"
# olur ve `indirim` araması EŞLEŞMEZ. Desenler re.IGNORECASE ile ham metinde
# doğru çalışıyor; ama bu dosyadaki bağlam kontrolleri ÖNCEDEN küçültülmüş
# pencerelerde (`_pencere`, `_tutar_cumle`) arama yapıyor ve orada sessizce
# başarısız oluyordu.
#
# Ölçülen sonuç: "Etkinlik Biletlerinde 250 TL İndirim" kaydında ödül tutarı
# BOŞ kalıyordu — çünkü `_ODUL_IPUCLARI` küçültülmüş cümlede "indirim"
# arıyor, cümlede ise "i̇ndirim" yazıyordu. Aynı tuzak İ ile başlayan her
# anahtar kelimeyi (İade, İşlem, İhtiyaç...) etkiliyor.
#
# Çözüm: küçültmeyi TÜRKÇEYE UYGUN yap ve artık birleşen noktayı temizle.
# =============================================================================
_BIRLESEN_NOKTA = "̇"


def _kucult(metin: str) -> str:
    """Türkçe farkındalıklı küçültme: İ -> i, I -> ı, birleşen nokta atılır."""
    if not metin:
        return ""
    return (metin.replace("İ", "i").replace("I", "ı")
            .lower().replace(_BIRLESEN_NOKTA, ""))


def _pencere(
    metin: str,
    baslangic: int,
    bitis: int,
    genislik: int = 80,
) -> str:
    return _kucult(metin[
        max(0, baslangic - genislik): min(len(metin), bitis + genislik)
    ])


def _bulgu(
    metin: str,
    eslesme: re.Match,
    deger: Any,
    kural: str,
    *,
    guven: float = 1.0,
    birim: str = "metin",
    kanit_genislik: int = 80,
) -> AlanBulgusu:
    return AlanBulgusu(
        deger=deger,
        ham_metin=eslesme.group(),
        kural=kural,
        guven=guven,
        kanit_metni=_pencere(
            metin,
            eslesme.start(),
            eslesme.end(),
            kanit_genislik,
        ).strip(),
        baslangic_konum=eslesme.start(),
        bitis_konum=eslesme.end(),
        birim=birim,
    )


def _ilk_yuksek_guvenli(
    mevcut: Optional[AlanBulgusu],
    aday: AlanBulgusu,
) -> AlanBulgusu:
    if mevcut is None or aday.guven > mevcut.guven:
        return aday
    return mevcut


# =============================================================================
# 1. ORANLAR
# =============================================================================

_YUZDE = re.compile(
    r"(?:%|yüzde)\s*\d+(?:[.,]\d+)?"
    r"|\d+(?:[.,]\d+)?\s*%",
    re.IGNORECASE,
)

_INDIRIM_IPUCLARI = (
    "indirim",
    "iskonto",
    "indirimli",
)

_CASHBACK_IPUCLARI = (
    "cashback",
    "nakit iade",
    "nakit iade oranı",
    "iade oranı",
    "nakit ödül",
    "nakit odul",
    "harcama",
)

# "%0 Vade Farkı ile 6 taksit" gibi ifadelerde ±70 karakterlik pencerede
# "harcama" geçtiği için yukarıdaki gevşek ipucu tetikleniyor ve vade farkı
# oranı `nakit_iade_yuzde` olarak kaydediliyordu (3 kayıt, hepsi %0).
_CASHBACK_NEGATIF = (
    "vade farkı",
    "vade farki",
    "komisyon",
    "faiz",
)

_KARPAYI_ACIK = (
    "kâr payı",
    "kar payı",
    "kâr paylaşım",
    "kar paylaşım",
    "kâr paylaşım oranı",
    "kar paylaşım oranı",
)

_KARPAYI_NEGATIF = (
    "iade",
    "ödül",
    "odul",
    "kazan",
    "mil",
    "puan",
    "bonus",
    "çekiliş",
    "komisyon",
    "cashback",
    "indirim",
    "iskonto",
)

_GETIRI_IPUCLARI = (
    "getiri oranı",
    "getiri",
    "kâr oranı",
    "kar oranı",
    "paylaşım oranı",
    "paylasim orani",
)

_TAHSIS_IPUCLARI = (
    "tahsis",
    "tahsis ücreti",
    "masraf oranı",
    "komisyon oranı",
    "binde",
)

# =============================================================================
# KÂR PAYI TANIMA — AÇIK BAĞLAM
#
# 🚨 ÖLÇÜM (27.08.2026): gerçekçi 10 kâr payı ifadesinin YALNIZCA 5'i
# yakalanıyordu. Sebepleri:
#   1) `_KARPAYI_ACIK` düz metin listesiydi; Türkçe ek alınca eşleşmiyordu
#      ("kâr paylı", "kâr payıyla" -> "kâr payı" alt dizesi yok).
#   2) Dal sırası `elif` zinciriydi ve GEVŞEK ipuçları (tahsis / indirim /
#      cashback) AÇIK kâr payı bağlamından ÖNCE geliyordu. `_CASHBACK_IPUCLARI`
#      içindeki yalın "harcama" yüzünden "Harcamalarınızı %2,99 kâr payı
#      oranıyla taksitlendirin" cümlesi NAKİT İADE sayılıyordu.
#   3) "kâr oranı" `_GETIRI_IPUCLARI` üzerinden `tahsis_ucreti` alanına
#      yazılıyordu — kâr oranı bir ÜCRET DEĞİLDİR; bu hem kaçırma hem de
#      yanlış alana yazma hatasıydı.
# Artık açık kâr payı bağlamı EN ÖNCE ve ek toleranslı biçimde sınanıyor.
# =============================================================================
_KARPAYI_ACIK_DESEN = re.compile(
    r"k[âa]r\s*pay\w*"          # kâr payı, kâr paylı, kâr payıyla, kar payi
    r"|k[âa]r\s*payla[şs]\w*"   # kâr paylaşım(ı)
    r"|k[âa]r\s*oran\w*",       # kâr oranı  (ÜCRET DEĞİL, getiri)
    re.IGNORECASE,
)

# Katılma hesabının PAYLAŞIM oranı (%80-98) finansman kâr payıyla aynı alana
# yazılamaz; llm_extractor'da da aynı ayrım var. Buradaki ikinci savunma hattı.
_KATILMA_HESABI_DESEN = re.compile(
    r"kat[ıi]lma\s+hesab|pay(?:la[şs][ıi]m|da[şs][ıi]m)\s+oran"
    r"|k[âa]r\s+pay[ıi]\s+da[ğg][ıi]t",
    re.IGNORECASE,
)
_FINANSMAN_BAGLAM_DESEN = re.compile(
    r"finansman|kredi|taksitl|vade\s*fark|tahsis\s+[üu]cret", re.IGNORECASE
)

# Finansman kâr payı oranının makul üst sınırı; üstü paylaşım oranıdır.
_KARPAYI_UST_SINIR = 50.0


def _kar_payi_kabul_edilir_mi(deger: float, pencere: str) -> bool:
    """Bu yüzde, FİNANSMAN kâr payı oranı olarak yazılabilir mi?"""
    if not (0.0 <= deger <= _KARPAYI_UST_SINIR):
        return False
    if (_KATILMA_HESABI_DESEN.search(pencere)
            and not _FINANSMAN_BAGLAM_DESEN.search(pencere)):
        return False
    return True


def oranlari_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """
    Yüzde ifadelerini bağlamına göre:
        - indirim_orani_yuzde
        - nakit_iade_yuzde
        - kar_payi_orani
    alanlarına dağıtır.
    """
    bulgular: Dict[str, AlanBulgusu] = {}

    for eslesme in _YUZDE.finditer(metin):
        deger = yuzde_normalize(eslesme.group())
        if deger is None:
            continue

        pencere = _pencere(
            metin, eslesme.start(), eslesme.end(), genislik=70
        )

        # 0) AÇIK KÂR PAYI BAĞLAMI — en özgül sinyal, en önce sınanır.
        #
        # ⚠️ DAR PENCERE ŞART. ±70 karakterde bakıldığında bir sonraki
        # BÖLÜM BAŞLIĞI da pencereye giriyordu: "…komisyon fiyatlarımızdan
        # %25 indirimli olarak kiralık kasa kullanabileceklerdir. Yüksek Kâr
        # Paylaşım Oranı:" cümlesinde %25 bir İNDİRİMDİR, ama 62 karakter
        # ötedeki başlık yüzünden kâr payı oranı (%25) olarak kaydediliyordu.
        # Kâr payı ifadesi Türkçede yüzdeye bitişik yazılır; ±35 yeterli.
        dar_pencere = _pencere(metin, eslesme.start(), eslesme.end(), genislik=35)
        if _KARPAYI_ACIK_DESEN.search(dar_pencere):
            # ⚠️ KABUL DAR, RED GENİŞ PENCEREDE.
            # Reddetme sinyali ("katılma hesabı", "paylaşım oranı") dar
            # pencerenin kenarına denk gelip yarıda kesilebiliyor; o zaman
            # tetikleyici eşleşiyor ama koruma çalışmıyordu. Kabul kararı
            # yakınlık ister, red kararı ise kaçırılmamalıdır.
            if _kar_payi_kabul_edilir_mi(float(deger), pencere):
                aday = _bulgu(
                    metin,
                    eslesme,
                    float(deger),
                    "yuzde+kar_payi_acik_baglami",
                    guven=0.99,
                    birim="percent",
                )
                bulgular["kar_payi_orani"] = _ilk_yuksek_guvenli(
                    bulgular.get("kar_payi_orani"), aday
                )
            continue

        if any(k in pencere for k in _TAHSIS_IPUCLARI):
            aday = _bulgu(
                metin,
                eslesme,
                float(deger),
                "yuzde+tahsis_baglami",
                guven=0.99,
                birim="percent",
            )
            bulgular["tahsis_ucreti_orani"] = _ilk_yuksek_guvenli(
                bulgular.get("tahsis_ucreti_orani"), aday
            )

        elif any(k in pencere for k in _INDIRIM_IPUCLARI):
            aday = _bulgu(
                metin,
                eslesme,
                float(deger),
                "yuzde+indirim_baglami",
                guven=0.98,
                birim="percent",
            )
            bulgular["indirim_orani_yuzde"] = _ilk_yuksek_guvenli(
                bulgular.get("indirim_orani_yuzde"), aday
            )

        elif any(k in pencere for k in _CASHBACK_IPUCLARI):
            # "%0 nakit iade" diye bir kampanya özelliği yoktur; sıfır değer
            # ya da vade farkı/komisyon bağlamı, yanlış okumanın işaretidir.
            if float(deger) == 0.0 or any(k in pencere for k in _CASHBACK_NEGATIF):
                continue
            aday = _bulgu(
                metin,
                eslesme,
                float(deger),
                "yuzde+cashback_baglami",
                guven=0.99,
                birim="percent",
            )
            # Eğer mevcut bir nakit_iade_yuzde varsa, yüksek olan sayısal değeri korur
            mevcut = bulgular.get("nakit_iade_yuzde")
            if mevcut is None or aday.deger > mevcut.deger:
                bulgular["nakit_iade_yuzde"] = aday

        elif any(k in pencere for k in _GETIRI_IPUCLARI):
            # "oran" kelimesini tek başına sinyal olarak kullanmıyoruz.
            #
            # 🚨 ESKİDEN BU DAL `tahsis_ucreti` ALANINA YAZIYORDU.
            # "Taşıt finansmanında %2,79 kâr oranı" gibi bir cümlede getiri
            # oranı, TAHSİS ÜCRETİ olarak kaydediliyordu — kâr oranı bir ücret
            # değildir. Banka kıyas tablosunda bu, hem kâr payı sütununu boş
            # bırakıyor hem masraf sütununu uyduruyordu. Artık doğru alana,
            # kâr payı için geçerli olan aynı güvenlik kontrolleriyle yazılıyor
            # (paylaşım oranı ayrımı + üst sınır).
            if (not any(n in pencere for n in _KARPAYI_NEGATIF)
                    and _kar_payi_kabul_edilir_mi(float(deger), pencere)):
                aday = _bulgu(
                    metin,
                    eslesme,
                    float(deger),
                    "yuzde+getiri_baglami",
                    guven=0.88,
                    birim="percent",
                )
                bulgular["kar_payi_orani"] = _ilk_yuksek_guvenli(
                    bulgular.get("kar_payi_orani"), aday
                )

    # -------------------------------------------------------------------
    # SON ÇARE: ÖDEME PLANI TABLOSU
    # -------------------------------------------------------------------
    # Bazı bankalar (ör. Türkiye Finans) oranı düz cümlede değil TABLO
    # hâlinde veriyor:
    #     "Vade | Kâr Payı Oranı | Tahsis Ücreti | Aylık Toplam Maliyet
    #      3  4,20%  0,50%  5,77% ...
    #      12 4,15%  0,50%  5,50% ..."
    # Sütun başlığı sayılardan uzakta kaldığı için yukarıdaki dar pencereli
    # kontrol hiçbirini yakalamıyordu; iki büyük ihtiyaç finansmanı kampanyası
    # kâr payı oranı BOŞ kalıyordu. Başlıktan sonraki İLK makul yüzde, en kısa
    # vadenin oranıdır ve kampanyanın ilan edilen oranıdır.
    if "kar_payi_orani" not in bulgular:
        baslik_es = re.search(r"k[âa]r\s*pay[ıi]\s*oran[ıi]", metin, re.IGNORECASE)
        if baslik_es:
            kuyruk = metin[baslik_es.end(): baslik_es.end() + 200]
            for satir_es in _YUZDE.finditer(kuyruk):
                v = yuzde_normalize(satir_es.group())
                if v is None:
                    continue
                if _kar_payi_kabul_edilir_mi(float(v), kuyruk[:120]):
                    bulgular["kar_payi_orani"] = _bulgu(
                        metin,
                        satir_es,
                        float(v),
                        "yuzde+odeme_plani_tablosu",
                        guven=0.90,
                        birim="percent",
                    )
                break

    return bulgular


# =============================================================================
# 2. VADE VE TAKSİT
# =============================================================================

# Kapanış `\b` yerine `\w*`: Türkçede taksit hemen her zaman ek alıyor
# ("4 taksite kadar", "9 taksitle", "6 taksitli") ve `taksit\b` bunların
# HİÇBİRİNİ tutmuyordu.
# ⚠️ Serbest `\w*` fazla açık kaldı: "31.12.2026 Taksitlio'nun" metninde
# "2026 Taksitlio" eşleşip taksit sayısı 2026 çıkıyordu. İki koruma eklendi:
#   • sayı en fazla 3 hane (100'ün üzerinde taksit yok),
#   • serbest devam yerine gerçek Türkçe ekleri sayan kapalı bir liste.
_TAKSIT = re.compile(
    r"\b(\d{1,3})\s*(?:ay|aya|ayın)?\s*(?:varan|kadar)?\s*"
    r"taksit(?:i|e|te|le|li|lik|ler|lere|leri|lerde|iniz|inizi)?\b",
    re.IGNORECASE,
)

_VADE_ADAYI = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:ay|yıl|yil|sene)[a-zçğıöşü]*",
    re.IGNORECASE,
)

_VADE_BAGLAMI = re.compile(
    r"(?:vade|vadeli|vadeye|vadesi|kadar|varan)",
    re.IGNORECASE,
)

# Ödemesiz/ertelemeli dönem ifadeleri — vade ile aynı cümlede geçer ama
# vadenin kendisi değildir (bkz. vade_ve_taksit_cikar içindeki kullanım).
_VADE_DISLAMA = re.compile(
    r"ödemesiz|odemesiz|ertele\w*|ertelemeli|geri\s*ödemesiz",
    re.IGNORECASE,
)


def vade_ve_taksit_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}

    # --- TAKSİT ÇIKARIMI ---
    for taksit_bul in _TAKSIT.finditer(metin):
        deger = int(taksit_bul.group(1))
        
        aday = _bulgu(
            metin,
            taksit_bul,
            deger,
            "sayi+taksit_kalibi",
            guven=0.99,
            birim="adet",
        )
        
        bulgular["taksit"] = _ilk_yuksek_guvenli(
            bulgular.get("taksit"), aday
        )

    # --- VADE ÇIKARIMI ---
    for vade_bul in _VADE_ADAYI.finditer(metin):
        ifade = vade_bul.group()
        
        # Eğer bu ifade zaten bir taksit kalıbının içindeyse (Örn: "3 aya varan taksit")
        # bunu finansman vadesi (vade_ay) olarak tekrar işlemeyelim.
        if "taksit" in metin[vade_bul.start(): min(len(metin), vade_bul.end() + 15)].lower():
            continue

        sonrasi = _kucult(metin[
            vade_bul.end(): min(len(metin), vade_bul.end() + 35)
        ])

        oncesi = _kucult(metin[
            max(0, vade_bul.start() - 35): vade_bul.start()
        ])

        baglam = f"{oncesi} {sonrasi}"

        vade_mi = bool(_VADE_BAGLAMI.search(baglam))

        if not vade_mi:
            continue

        # 🚫 ÖDEMESİZ DÖNEM VADE DEĞİLDİR.
        # "6 aya kadar ödemesiz dönem ve 60 aya varan vade imkânı" cümlesinde
        # vade 60 aydır; 6 ay yalnızca ödemenin ertelendiği süredir. Kural ilk
        # "ay" ifadesini alıp vade_ay=6 yazıyordu. Aynı hata "1-6 ay vade
        # (3 ay ertelemeli)" kaydında da vade_ay=3 üretmişti.
        #
        # Ayırt edici işaret SIRADIR: erteleme kelimesi sayıdan sonra ve
        # "vade" kelimesinden ÖNCE geliyorsa, o sayı ertelemeye aittir.
        #   "6 ay|a kadar ÖDEMESİZ dönem ... vade"  -> erteleme (ele)
        #   "60 ay|a varan VADE"                    -> vade      (al)
        #   "6 ay| VADE (3 ay ertelemeli)"          -> vade      (al)
        #   "3 ay| ERTELEMELİ)"                     -> erteleme (ele)
        # Karşılaştırma `_VADE_BAGLAMI` ile YAPILAMAZ: o desen "kadar"/"varan"
        # gibi genel kelimeleri de içeriyor ve "6 aya KADAR ödemesiz" ifadesinde
        # "kadar" ertelemeden önce geldiği için sayı vade sanılıyordu. Sıra
        # kıyaslaması yalnızca gerçek "vade" kelimesine bakmalı.
        _ertele = _VADE_DISLAMA.search(sonrasi)
        if _ertele:
            _vade_kel = re.search(r"vade\w*", sonrasi, re.IGNORECASE)
            if _vade_kel is None or _ertele.start() < _vade_kel.start():
                continue

        deger = vade_normalize(ifade)
        if deger is None:
            continue

        aday = _bulgu(
            metin,
            vade_bul,
            int(deger),
            "sayi+birim+vade_baglami",
            guven=0.97,
            birim="ay",
        )

        bulgular["vade_ay"] = _ilk_yuksek_guvenli(
            bulgular.get("vade_ay"), aday
        )

    return bulgular


# =============================================================================
# 3. PARA TUTARLARI
# =============================================================================

_TUTAR = re.compile(
    r"(?<![\d.,])"
    r"(?:\d{1,3}(?:[.]\d{3})+|\d+)"
    r"(?:,\d+)?"
    r"\s*(?:bin|milyon)?"
    r"\s*(?:TL|₺|Türk\s+Liras[ıi])"
    r"(?:'?[a-zçğıöşü]+)?",
    re.IGNORECASE,
)

# Bir finansman/kredi tutarının makul alt sınırı. Bunun altındaki TL değerleri
# kampanya metninde ödül, eşik ya da ücret olarak geçer — finansman olarak değil.
_ASGARI_FINANSMAN_TUTARI = 1000.0

_MIN_IPUCLARI = re.compile(
    r"\b(?:en\s+az|minimum|min\.?|asgari|en\s+düşük)\b",
    re.IGNORECASE,
)

_MAX_IPUCLARI = re.compile(
    r"\b(?:en\s+fazla|maksimum|max\.?|azami|kadar|üst sınır)\b",
    re.IGNORECASE,
)

# Ek toleransı şart: "alışverişlerinizde" / "harcamalarınızda" gibi çekimli
# hâller `\balışveriş\b` ile tutmuyordu; bu yüzden 3.4'teki harcama eşiği dalı
# hiç çalışmıyor, tutarlar 3.5'e düşüp `finansman_tutari` oluyordu.
_HARCAMA_IPUCLARI = re.compile(
    r"\b(?:harcama\w*|alışveriş\w*|al[ıi]sveris\w*)",
    re.IGNORECASE,
)

_FINANSMAN_IPUCLARI = re.compile(
    r"\b(?:finansman|finansmanı|finansmanınız|"
    r"finanse|konut finansmanı|taşıt finansmanı|ihtiyaç finansmanı)\b",
    re.IGNORECASE,
)

_KREDI_IPUCLARI = re.compile(
    r"\b(?:kredi(?!\s*kart)|kredi tutarı|kredi miktarı)\b",
    re.IGNORECASE,
)

_LIMIT_IPUCLARI = re.compile(
    r"\b(?:limit|limiti|limitiniz)\b",
    re.IGNORECASE,
)

_ODUL_IPUCLARI = re.compile(
    # `indirim` EKLENDİ: "toplamda 3.000 TL'ye varan indirim",
    # "Etkinlik Biletlerinde 250 TL İndirim" gibi TL cinsinden indirimler
    # hiçbir ödül dalına düşmüyordu — oysa bunlar da parasal kazanımdır ve
    # ödül kıyaslamasında yer almalıdır. (Yüzdesel indirim ayrı alanda:
    # oranlari_cikar -> indirim_orani_yuzde.)
    r"\b(?:hediye|ödül|odul|çek|çekiniz|iade|bonus|fırsat|firsat|indirim\w*"
    # Kart programlarının ödül para birimleri. Bunlar listede yoktu, bu yüzden
    # "Giyim ve Kozmetik Alışverişlerinize 1.300 TL ParafPara" başlığındaki
    # ilan edilen tutar hiçbir dala düşmüyor, ödül olarak gövdedeki kademe
    # tablosundan 800 TL yazılıyordu.
    r"|parafpara|paraf\s*para|worldpuan|chip\s*para|chippara|maxipuan"
    r")\b",
    re.IGNORECASE,
)

_PUAN_IPUCLARI = re.compile(
    r"\b(?:puan|worldpuan|chip[- ]?para|chippara|maxipuan|"
    r"parafpuan|bonus\s*puan|mil)\b",
    re.IGNORECASE,
)

_MASRAF_IPUCLARI = re.compile(
    r"\b(?:masraf|ücret|ucret|tahsis|dosya)\b",
    re.IGNORECASE,
)

_ESIK_SONRASI = re.compile(
    r"^\s*(?:ve\s+)?"
    r"(?:üzeri|üzerinde|üstü|üstünde|yukarısı|fazlası|"
    r"altı|altında|aşağısı|kadar\s+olan|arasında|aras[ıi]|"
    r"-\s*\d|harca(?!ma\s+iade))",
    re.IGNORECASE,
)

# "toplamda 2.000 TL Worldpuan" — kampanya metinleri neredeyse her zaman
# hem BİRİM BAŞINA ödülü ("her talimat için 500 TL") hem TOPLAMI yazıyor.
# İlan edilen ve kullanıcının gördüğü değer TOPLAMDIR; birim başına tutar
# onu eziyordu (6 kayıtta ölçüldü).
_TOPLAM_ONCESI = re.compile(r"toplam(?:da|[ıi])?\s*$", re.IGNORECASE)

_ESIK_ONCESI = re.compile(
    r"(?:en\s+az|minimum|min\.?|asgari)\s*$",
    re.IGNORECASE,
)


def _tutar_cumle(metin: str, baslangic: int, bitis: int) -> str:
    """
    Tutarın bulunduğu cümleyi yaklaşık olarak çıkarır.
    Cümle bağlamı, ±50 karakter penceresinden daha güvenlidir.
    """
    sol = max(
        metin.rfind(".", 0, baslangic),
        metin.rfind("!", 0, baslangic),
        metin.rfind("?", 0, baslangic),
        metin.rfind("\n", 0, baslangic),
    )
    saglar = [
        p for p in (
            metin.find(".", bitis),
            metin.find("!", bitis),
            metin.find("?", bitis),
            metin.find("\n", bitis),
        )
        if p != -1
    ]
    sag = min(saglar) if saglar else len(metin)

    return _kucult(metin[sol + 1:sag].strip())


def tutar_cikar(metin: str, baslik: str = "") -> Dict[str, AlanBulgusu]:
    """TL tutarlarını semantik bağlamlarına göre ayırır.

    `baslik` verilirse, metnin başındaki başlık bölgesinde geçen ödül
    tutarına daha yüksek güven verilir (bkz. 3.6). Çağıran taraf
    `metin` olarak "başlık. gövde" birleşimini geçirdiği için başlık
    bölgesi metnin ilk `len(baslik)` karakteridir.
    """
    bulgular: Dict[str, AlanBulgusu] = {}
    baslik_sonu = len(baslik or "")

    for tutar_bul in _TUTAR.finditer(metin):
        deger = para_normalize(tutar_bul.group())
        if deger is None:
            continue

        baslangic, bitis = tutar_bul.start(), tutar_bul.end()
        cumle = _tutar_cumle(metin, baslangic, bitis)
        pencere = _pencere(metin, baslangic, bitis, 70)

        onceki = _kucult(metin[max(0, baslangic - 25):baslangic])
        sonraki = _kucult(metin[bitis:min(len(metin), bitis + 35)])
        baslikta = baslangic < baslik_sonu
        toplam_ifadesi = bool(_TOPLAM_ONCESI.search(onceki))

        # -------------------------------------------------------------
        # 3.0 HARCAMA EŞİĞİ — HER ŞEYDEN ÖNCE
        # -------------------------------------------------------------
        # Bu kontrol eskiden 3.4'teydi, yani PUAN dalından (3.3) SONRA.
        # "her 1.500 TL ve üzeri harcamaya 50 TL, toplamda 200 TL Worldpuan"
        # cümlesinde 1.500 TL'nin ±70 penceresinde "Worldpuan" geçtiği için
        # puan dalı önce tetikleniyor ve ASGARİ HARCAMA EŞİĞİ, ödül tutarı
        # olarak kaydediliyordu. Bir eşik, yanında hangi ödül kelimesi geçerse
        # geçsin eşiktir; bu yüzden sıranın başına alındı.
        if _HARCAMA_IPUCLARI.search(cumle):
            esik = _ESIK_SONRASI.match(sonraki)
            if esik:
                asgari = bool(re.match(
                    r"\s*(?:ve\s+)?(?:üzeri|üstü|yukarısı|fazlası)",
                    sonraki, re.IGNORECASE))
                aday = _bulgu(metin, tutar_bul, deger,
                              "para+esik_deyimi", guven=0.96, birim="TL")
                anahtar = "min_harcama_tl" if asgari else "max_harcama_tl"
                bulgular[anahtar] = _ilk_yuksek_guvenli(bulgular.get(anahtar), aday)
                continue

        # -------------------------------------------------------------
        # 3.1 MGM (Müşteri Getir Müşteri)
        # -------------------------------------------------------------
        if re.search(
            r"(arkadaş|arkadas|davet|referans|yakınını|yakinini)"
            r".{0,80}"
            r"(kazan|ödül|odul|iade|hediye)",
            cumle,
            re.IGNORECASE,
        ) or re.search(
            r"(kazan|ödül|odul|iade|hediye)"
            r".{0,80}"
            r"(arkadaş|arkadas|davet|referans|yakınını|yakinini)",
            cumle,
            re.IGNORECASE,
        ):
            # "toplam(da)" ifadesi kampanyanın İLAN EDİLEN değerini işaret
            # eder ve diğer dalların (puan 0.97, ödül 0.93) üzerine çıkmalıdır;
            # sabit 0.94 ile MGM toplamı puan dalına yeniliyordu.
            aday = _bulgu(
                metin,
                tutar_bul,
                deger,
                "para+mgm_baglami" + ("+toplam" if toplam_ifadesi else ""),
                guven=1.0 if toplam_ifadesi else 0.94,
                birim="TL",
            )

            # ⚠️ Ayrım cümle bazlıydı, oysa MGM metinlerinde iki tutar AYNI
            # cümlede geçiyor: "her yakınınız için 500 TL, toplamda 5.000 TL'ye
            # varan". İkisi de kişi başı kazanca yazılıyor, kampanya tavanı
            # (5.000 TL) kayboluyordu. Ayırt edici işaret "toplam(da)" ifadesi.
            if toplam_ifadesi:
                bulgular["mgm_limit_tl"] = _ilk_yuksek_guvenli(
                    bulgular.get("mgm_limit_tl"), aday
                )
                # İlan edilen toplam, kampanyanın ödül tutarıdır.
                bulgular["odul_tutari_tl"] = _ilk_yuksek_guvenli(
                    bulgular.get("odul_tutari_tl"), aday
                )
            elif "mgm" in cumle or "arkadaş" in cumle or "davet" in cumle:
                bulgular["kisi_basi_kazanc"] = _ilk_yuksek_guvenli(
                    bulgular.get("kisi_basi_kazanc"), aday
                )
            else:
                bulgular["mgm_limit_tl"] = _ilk_yuksek_guvenli(
                    bulgular.get("mgm_limit_tl"), aday
                )
            continue

        # -------------------------------------------------------------
        # 3.2 Tahsis / dosya masrafı
        # -------------------------------------------------------------
        if _MASRAF_IPUCLARI.search(pencere):
            if not re.search(r"\b(?:üyelik|abonelik)\b", pencere):
                aday = _bulgu(
                    metin,
                    tutar_bul,
                    deger,
                    "para+masraf_baglami",
                    guven=0.94,
                    birim="TL",
                )
                bulgular["tahsis_ucreti_tl"] = _ilk_yuksek_guvenli(
                    bulgular.get("tahsis_ucreti_tl"), aday
                )
                continue

        # -------------------------------------------------------------
        # 3.3 Puan / mil
        # -------------------------------------------------------------
        if _PUAN_IPUCLARI.search(pencere):
            aday = _bulgu(
                metin,
                tutar_bul,
                deger,
                "para+puan_baglami" + ("+toplam" if toplam_ifadesi
                                       else "+baslik" if baslikta else ""),
                guven=1.0 if toplam_ifadesi else (0.99 if baslikta else 0.97),
                birim="TL",
            )
            bulgular["puan_kazanc"] = _ilk_yuksek_guvenli(
                bulgular.get("puan_kazanc"), aday
            )
            # 🎁 PUAN ÖDÜLÜ AYNI ZAMANDA BİR ÖDÜL TUTARIDIR.
            # Bu dal `continue` ile bittiği için 3.6 (ödül) hiç çalışmıyor ve
            # "500 TL Worldpuan" yalnızca `puan_kazanc`a yazılıyordu. Ölçüm:
            # kural katmanı tek başına çalıştığında Albaraka'nın 12 ödüllü
            # kampanyasının 11'inde `odul_tutari` BOŞ kalıyordu (LLM devrede
            # olduğu için tabloda görünmüyordu, ama LLM erişilemediğinde ödül
            # kıyaslaması tamamen çöküyordu).
            # Bu programların birimi zaten TL'dir ("500 TL Worldpuan"), o
            # yüzden aynı değer ödül tutarı olarak da yazılıyor.
            bulgular["odul_tutari_tl"] = _ilk_yuksek_guvenli(
                bulgular.get("odul_tutari_tl"), aday
            )
            continue

        # -------------------------------------------------------------
        # 3.4 Harcama eşiği
        # -------------------------------------------------------------
        if _HARCAMA_IPUCLARI.search(cumle):
            # Eşik deyimi kontrolü 3.0'a taşındı (puan dalından önce olmalı).
            if _MIN_IPUCLARI.search(onceki) or _MIN_IPUCLARI.search(pencere):
                aday = _bulgu(
                    metin,
                    tutar_bul,
                    deger,
                    "para+min_harcama_baglami",
                    guven=0.98,
                    birim="TL",
                )
                bulgular["min_harcama_tl"] = _ilk_yuksek_guvenli(
                    bulgular.get("min_harcama_tl"), aday
                )
                continue

            # ⚠️ ÖDÜL TAVANI, HARCAMA TAVANI DEĞİLDİR.
            # `_MAX_IPUCLARI` gevşek ("kadar", "maksimum", "azami") ve bu dal
            # cümlede harcama kelimesi geçtiği anda tetikleniyor. Sonuç:
            # "her ay 250 TL'ye KADAR indirim kazanma" ve "tek işlemde
            # MAKSİMUM 5.000 TL indirim kazanılabilir" ifadelerindeki ÖDÜL
            # ÜST SINIRI, harcama tavanı olarak kaydedilip 3.6'ya hiç
            # ulaşmıyordu. Pencerede bir ödül kelimesi varsa bu bir ödül
            # tavanıdır; aşağıdaki ödül dalına bırakılıyor.
            if ((_MAX_IPUCLARI.search(onceki) or _MAX_IPUCLARI.search(pencere))
                    and not _ODUL_IPUCLARI.search(pencere)):
                aday = _bulgu(
                    metin,
                    tutar_bul,
                    deger,
                    "para+max_harcama_baglami",
                    guven=0.92,
                    birim="TL",
                )
                bulgular["max_harcama_tl"] = _ilk_yuksek_guvenli(
                    bulgular.get("max_harcama_tl"), aday
                )
                continue

        # -------------------------------------------------------------
        # 3.5 Finansman / Kredi / Kampanya Üst Limitleri (GÜNCELLENDİ)
        # -------------------------------------------------------------
        genel_limit_baglami = re.search(
            r"\b(?:üst\s+limit|azami|maksimum|max|kampanya\s+limiti|kredi\s+limiti|tutar\s+limiti)\b",
            pencere,
            re.IGNORECASE,
        )

        acik_finansman = bool(
            _FINANSMAN_IPUCLARI.search(cumle) or _KREDI_IPUCLARI.search(cumle)
        )
        finansman_baglami = (
            acik_finansman
            or "taksit" in cumle.lower()
            or genel_limit_baglami
        )

        # ⚠️ ÖDÜL BAĞLAMI FİNANSMANI BASTIRIR.
        # "tek işlemde maksimum 5.000 TL indirim kazanılabilir" cümlesinde
        # finansman/kredi kelimesi YOK; bağlamı yalnızca "maksimum" kelimesi
        # (genel_limit_baglami) kuruyor ve ödül üst sınırı FİNANSMAN TUTARI
        # olarak kaydediliyordu. Ortada bir ödül kelimesi varken finansman
        # sayabilmek için AÇIK bir finansman/kredi kelimesi şart.
        if finansman_baglami and _ODUL_IPUCLARI.search(pencere) and not acik_finansman:
            finansman_baglami = False

        if finansman_baglami:
            # Min Finansman Tutarı
            if _MIN_IPUCLARI.search(onceki) or re.search(
                r"\b(?:en az|minimum|asgari)\b.{0,20}(?:finansman|kredi|tutar)",
                cumle,
                re.IGNORECASE,
            ):
                aday = _bulgu(
                    metin,
                    tutar_bul,
                    deger,
                    "para+min_finansman_baglami",
                    guven=0.94,
                    birim="TL",
                )
                bulgular["min_finansman_tutari"] = _ilk_yuksek_guvenli(
                    bulgular.get("min_finansman_tutari"), aday
                )
                continue

            # Max Finansman Tutarı / Kampanya Üst Limiti
            # ⚠️ Makuliyet tabanı burada da geçerli. `semaya_donustur` artık
            # `finansman_tutari` boşsa bu alana düşüyor; taban olmayınca
            # "en fazla 300 TL nakit iade" gibi ÖDÜL TAVANLARI finansman
            # tutarı olarak tabloya giriyordu (6 kayıt: 100/250/300/500 TL).
            # Ödül tavanı koruması burada da geçerli: "tek işlemde MAKSİMUM
            # 5.000 TL indirim kazanılabilir" cümlesinde `genel_limit_baglami`
            # ("maksimum") tetikleniyor ve ödül üst sınırı FİNANSMAN LİMİTİ
            # olarak kaydediliyordu.
            if ((_MAX_IPUCLARI.search(pencere) or genel_limit_baglami)
                    and deger >= _ASGARI_FINANSMAN_TUTARI
                    and not _ODUL_IPUCLARI.search(pencere)):
                aday = _bulgu(
                    metin,
                    tutar_bul,
                    deger,
                    "para+max_finansman_baglami",
                    guven=0.95,
                    birim="TL",
                )
                bulgular["max_finansman_tutari"] = _ilk_yuksek_guvenli(
                    bulgular.get("max_finansman_tutari"), aday
                )
                continue

            # Genel Finansman Tutarı
            # ⚠️ Makuliyet tabanı: "2.500 TL ve üzeri harcamalarında 250 TL
            # kazan" gibi cümlelerde ödül tutarı da finansman bağlamının
            # içinde kalıyor ve 250 TL'lik "finansman tutarı" üretiyordu.
            # Bu eşiğin altındaki tutar finansman değildir; aşağıdaki ödül
            # dalına düşmesi için burada yakalanmıyor.
            if deger < _ASGARI_FINANSMAN_TUTARI:
                pass
            else:
                aday = _bulgu(
                    metin,
                    tutar_bul,
                    deger,
                    "para+finansman_baglami",
                    guven=0.93,
                    birim="TL",
                )
                bulgular["finansman_tutari"] = _ilk_yuksek_guvenli(
                    bulgular.get("finansman_tutari"), aday
                )
                continue

        # -------------------------------------------------------------
        # 3.6 Ödül / hediye / iade
        # -------------------------------------------------------------
        if _ODUL_IPUCLARI.search(cumle):
            # 🏷️ BAŞLIKTAKİ TUTAR ÖNCELİKLİDİR.
            # Kampanya gövdeleri çoğu kez kademe tablosu içeriyor
            # ("7.500-14.999 TL harcamaya 500 TL, 15.000-24.999 TL'ye 800 TL…")
            # ve ilk yakalanan kademe, başlıkta REKLAM EDİLEN üst tutarı
            # eziyordu: "Giyim ve Kozmetik Alışverişlerinize 1.300 TL
            # ParafPara" kaydında ödül 50 TL olarak yazılmıştı. Başlık,
            # bankanın ilan ettiği değerdir; ona daha yüksek güven veriyoruz.
            aday = _bulgu(
                metin,
                tutar_bul,
                deger,
                "para+odul_baglami" + ("+toplam" if toplam_ifadesi
                                       else "+baslik" if baslikta else ""),
                guven=1.0 if toplam_ifadesi else (0.97 if baslikta else 0.93),
                birim="TL",
            )
            bulgular["odul_tutari_tl"] = _ilk_yuksek_guvenli(
                bulgular.get("odul_tutari_tl"), aday
            )

    return bulgular


# =============================================================================
# 4. MASRAF DURUMU
# =============================================================================

_MASRAF_YOK = re.compile(
    r"[^.!?]*(?:"
    r"masraf\w*\s+al[ıi]nmamaktad[ıi]r"
    r"|masraf\w*\s+al[ıi]nmaz"
    r"|masrafs[ıi]z"
    r"|ücret\w*\s+al[ıi]nmamaktad[ıi]r"
    r"|ücret\w*\s+al[ıi]nmaz"
    r"|banka\s+taraf[ıi]ndan\s+karş[ıi]lan\w+"
    r"|tahsis\s+ücreti\s+yok"
    r"|tahsis\s+ücreti\s+al[ıi]nm"
    r")[^.!?]*[.!?]?",
    re.IGNORECASE,
)

_UCRETSIZ_HIZMET = re.compile(
    r"[^.!?]*ücretsiz[^.!?]*[.!?]?",
    re.IGNORECASE,
)

_BANKA_HIZMETI = re.compile(
    r"\bhavale\b|\beft\b|\bfast\b|komisyon|hesap\s+işletim|"
    r"para\s+transfer|dosya|tahsis|masraf",
    re.IGNORECASE,
)


def masraf_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}

    masraf_bul = _MASRAF_YOK.search(metin)
    if masraf_bul:
        cumle = masraf_bul.group().strip()

        bulgular["tahsis_ucreti"] = AlanBulgusu(
            deger=0.0,
            ham_metin=cumle,
            kural="masraf_yok_kalibi",
            guven=0.99,
            kanit_metni=cumle,
            birim="TL",
        )

        bulgular["masraf_bilgi"] = AlanBulgusu(
            deger=cumle,
            ham_metin=cumle,
            kural="masraf_yok_kalibi",
            guven=0.99,
            kanit_metni=cumle,
            birim="metin",
        )

        return bulgular

    for hizmet_bul in _UCRETSIZ_HIZMET.finditer(metin):
        cumle = hizmet_bul.group().strip()

        if (
            _BANKA_HIZMETI.search(cumle)
            and "sms" not in cumle.lower()
        ):
            bulgular["masraf_bilgi"] = AlanBulgusu(
                deger=cumle,
                ham_metin=cumle,
                kural="ucretsiz_hizmet_kalibi",
                guven=0.92,
                kanit_metni=cumle,
                baslangic_konum=hizmet_bul.start(),
                bitis_konum=hizmet_bul.end(),
                birim="metin",
            )
            return bulgular

    return {}


import re
from datetime import datetime
from typing import Dict

# 1. Sayısal Tarih Aralığı (ör. 17.08.2026 - 17.09.2026)
_TARIH_ARALIGI = re.compile(
    r"("
    r"\d{1,2}[./-]\d{1,2}[./-]\d{4}"
    r")\s*(?:-|–|—|ile|ve)\s*("
    r"\d{1,2}[./-]\d{1,2}[./-]\d{4}"
    r")",
    re.IGNORECASE,
)

# 2. Yazılı Tarih Aralığı (ör. 17 Ağustos - 17 Eylül 2026 veya 17 Ağustos 2026 - 17 Eylül 2026)
_TARIH_ARALIGI_YAZI = re.compile(
    r"("
    r"\d{1,2}\s+[a-zçğıöşü]+(?:\s+\d{4})?"  # İlk tarihteki yıl opsiyonel yapıldı (?:\s+\d{4})?
    r")\s*(?:-|–|—|ile|ve)\s*("
    r"\d{1,2}\s+[a-zçğıöşü]+\s+\d{4}"        # İkinci tarihte yıl zorunlu
    r")",
    re.IGNORECASE,
)

_BITIS_TARIHI = re.compile(
    r"("
    r"(?:\d{1,2}\s+[a-zçğıöşü]+\s+\d{4}"
    r"|\d{1,2}[./-]\d{1,2}[./-]\d{4})"
    r")"
    r"[a-zçğıöşü' ]{0,20}"
    r"(?:tarihine\s+)?kadar",
    re.IGNORECASE,
)


import re
from datetime import datetime, date
from typing import Dict


def _tarih_objesine_cevir(tarih_val) -> datetime:
    """tarih_normalize'den gelen değeri güvenli bir şekilde datetime objesine dönüştürür."""
    if isinstance(tarih_val, datetime):
        return tarih_val
    if isinstance(tarih_val, date):
        return datetime.combine(tarih_val, datetime.min.time())
    if isinstance(tarih_val, str):
        # Yaygın string formatları denenir
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(tarih_val.strip(), fmt)
            except ValueError:
                pass
    return None


# Kampanya tarihleri için makul yıl penceresi. Bundan uzak bir yıl, kampanya
# gerçeği değil ayrıştırma/tarama artefaktıdır (bkz. 2076 örneği).
_TARIH_GECMIS_YIL = 12
_TARIH_GELECEK_YIL = 8


def _makul_tarih_mi(tarih_val) -> bool:
    """None kabul edilir (alan yok demektir); dolu ama saçma yıl reddedilir."""
    if tarih_val is None:
        return True
    dt = _tarih_objesine_cevir(tarih_val)
    if dt is None:
        return True          # çevrilemiyorsa burada karar verme
    bu_yil = date.today().year
    return (bu_yil - _TARIH_GECMIS_YIL) <= dt.year <= (bu_yil + _TARIH_GELECEK_YIL)


def tarihleri_cikar(
    metin: str,
    temizlenme_tarihi: Optional[Union[str, date, datetime]] = None
) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}

    # 5.1 Sayısal tarih aralığı
    tarih_bul = _TARIH_ARALIGI.search(metin)

    # 5.2 Yazılı tarih aralığı
    if not tarih_bul:
        tarih_bul = _TARIH_ARALIGI_YAZI.search(metin)

    if tarih_bul:
        bas_str = tarih_bul.group(1).strip()
        bit_str = tarih_bul.group(2).strip()

        # İlk tarihte yıl yoksa (ör. "17 Ağustos"), bitiş tarihinin yılını alıp ekler
        if not re.search(r"\d{4}", bas_str):
            yil_eslesme = re.search(r"\d{4}", bit_str)
            if yil_eslesme:
                bas_str += f" {yil_eslesme.group()}"

        bas = tarih_normalize(bas_str)
        bit = tarih_normalize(bit_str)

        # ⚠️ Aralık kalıbı ilk eşleşmeyi alır ve makuliyete bakmazdı. Taranan
        # metinlerde bozuk yıllar var ("... 2026 - 31 ... 2076"); bu kayıtta
        # doğru tarih "31 Temmuz 2026" metnin üç ayrı yerinde yazılı olduğu
        # hâlde bitiş 2076-07-31 olarak kaydedilmişti. Makul olmayan yıl
        # üreten aralık eşleşmesini çöpe atıp 5.3'teki "…tarihine kadar"
        # kalıbına düşüyoruz.
        if not (_makul_tarih_mi(bas) and _makul_tarih_mi(bit)):
            bas = bit = None

        if bas:
            bulgular["baslangic_tarihi"] = _bulgu(
                metin, tarih_bul, bas, "tarih_araligi", guven=0.99, birim="tarih"
            )

        if bit:
            bulgular["bitis_tarihi"] = _bulgu(
                metin, tarih_bul, bit, "tarih_araligi", guven=0.99, birim="tarih"
            )

        # Süre hesaplama (sure_gun)
        if bas and bit:
            bas_dt = _tarih_objesine_cevir(bas)
            bit_dt = _tarih_objesine_cevir(bit)

            if bas_dt and bit_dt:
                sure = abs((bit_dt - bas_dt).days)
                bulgular["sure_gun"] = _bulgu(
                    metin, tarih_bul, sure, "hesaplanmis_sure", guven=0.99, birim="gun"
                )

        # Aralık kalıbı işe yaradıysa bitir; makul olmayan tarih ürettiyse
        # (yukarıda temizlendi) aşağıdaki daha dar kalıba düşülür.
        if bas or bit:
            return bulgular

    # 5.3 "... tarihine kadar"
    tarih_bul = _BITIS_TARIHI.search(metin)

    if tarih_bul:
        bit = tarih_normalize(tarih_bul.group(1))

        if bit:
            bulgular["bitis_tarihi"] = _bulgu(
                metin, tarih_bul, bit, "tarih+kadar_kalibi", guven=0.97, birim="tarih"
            )

            # BAŞLANGIÇ TARİHİ VE SÜRE ATAMA (Bitiş Var, Başlangıç Yok)
            bas_varsayilan = temizlenme_tarihi or date.today()

            # str formatına/ISO formatına dönüştürme kontrolü
            if isinstance(bas_varsayilan, (date, datetime)):
                bas_varsayilan_str = bas_varsayilan.isoformat()
            else:
                bas_varsayilan_str = str(bas_varsayilan)

            bas_norm = tarih_normalize(bas_varsayilan_str) or bas_varsayilan_str

            bas_dt = _tarih_objesine_cevir(bas_norm)
            bit_dt = _tarih_objesine_cevir(bit)

            # ⚠️ Uydurulan başlangıç, metinden OKUNAN bitişten sonra olamaz.
            # `temizlenme_tarihi` bu çağrı yolunda hep None olduğu için
            # varsayılan daima "bugün"dü; süresi geçmiş kampanyalarda bu
            # "bugün başladı, iki ay önce bitti" gibi imkânsız kayıtlar
            # üretiyordu (10 kayıt) ve alttaki max(0, ...) kırpması yüzünden
            # sure_gun 0 çıkıyordu (6 kayıt). Bilinmeyen başlangıç, YANLIŞ
            # başlangıçtan iyidir: böyle durumda alanı hiç yazmıyoruz.
            if bas_dt and bit_dt and bas_dt > bit_dt:
                return bulgular

            bulgular["baslangic_tarihi"] = _bulgu(
                metin, tarih_bul, bas_norm, "varsayilan_temizlenme_tarihi", guven=0.80, birim="tarih"
            )

            # Bitiş ile varsayılan başlangıç arasındaki süreyi hesapla
            if bas_dt and bit_dt:
                sure = max(0, (bit_dt - bas_dt).days)
                bulgular["sure_gun"] = _bulgu(
                    metin, tarih_bul, sure, "hesaplanmis_sure_varsayilan", guven=0.80, birim="gun"
                )

    return bulgular

# =============================================================================
# 6. HEDEF KİTLE
# =============================================================================

_HEDEF_KALIPLARI = [
    (
        "maas_musterisi",
        re.compile(
            r"\bmaaş\s+müşteri\w*"
            r"|\bmaaş[ıi]n[ıi]\s+taş[ıi]yan\w*",
            re.IGNORECASE,
        ),
    ),
    (
        "özel",
        re.compile(
            r"\besnaf\b|\bçiftçi\b|\bşah[ıi]s\s+firma\w*"
            r"|\bişletme\s+sahi\w*|\bişletmelere\b"
            r"|\bişletmeniz\w*|\bKOBİ\b|\bemekli\b"
            r"|\böğrenci\b|\bgenç(?:lere|ler)?\b"
            r"|\bbireysel\b",
            re.IGNORECASE,
        ),
    ),
    (
        "yeni_musteri",
        re.compile(
            r"\byeni\s+müşteri\w*"
            r"|\bmüşteri\s+ol(?:an|acak|up|mak)\b"
            r"|\byeni\s+açılacak\w*"
            r"|\byeni\s+açılan\w*"
            r"|\bilk\s+kez\s+hesap\b",
            re.IGNORECASE,
        ),
    ),
    (
        "mevcut_musteri",
        re.compile(
            r"\bmevcut\s+müşteri\w*"
            r"|\bmüşterilerimize\s+özel\b"
            r"|\bmevcut\s+müşteriler\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tum_musteriler",
        re.compile(
            r"\btüm\s+müşteri\w*"
            r"|\bherkes\b"
            r"|\btüm\s+kullanıcı\w*"
            r"|\btüm\s+bireysel\s+müşteri\w*",
            re.IGNORECASE,
        ),
    ),
]


import re

_HEDEF_KALIPLARI = [
    (
        "maas_musterisi",
        re.compile(
            r"\bmaaş\s+müşteri\w*"
            r"|\bmaaş[ıi]n[ıi]\s+taş[ıi]yan\w*",
            re.IGNORECASE,
        ),
    ),
    (
        "segment",
        re.compile(
            r"\besnaf\b|\bçiftçi\b|\bşah[ıi]s\s+firma\w*"
            r"|\bişletme\s+sahi\w*|\bişletmelere\b"
            r"|\bişletmeniz\w*|\bKOBİ\b|\bemekli\b"
            r"|\böğrenci\b|\bgenç(?:lere|ler)?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "yeni_musteri",
        re.compile(
            r"\byeni\s+müşteri\w*"
            r"|\bmüşteri\s+ol(?:acak|up|mak)\b"
            r"|\bdavet\s+edilen\b"
            r"|\bilk\s+kez\s+müşteri\b"
            r"|\byeni\s+açılacak\w*"
            r"|\byeni\s+açılan\w*"
            r"|\bilk\s+kez\s+hesap\b"
            r"|\bhenüz\s+müşteri\s+değil\w*",
            re.IGNORECASE,
        ),
    ),
    (
        "mevcut_musteri",
        re.compile(
            r"\bmevcut\s+müşteri\w*"
            r"|\bmüşterilerimize\s+özel\b"
            r"|\bmüşterisiyseniz\b"
            r"|\bmevcut\s+müşteriler\b"
            r"|\bbireysel\s+müşteri\w*"  
            r"|\btüm\s+müşteri\w*"        
            r"|\bdavet\s+eden\b",
            re.IGNORECASE,
        ),
    ),
]

_HEDEF_DISLAMA = re.compile(
    r"yararlanamaz|katılamaz|dahil\s+değil|yararlanamazlar|"
    r"faydalanamaz",
    re.IGNORECASE,
)

from typing import Dict, List, Set

_GUVEN_SKORLARI = {
    "maas_musterisi": 0.98,
    "ozel": 0.95,
    "yeni_musteri": 0.98,
    "mevcut_musteri": 0.98,
}


def hedef_kitle_cikar(metin: str) -> Dict[str, List[str]]:
    bulunan_kitleler: Set[str] = set()

    for etiket, desen in _HEDEF_KALIPLARI:
        for esles in desen.finditer(metin):
            sonrasi = metin[esles.end() : min(len(metin), esles.end() + 150)].lower()

            # Dışlama kontrolü
            if _HEDEF_DISLAMA.search(sonrasi):
                continue

            bulunan_kitleler.add(etiket)

    # DÜZELTME / NORMALİZASYON MANTIĞI:
    # Metinde özel bir şart veya kitle bulunamadıysa varsayılan olarak 'mevcut_musteri' kabul edilir.
    if not bulunan_kitleler:
        bulunan_kitleler.add("mevcut_musteri")

    return {"hedef_kitle": list(bulunan_kitleler)}


# =============================================================================
# 7. MGM / ARKADAŞINI GETİR
# =============================================================================

_MGM_KISI_LIMITI = re.compile(
    r"(?:toplamda|toplam)\s+(\d+)\s+kişi",
    re.IGNORECASE
)

_MGM_MAX_ODUL = re.compile(
    r"maksimum\s+([\d.,]+(?:\s*bin)?)\s*TL\s+nakit\s+ödül",
    re.IGNORECASE
)

def mgm_detay_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}

    # 1. Kişi Sayısı Limiti Yakalama (Örn: 5 kişi)
    kisi_bul = _MGM_KISI_LIMITI.search(metin)
    if kisi_bul:
        kisi_sayisi = int(kisi_bul.group(1))
        bulgular["mgm_limit_kisi"] = _bulgu(
            metin,
            kisi_bul,
            kisi_sayisi,
            "sayi+mgm_kisi_limiti",
            guven=0.99,
            birim="kisi",
        )

    # 2. Kişi Başı ve Maksimum Ödül Tutarları
    # 2.000 TL kişi başı kazanç
    kisi_basi_bul = re.search(r"kişi\s+başı\s+maksimum\s+([\d.,]+)\s*TL", metin, re.IGNORECASE)
    if kisi_basi_bul:
        deger = para_normalize(kisi_basi_bul.group(1) + " TL")
        if deger:
            bulgular["kisi_basi_kazanc"] = _bulgu(
                metin,
                kisi_basi_bul,
                deger,
                "para+mgm_kisi_basi",
                guven=0.98,
                birim="TL",
            )

    # Toplam 10.000 TL maksimum ödül tutarı
    toplam_odul_bul = _MGM_MAX_ODUL.search(metin)
    if toplam_odul_bul:
        deger = para_normalize(toplam_odul_bul.group(1) + " TL")
        if deger:
            bulgular["odul_tutari_tl"] = _bulgu(
                metin,
                toplam_odul_bul,
                deger,
                "para+mgm_toplam_odul",
                guven=0.98,
                birim="TL",
            )

    return bulgular

#_MGM_KALIBI = re.compile(
    #r"arkadaşını\s+(?:davet\s+et|getir)"
    #r"|arkadaşınızı\s+(?:davet\s+edin|getirin)"
    #r"|arkadaşı\w*\s+getir\w*"
    #r"|arkadaş\w*\s+davet\s+et\w*"
    #r"|yakınını\s+davet\s+et\w*"
    #r"|yakınınızı\s+davet\s+edin"
    #r"|davet\s+et(?:tiğin|tiğiniz)?\s+arkadaş"
    #r"|referans\s+(?:kod|link|bağlant)"
    #r"|referansın\w*\s+ile"
    #r"|getir\s+kazan",
    #re.IGNORECASE,
#)


#def mgm_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    #esles = _MGM_KALIBI.search(metin)

    #if not esles:
        #return {}

    #return {
        #"is_mgm": _bulgu(
            #metin,
            #esles,
            #True,
            #"mgm_kalibi",
            #guven=0.99,
            #birim="boolean",
        #)
    #}


# =============================================================================
# 8. KAMPANYA TÜRÜ (campain_classifier üzerinden)
# =============================================================================

def kategori_cikar(
    baslik: str,
    metin: str,
    llm_aktif: bool = False,
) -> Dict[str, AlanBulgusu]:
    """
    Kampanyanın temel ürün/aksiyon türünü campain_classifier.siniflandir
    kullanarak çıkarır.
    """
    cb: Optional[AlanBulgusu] = siniflandir(
        baslik or "", metin or "", llm_aktif=llm_aktif
    )

    if cb is None:
        return {}

    return {
        "kampanya_turu": AlanBulgusu(
            deger=cb.deger,
            ham_metin=cb.ham,
            kural=cb.kural,
            yontem="regex",
            guven=0.94,
            kanit_metni=cb.ham,
            birim="metin",
        )
    }


import re
from typing import Any, Dict, Optional

# Projenizdeki AlanBulgusu sınıf yapısına uygun temsil (gerekliyse import edin)
class AlanBulgusu:
    def __init__(
        self,
        deger: Any,
        ham_metin: str = "",
        kural: str = "",
        yontem: str = "regex",
        guven: float = 1.0,
        kanit_metni: str = "",
        baslangic_konum: int = -1,
        bitis_konum: int = -1,
        birim: Optional[str] = None,
    ):
        self.deger = deger
        self.ham_metin = ham_metin
        self.kural = kural
        self.yontem = yontem
        self.guven = guven
        self.kanit_metni = kanit_metni
        self.baslangic_konum = baslangic_konum
        self.bitis_konum = bitis_konum
        self.birim = birim


def metni_temizle(metin: str) -> str:
    """Metin içindeki peş peşe sayılan genel şart sektör listelerini temizler."""
    if not metin:
        return ""
    
    coklu_sektor_pattern = re.compile(
        r"(?:restoran|market|akaryakıt|eğitim|elektronik|giyim|kozmetik|seyahat|sağlık|ulaşım|yapı|sigorta)"
        r"(?:\s*,\s*|\s+veya\s+|\s+ve\s+|\s+)"
        r"(?:restoran|market|akaryakıt|eğitim|elektronik|giyim|kozmetik|seyahat|sağlık|ulaşım|yapı|sigorta)"
        r"(?:\s*,\s*|\s+veya\s+|\s+ve\s+|\s+)"
        r"(?:restoran|market|akaryakıt|eğitim|elektronik|giyim|kozmetik|seyahat|sağlık|ulaşım|yapı|sigorta)",
        re.IGNORECASE
    )
    return coklu_sektor_pattern.sub("", metin)


def metni_temizle(metin: str) -> str:
    """Metin içindeki peş peşe sayılan genel şart sektör listelerini temizler."""
    if not metin:
        return ""
    
    coklu_sektor_pattern = re.compile(
        r"(?:restoran|market|akaryakıt|eğitim|elektronik|giyim|kozmetik|seyahat|sağlık|ulaşım|yapı|sigorta)"
        r"(?:\s*,\s*|\s+veya\s+|\s+ve\s+|\s+)"
        r"(?:restoran|market|akaryakıt|eğitim|elektronik|giyim|kozmetik|seyahat|sağlık|ulaşım|yapı|sigorta)"
        r"(?:\s*,\s*|\s+veya\s+|\s+ve\s+|\s+)"
        r"(?:restoran|market|akaryakıt|eğitim|elektronik|giyim|kozmetik|seyahat|sağlık|ulaşım|yapı|sigorta)",
        re.IGNORECASE
    )
    return coklu_sektor_pattern.sub("", metin)


import re
from typing import Dict, Optional

# Gövde metninden bir sektörün toplayabileceği en yüksek puan. Başlık zaten 3
# puan getirdiği için tavan 2 olunca başlık her zaman gövdeyi yener.
_METIN_SKOR_TAVANI = 2
# Tek bir kaçak kelimenin sektör belirlemesini engelleyen alt eşik.
_ASGARI_SEKTOR_SKORU = 2


def sektor_cikar(metin: str, baslik: str = "") -> Dict[str, AlanBulgusu]:
    """
    Başlık ve metin üzerinden sektör/kategori tespiti yapar 
    ve projeye uygun AlanBulgusu yapısında bir Dict döner.
    """
    islenen_metin = metni_temizle(metin)
    
    # 1. AŞAMA: Çoklu Bankacılık / Program Kontrolü (Override Kuralı)
    genel_bankacilik_pattern = re.compile(
        r"\bi[şs]lem\s+yapt[ıi]k[çc]a\s+kazan\b|\bg[üu]nl[üu]k\s+bankac[ıi]l[ıi]k\b"
        r"|\bbankac[ıi]l[ıi]k\s+i[şs]lemleri\b|\bhayat\s+pay\b|\barkada[şs][ıi]n[ıi]\s+davet\b", 
        re.IGNORECASE
    )
    
    eslesme = genel_bankacilik_pattern.search(baslik) or genel_bankacilik_pattern.search(islenen_metin)
    if eslesme:
        islem_sayaci = 0
        if re.search(r"\bfatura\b", islenen_metin, re.IGNORECASE): islem_sayaci += 1
        if re.search(r"\bd[öo]viz\b|\bal[ıi]m[- ]sat[ıi]m\b", islenen_metin, re.IGNORECASE): islem_sayaci += 1
        if re.search(r"\btransfer\b|\beft\b|\bfast\b", islenen_metin, re.IGNORECASE): islem_sayaci += 1
        if re.search(r"\bkart\s+harcamas[ıi]\b|\bbanka\s+kart\b", islenen_metin, re.IGNORECASE): islem_sayaci += 1
        
        if islem_sayaci >= 2:
            return {
                "sektor": _bulgu(
                    metin=islenen_metin,
                    eslesme=eslesme,
                    deger="Genel / Sektör Bağımsız",
                    kural="sektor_coklu_bankacilik_override",
                    guven=0.95,
                    birim="kategori"
                )
            }

    # 2. AŞAMA: Skorlama Mimarisi (İstenen 7 Sektör)
    # ⚠️ TÜRKÇE EK TOLERANSI (27.08.2026): Genel adların sonundaki `\b`,
    # kelime ek aldığında eşleşmeyi bozuyordu — "Seyahatlerinde" `\bseyahat\b`
    # ile tutmuyor, kampanya "Genel / Sektör Bağımsız" kalıyordu. Ölçüm:
    # bilet +5, eğitim +3, seyahat/otel/market +1 başlık. Genel adlara `\w*`
    # eklendi; MARKA adları `\b` ile bırakıldı (ör. `mavi\w*` "maviye"yi de
    # tutar), ayrıca ekle anlamı kayan kökler (saat, takı, araç, tur, oto)
    # bilerek dar tutuldu: `tur\w*` "turkcell"i, `ara[çc]\w*` "aracılık"ı
    # yakalardı.
    sektor_kurallari = {
        "Market ve Gıda": (
            # `\bbin\b` BİM zincirinin yazım hatasıydı ve tutarlardaki
            # "250 Bin TL" ile eşleşip 2 kaydı Market'e itiyordu.
            # "yapı marketi" bir NALBURDUR, market zinciri değil; bu yüzden
            # "Mobilya, Dekorasyon ve Yapı Marketi Alışverişinize" kampanyası
            # Market ve Gıda'ya düşüyordu. Negatif geriye bakış onu dışlıyor.
            r"(?<!yapı )(?<!yapi )\bmarket\w*"
            r"|\bg[ıi]da\w*|\bs[üu]permarket\w*|\bhipermarket\w*|\bşarküteri\w*|\bmanav\w*|\bkasap\w*"
            r"|\bmigros\b|\bcarrefour\b|\bcarrefoursa\b|\bbim\b|\ba101\b|\bşok\b|\bfile\b|\bmacrocenter\b"
            r"|\byemeksepeti\s+market\b|\bgetirmarket\b|\bgetir\s+büyük\b|\bistegelsin\b|\bavm\s+g[ıi]da\b"
        ),
        "E-Ticaret ve Pazaryerleri": (
            r"\be-?t[ıi]caret\w*|\bpazaryer[ıi]\w*|\bonline\s+al[ıi][şs]veri[şs]\w*|\btrendyol\b|\bhepsiburada\b"
            r"|\bn11\b|\bamazon\b|\bçiçeksepeti\b|\bpazarama\b|\bidefix\b|\bbonanza\b|\bebay\b|\baliexpress\b"
        ),
        "Akaryakıt ve Otomotiv": (
            r"\bakaryak[ıi]t\w*|\bbenzin\w*|\bmotorin\w*|\bdizel\w*|\blpg\b|\botogaz\w*|\bistasyon\w*|\botomotiv\w*"
            r"|\baraç\b|\boto\b|\bshell\b|\bopet\b|\bpetrol\s+ofisi\b|\bbp\b|\btotal\b|\btotalenergies\b"
            r"|\bpo\b|\btp\b|\bopet\s+fuchs\b|\botobak[ıi]m\w*|\blastik\w*|\bservis\b"
        ),
        "Teknoloji ve Elektronik": (
            r"\btekno\w*|\belektronik\w*|\bbilgisayar\w*|\btelefon\w*|\bcep\s+telefonu\w*|\btablet\w*"
            r"|\btroy\s+ma[gğ]aza\w*|\bgürgençler\b|\bteknosa\b|\bmediamarkt\b|\bvatan\s+bilgisayar\b"
            r"|\bapple\b|\bsamsung\b|\bbyfix\b|\beve\s+elektronik\b"
            # Verideki bilgisayar satıcıları: bunlar olmadan "Monster
            # Notebook'ta 12 Aya Varan Taksit" (3 banka) sektörsüz kalıyordu.
            r"|\bnotebook\w*|\blaptop\w*|\bitopya\b|\bcasper\b|\bxiaomi\b|\bmonster\b"
        ),
        "Giyim ve Aksesuar": (
            r"\bgiyim\w*|\btekstil\w*|\bkiyafet\w*|\bkonfeksiyon\w*|\bayakkab[ıi]\w*|\bçanta\w*|\baksesuar\w*"
            r"|\bsaat\b|\btak[ıi]\b|\bzarab|\bh&m\b|\blcw\b|\blc\s+waikiki\b|\bdefacto\b|\bmavi\b"
            r"|\bkoton\b|\bboyner\b|\byarg[ıi]\b|\bvakko\b|\bderimod\b|\bflo\b|\btergan\b"
        ),
        "Seyahat ve Turizm": (
            r"\bseyahat\w*|\bturizm\w*|\botel\w*|\bkonaklama\w*|\buçak\w*|\bbilet\w*|\bhavayolu\w*|\bthy\b"
            r"|\btürk\s+hava\s+yollar[ıi]\b|\bpegasus\b|\bajet\b|\bsunexpress\b|\bturna\b|\benuygun\b"
            r"|\bobilet\b|\betstur\b|\bjolly\b|\btur\b|\baraç\s+kiralama\w*|\brent\s+a\s+car\b"
        ),
        "Eğitim ve Kırtasiye": (
            r"\be[gğ]itim\w*|\bokul\w*|\bk[ıi]rtasiye\w*|\bokula\s+dönü[şs]\w*|\bnezih\b|\büniversite\w*"
            r"|\bkurs\w*|\bderse\w*|\bkitap\w*|\bkitabevi\w*|\bd&r\b|\bdr\b|\bbkm\s+kitap\b|\bdr\.com\.tr\b"
        ),
        # --- 27.08.2026'da EKLENEN üç sektör ---------------------------------
        # Katalogun %67'si "Genel / Sektör Bağımsız" kalıyordu; sınıfsız
        # kalanların içindeki en kalabalık üç küme buydu. Marka adları
        # doğrudan bu veri kümesindeki kampanya başlıklarından alındı.
        "Mobilya ve Ev": (
            r"\bmobilya\w*|\bev\s+tekstil\w*|\bbeyaz\s+e[şs]ya\w*|\bmutfak\s+e[şs]ya\w*"
            r"|\byap[ıi]\s+market\w*|\bdekorasyon\w*|\bnalbur\w*"
            r"|\bbellona\b|\bistikbal\b|\bmondi\b|\bdo[ğg]ta[şs]\b|\benza\s+home\b|\byata[şs]\b"
            r"|\bdivanev\b|\bkelebek\b|\bpuffy\b|\balfemo\b|\bkonfor\b|\bçetmen\b|\bevidea\b"
            r"|\bkoçta[şs]\b|\bdemird[öo]küm\b|\bvaillant\b|\bider\s+mobilya\b|\benglish\s+home\b"
            r"|\bschafer\b|\bdyson\b"
        ),
        "Sağlık": (
            r"\bsa[ğg]l[ıi]k\s+harcama\w*|\beczane\w*|\bhastane\w*|\bdi[şs]\s+hastane\w*"
            r"|\bpoliklinik\w*|\bmedikal\b|\boptik\b|\bmemorial\b|\brestoderm\b|\balpi\s+di[şs]\b"
            r"|\bmedical\s+park\b|\bacıbadem\b"
        ),
        "Restoran ve Yeme-İçme": (
            r"\brestoran\w*|\bkafe\w*|\bkahve\w*|\byemek\s+harcama\w*|\bcaf[eé]\b"
            r"|\byemeksepeti\b(?!\s+market)|\bgetir\s*yemek\b|\bespressolab\b|\bstarbucks\b"
            r"|\bkahve\s+dünyas[ıi]\b|\btatl[ıi]c[ıi]\w*"
        ),
    }
    
    skorlar: Dict[str, int] = {sektor: 0 for sektor in sektor_kurallari}
    en_iyi_eslesmeler: Dict[str, Optional[re.Match]] = {sektor: None for sektor in sektor_kurallari}
    
    for sektor, pattern in sektor_kurallari.items():
        regex_obj = re.compile(pattern, re.IGNORECASE)

        # Başlık kontrolü (Ağırlık: 3)
        baslik_eslesme = regex_obj.search(baslik)
        if baslik and baslik_eslesme:
            skorlar[sektor] += 3
            if en_iyi_eslesmeler[sektor] is None:
                en_iyi_eslesmeler[sektor] = baslik_eslesme

        # Metin kontrolü (Ağırlık: 1 x Her eşleşme, EN FAZLA 2)
        # ⚠️ Sınır şart: kampanya şartlar-koşullar metinleri kapsam listeleri
        # içeriyor ("havayolları, seyahat acenteleri, konaklama ile ilgili
        # harcamalarda 3 ay, elektronik eşya...") ve bu liste tekrar tekrar
        # eşleştiği için bilgisayar satıcısı kampanyalarını (ITOPYA, Casper)
        # "Seyahat ve Turizm" yapıyordu. Tavan, şablon metnin gerçek sinyali
        # ezmesini engelliyor.
        metin_eslesmeleri = list(regex_obj.finditer(islenen_metin))
        skorlar[sektor] += min(len(metin_eslesmeleri), _METIN_SKOR_TAVANI)

        if metin_eslesmeleri and en_iyi_eslesmeler[sektor] is None:
            en_iyi_eslesmeler[sektor] = metin_eslesmeleri[0]

    en_yuksek_skor = max(skorlar.values())

    # Tepe skorunu birden çok sektör paylaşıyorsa karar verilemez.
    tepe = [s for s, v in skorlar.items() if v == en_yuksek_skor]

    kazanan_sektor = None
    if en_yuksek_skor >= _ASGARI_SEKTOR_SKORU:
        if len(tepe) == 1:
            kazanan_sektor = tepe[0]
        else:
            # ⚠️ Beraberlik iki farklı sebepten olabilir:
            #  (a) Gövde şablonu birden çok sektörü eşit besliyor -> kanıt
            #      gerçekten çelişkili, "Genel" dürüst cevaptır.
            #  (b) BAŞLIK iki sektöre birden değiyor:
            #      "A101 Ekstra'da tüm cep telefonlarına 3 Taksit"
            #      "A101'lerde yapacağın kırtasiye harcamaların"
            #      Burada kampanyanın konusu belli; "Genel" demek bilgi kaybı.
            # Türkçe baş-sonda bir dildir: niteleyen önce, ASIL KONU sonda
            # gelir (mağaza adı önde, ürün kategorisi arkada). Bu yüzden
            # başlıkta EN SONDA eşleşen sektör seçiliyor.
            baslikta = [(s, en_iyi_eslesmeler[s].start())
                        for s in tepe
                        if baslik and en_iyi_eslesmeler.get(s) is not None
                        and en_iyi_eslesmeler[s].start() < len(baslik)]
            if baslikta:
                kazanan_sektor = max(baslikta, key=lambda x: x[1])[0]

    if kazanan_sektor:
        eslesme_obj = en_iyi_eslesmeler[kazanan_sektor]
        
        # Kural adını güvenli slug formatına dönüştür (örn: sektor_skorlama_market_ve_gida)
        kural_slug = re.sub(r'[^a-z0-9]', '_', kazanan_sektor.lower()).strip('_')
        
        if eslesme_obj:
            return {
                "sektor": _bulgu(
                    metin=islenen_metin,
                    eslesme=eslesme_obj,
                    deger=kazanan_sektor,
                    kural=f"sektor_skorlama_{kural_slug}",
                    guven=0.85,
                    birim="kategori"
                )
            }

    # Hiçbir sektöre uymuyorsa varsayılan durum
    return {
        "sektor": AlanBulgusu(
            deger="Genel / Sektör Bağımsız",
            ham_metin="",
            kural="sektor_varsayilan",
            guven=0.50,
            kanit_metni="",
            baslangic_konum=0,
            bitis_konum=0,
            birim="kategori"
        )
    }
# ============================================================
# KATEGORİ TESPİTİ
# ============================================================



import re
from typing import Dict, Any

# 1. Regex desenlerini kategori bazında TEK BİR pattern olarak derliyoruz (Performans ve Okunabilirlik)
KATEGORI_KURALLARI: list[tuple[str, re.Pattern]] = [
    (
        "Dijital / Anında Alışveriş Finansmanları",
        re.compile(
            r"\bmağazada\s*finansman|\bmagazada\s*finansman|\bbayide\s*finansman\b"
            r"|\bşimdi\s*al\b|\bsimdi\s*al\b|\bveresiye\b|\bdijital\s*tüketici"
            r"|\bdijital\s*tuketici|\bjet\s*finansman\b|\bhızlı\s*finansman"
            r"|\bhizli\s*finansman|\balışveriş\s*kredi|\balisveris\s*kredi",
            re.IGNORECASE,
        ),
    ),
    (
        "Bireysel / İhtiyaç Finansmanları",
        re.compile(
            r"\bihtiya[çc]\b|\beğitim\b|\begitim\b|\bokul\b|\böğrenci\b|\bogrenci\b"
            r"|\bsağlık\b|\bsaglik\b|\btedavi\b|\bhac\b|\bumre\b|\btatil\b|\bseyahat\b"
            r"|\bev\s*eşya|\bev\s*esya|\beyaş\b|\bteknoloji\b|\btelefon\b|\bcep\b"
            r"|\bdoğalgaz\b|\bdogalgaz\b|\btesisat\b|\benerji\s*dönüşüm|\benerji\s*donusum"
            r"|\bkarz[-_ ]?ı\s*hasen\b",
            re.IGNORECASE,
            ),
        ),
    (
        "Konut / Gayrimenkul Finansmanları",
        re.compile(
            r"\bkonut\b|\bev\s*(?:kredi|finansman)|\bmortgage\b|\bgayrimenkul\b"
            r"|\bişyeri\s*finansmanı\b|\barsa\b|\b2b\b|\b2-b\b|\bprefabrik\b"
            r"|\bkentsel\s*dönüşüm|\bkentsel\s*donusum|\bbina\s*tamamlama\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Taşıt Finansmanları",
        re.compile(
            r"\bta[şs][ıi]t\b|\bara[çc]\b|\bo?to\s*(?:kredi|finansman)"
            r"|\bmotosiklet\b|\bmotor\b|\btogg\b|\belektrikli\s*ara[çc]"
            r"|\bdeniz\s*ta[şs][ıi]t|\btekne\b|\bisiklet\b",
            re.IGNORECASE,
        ),
    ),
    
    (
        "Ticari & Kurumsal Finansmanlar",
        re.compile(
            r"\bticari\b|\bkurumsal\b|\bkobi\b|\bişletme\s*sermaye|\bisletme\s*sermaye"
            r"|\bsanayi\b|\bmakin[ae]\b|\bteçhizat\b|\btechizat\b|\bekipman\b"
            r"|\btar[ıi]m\b|\bçiftçi\b|\bciftci\b|\bsürdürülebilir\b|\bsurdurulebilir\b"
            r"|\byeşil\s*enerji\b|\byesil\s*enerji\b|\bges\b|\bgüneş\s*enerji|\bgunes\s*enerji"
            r"|\bdış\s*ticaret|\bdis\s*ticaret|\btedarikçi\s*finansman|\btedarikci\s*finansman"
            r"|\bleasing\b|\bkiralama\b",
            re.IGNORECASE,
        ),
    ),
]

VARSAYILAN_URUN_KATEGORISI = "Diğer"


def urun_kategori_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """
    Metinde geçen İLK ürün kategorisini tespit eder ve 
    tek bir AlanBulgusu nesnesi olarak döndürür.
    """
    metin_temiz = (metin or "").strip()
    if not metin_temiz:
        return {}

    for kategori_adi, desen in KATEGORI_KURALLARI:
        esles = desen.search(metin_temiz)
        if esles:
            return {
                "urun_kategori": _bulgu(
                    metin_temiz,
                    esles,
                    kategori_adi,
                    f"urun_kategori_{kategori_adi.lower()}",
                    guven=0.95,
                    birim="metin",
                )
            }

    return {}

# =============================================================================
# ODUL TİPİ VE ODUL METNİ ÇIKARICISI
# =============================================================================

_ODUL_TIPI_KALIPLARI = [
    ("Nakit Ödül", re.compile(r"\bnakit\s+(?:ödül|odul|iade)\b", re.IGNORECASE)),
    ("Puan/Bonus", re.compile(r"\b(?:puan|bonus|chip-para|worldpuan)\b", re.IGNORECASE)),
    ("Hediye Çeki", re.compile(r"\bhediye\s+çek\w*\b", re.IGNORECASE)),
    ("FX Dar Makas Avantajı", re.compile(r"\b(?:dar\s+makas|makas\s+avantajı|fx\s+avantajı)\b", re.IGNORECASE)),
    ("İndirim", re.compile(r"\b(?:indirim|iskonto)\b", re.IGNORECASE)),
]

def odul_tipi_ve_metni_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """
    Kampanyadaki ödül/avantaj tipini ve özet ödül metnini çıkarır.
    """
    bulgular: Dict[str, AlanBulgusu] = {}

    # 1. odul_tip tespiti
    for tip_adi, desen in _ODUL_TIPI_KALIPLARI:
        esles = desen.search(metin)
        if esles:
            bulgular["odul_tip"] = _bulgu(
                metin,
                esles,
                tip_adi,
                f"odul_tipi_{tip_adi.lower().replace(' ', '_')}",
                guven=0.96,
                birim="metin",
            )
            break

    # 2. odul_metni tespiti (Ödül veya avantajı özetleyen ana cümle)
    cumleler = re.split(r'(?<=[.!?])\s+', metin)
    for cumle in cumleler:
        cumle_temiz = cumle.strip()
        if re.search(r"\b(?:dar makas|makas avantajı|nakit ödül|hediye|puan|iade)\b", cumle_temiz, re.IGNORECASE):
            # Çok genel başlık cümleleri yerine somut oran/limit içeren cümleyi önceliklendir
            if re.search(r"\d|%", cumle_temiz):
                baslangic = metin.find(cumle_temiz)
                bitis = baslangic + len(cumle_temiz) if baslangic != -1 else None
                bulgular["odul_metni"] = AlanBulgusu(
                    deger=cumle_temiz,
                    ham_metin=cumle_temiz,
                    kural="odul_metni_ozet_cumle",
                    guven=0.92,
                    kanit_metni=cumle_temiz,
                    baslangic_konum=baslangic,
                    bitis_konum=bitis,
                    birim="metin",
                )
                break

    return bulgular


# =============================================================================
# KAZANÇ METNİ ÇIKARICISI
# =============================================================================

_KAZANC_IPUCLARI = re.compile(
    r"\b(?:kazanım|kazanabilir|kazanır|kazanın|kazanma|ödenir|aktarılacaktır|yararlanabilir|faydalanabilir|yararlanılabilmesi|faydalanılabilmesi)\b",
    re.IGNORECASE
)

_KAZANC_SART_IPUCLARI = re.compile(
    r"\b(?:şartı|durumunda|halinde|beklenir|dolduktan sonra|bakiyesinin|olması gerekmektedir|sağlaması|açılması gerekmektedir|kapsamında)\b",
    re.IGNORECASE
)

def kazanc_metni_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """
    Kampanyadaki kazanım şartını ve mekanizmasını içeren kritik cümleleri tespit eder.
    """
    cumleler = re.split(r'(?<=[.!?])\s+', metin)
    aday_cumleler = []

    for cumle in cumleler:
        cumle_temiz = cumle.strip()
        
        # Hem kazanım/faydalanma hem de koşul/gereksinim içeren cümleleri yakala
        if _KAZANC_IPUCLARI.search(cumle_temiz):
            if _KAZANC_SART_IPUCLARI.search(cumle_temiz) or "gün" in cumle_temiz.lower():
                aday_cumleler.append(cumle_temiz)

    if aday_cumleler:
        # Şart ve detay içeriği en yüksek olan uzun cümleyi seç
        en_iyi_cumle = max(aday_cumleler, key=len)
        
        baslangic = metin.find(en_iyi_cumle)
        bitis = baslangic + len(en_iyi_cumle) if baslangic != -1 else None

        return {
            "kazanc_metin": AlanBulgusu(
                deger=en_iyi_cumle,
                ham_metin=en_iyi_cumle,
                kural="cumle+kazanc_sarti_baglami",
                guven=0.95,
                kanit_metni=en_iyi_cumle,
                baslangic_konum=baslangic,
                bitis_konum=bitis,
                birim="metin",
            )
        }

    return {}


# =============================================================================
# 10. ANA GİRİŞ NOKTASI
# =============================================================================

def kurallarla_cikar(
    baslik: str,
    metin: str,
) -> Dict[str, AlanBulgusu]:
    """
    Başlık ve metinden yüksek kesinlikli alanları çıkarır.

    Yalnızca tespit edilen alanlar döndürülür.
    Hybrid katmanı bu çıktıyı kullanarak eksik alanlar için LLM çağırabilir.
    """
    tam_metin = f"{baslik or ''}. {metin or ''}".strip()

    bulgular: Dict[str, AlanBulgusu] = {}

    cikaricilar = (
        oranlari_cikar,
        vade_ve_taksit_cikar,
        tarihleri_cikar,
        masraf_cikar,
        hedef_kitle_cikar,
         #mgm_cikar,
        urun_kategori_cikar,
        mgm_detay_cikar,    # <-- YENİ EKLENDİ (5 kişi limiti ve MGM ödülleri için)
        odul_tipi_ve_metni_cikar,
        kazanc_metni_cikar,
    )

    for cikarici in cikaricilar:
        bulgular.update(cikarici(
            tam_metin
        ))

    # ⚠️ sektor_cikar YUKARIDAKİ listeden çıkarıldı: imzası
    # `sektor_cikar(metin, baslik="")` olduğu hâlde döngü tüm çıkarıcıları tek
    # argümanla çağırıyordu, yani başlık DAİMA boş geçiliyor ve fonksiyonun
    # kendi "Başlık kontrolü (Ağırlık: 3)" dalı hiç çalışmıyordu. Başlık artık
    # gerçekten aktarılıyor.
    bulgular.update(sektor_cikar(tam_metin, baslik or ""))
    # tutar_cikar da sektor_cikar gibi baslik farkindaligi istiyor:
    # basliktaki odul tutari, govdedeki kademe tablosuna yenilmemeli.
    bulgular.update(tutar_cikar(tam_metin, baslik or ""))

    bulgular.update(
        kategori_cikar(
            baslik or "",
            metin or "",
        )
    )

    return bulgular

 

# =============================================================================
# 11. SADE JSON'A DÖNÜŞTÜRME
# =============================================================================

def bulgulari_dict_yap(
    bulgular: Dict[str, AlanBulgusu],
) -> Dict[str, Any]:
    """
    AlanBulgusu nesnelerini JSON-uyumlu basit dict yapısına dönüştürür.
    """
    return {
        alan: {
            "deger": bulgu.deger,
            "ham_metin": bulgu.ham_metin,
            "kural": bulgu.kural,
            "yontem": bulgu.yontem,
            "guven": bulgu.guven,
            "kanit_metni": bulgu.kanit_metni,
            "baslangic_konum": bulgu.baslangic_konum,
            "bitis_konum": bulgu.bitis_konum,
            "birim": bulgu.birim,
        }
        for alan, bulgu in bulgular.items()
    }
