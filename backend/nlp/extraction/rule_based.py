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


from backend.nlp.normalizasyon.money import para_normalize
from backend.nlp.normalizasyon.date import tarih_normalize
from backend.nlp.normalizasyon.duration import vade_normalize
from backend.nlp.normalizasyon.percentage import yuzde_normalize

from backend.nlp.classification.campaign_classifier import siniflandir


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

def _pencere(
    metin: str,
    baslangic: int,
    bitis: int,
    genislik: int = 80,
) -> str:
    return metin[
        max(0, baslangic - genislik): min(len(metin), bitis + genislik)
    ].lower()


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

        elif any(k in pencere for k in _KARPAYI_ACIK):
            aday = _bulgu(
                metin,
                eslesme,
                float(deger),
                "yuzde+kar_paylasim_acik_baglami",
                guven=0.99,
                birim="percent",
            )
            bulgular["kar_payi_orani"] = _ilk_yuksek_guvenli(
                bulgular.get("kar_payi_orani"), aday
            )

        elif any(k in pencere for k in _GETIRI_IPUCLARI):
            # "oran" kelimesini tek başına sinyal olarak kullanmıyoruz.
            if not any(n in pencere for n in _KARPAYI_NEGATIF):
                aday = _bulgu(
                    metin,
                    eslesme,
                    float(deger),
                    "yuzde+getiri_baglami",
                    guven=0.88,
                    birim="percent",
                )
                bulgular["tahsis_ucreti"] = _ilk_yuksek_guvenli(
                    bulgular.get("tahsis_ucreti"), aday
                )

    return bulgular


# =============================================================================
# 2. VADE VE TAKSİT
# =============================================================================

_TAKSIT = re.compile(
    r"\b(\d+)\s*(?:ay|aya|ayın)?\s*(?:varan|kadar)?\s*taksit\b",
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

        sonrasi = metin[
            vade_bul.end(): min(len(metin), vade_bul.end() + 35)
        ].lower()

        oncesi = metin[
            max(0, vade_bul.start() - 35): vade_bul.start()
        ].lower()

        baglam = f"{oncesi} {sonrasi}"

        vade_mi = bool(_VADE_BAGLAMI.search(baglam))

        if not vade_mi:
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

_MIN_IPUCLARI = re.compile(
    r"\b(?:en\s+az|minimum|min\.?|asgari|en\s+düşük)\b",
    re.IGNORECASE,
)

_MAX_IPUCLARI = re.compile(
    r"\b(?:en\s+fazla|maksimum|max\.?|azami|kadar|üst sınır)\b",
    re.IGNORECASE,
)

_HARCAMA_IPUCLARI = re.compile(
    r"\b(?:harcama|harcamanız|harcamalarda|alışveriş|alışverişlerde|"
    r"harcama tutarı|harcama tutarınız)\b",
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
    r"\b(?:hediye|ödül|odul|çek|çekiniz|iade|bonus|fırsat|firsat)\b",
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

    return metin[sol + 1:sag].strip().lower()


def tutar_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """
    TL tutarlarını semantik bağlamlarına göre ayırır.
    """
    bulgular: Dict[str, AlanBulgusu] = {}

    for tutar_bul in _TUTAR.finditer(metin):
        deger = para_normalize(tutar_bul.group())
        if deger is None:
            continue

        baslangic, bitis = tutar_bul.start(), tutar_bul.end()
        cumle = _tutar_cumle(metin, baslangic, bitis)
        pencere = _pencere(metin, baslangic, bitis, 70)

        onceki = metin[max(0, baslangic - 25):baslangic].lower()
        sonraki = metin[bitis:min(len(metin), bitis + 35)].lower()

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
            aday = _bulgu(
                metin,
                tutar_bul,
                deger,
                "para+mgm_baglami",
                guven=0.94,
                birim="TL",
            )

            if "mgm" in cumle or "arkadaş" in cumle or "davet" in cumle:
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
                "para+puan_baglami",
                guven=0.97,
                birim="TL",
            )
            bulgular["puan_kazanc"] = _ilk_yuksek_guvenli(
                bulgular.get("puan_kazanc"), aday
            )
            continue

        # -------------------------------------------------------------
        # 3.4 Harcama eşiği
        # -------------------------------------------------------------
        if _HARCAMA_IPUCLARI.search(cumle):
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

            if _MAX_IPUCLARI.search(onceki) or _MAX_IPUCLARI.search(pencere):
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

        finansman_baglami = (
            _FINANSMAN_IPUCLARI.search(cumle)
            or _KREDI_IPUCLARI.search(cumle)
            or "taksit" in cumle.lower()
            or genel_limit_baglami
        )

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
            if _MAX_IPUCLARI.search(pencere) or genel_limit_baglami:
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
            aday = _bulgu(
                metin,
                tutar_bul,
                deger,
                "para+odul_baglami",
                guven=0.93,
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

            bulgular["baslangic_tarihi"] = _bulgu(
                metin, tarih_bul, bas_norm, "varsayilan_temizlenme_tarihi", guven=0.80, birim="tarih"
            )

            # Bitiş ile varsayılan başlangıç arasındaki süreyi hesapla
            bas_dt = _tarih_objesine_cevir(bas_norm)
            bit_dt = _tarih_objesine_cevir(bit)

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
    sektor_kurallari = {
        "Market ve Gıda": (
            r"\bmarket\b|\bg[ıi]da\b|\bs[üu]permarket\b|\bhipermarket\b|\bşarküteri\b|\bmanav\b|\bkasap\b"
            r"|\bmigros\b|\bcarrefour\b|\bcarrefoursa\b|\bbin\b|\ba101\b|\bşok\b|\bfile\b|\bmacrocenter\b"
            r"|\byemeksepeti\s+market\b|\bgetirmarket\b|\bgetir\s+büyük\b|\bistegelsin\b|\bavm\s+g[ıi]da\b"
        ),
        "E-Ticaret ve Pazaryerleri": (
            r"\be-?t[ıi]caret\b|\bpazaryer[ıi]\b|\bonline\s+al[ıi][şs]veri[şs]\b|\btrendyol\b|\bhepsiburada\b"
            r"|\bn11\b|\bamazon\b|\bçiçeksepeti\b|\bpazarama\b|\bidefix\b|\bbonanza\b|\bebay\b|\baliexpress\b"
        ),
        "Akaryakıt ve Otomotiv": (
            r"\bakaryak[ıi]t\b|\bbenzin\b|\bmotorin\b|\bdizel\b|\blpg\b|\botogaz\b|\bistasyon\b|\botomotiv\b"
            r"|\baraç\b|\boto\b|\bshell\b|\bopet\b|\bpetrol\s+ofisi\b|\bbp\b|\btotal\b|\btotalenergies\b"
            r"|\bpo\b|\btp\b|\bopet\s+fuchs\b|\botobak[ıi]m\b|\blastik\b|\bservis\b"
        ),
        "Teknoloji ve Elektronik": (
            r"\btekno\w*\b|\belektronik\b|\bbilgisayar\b|\btelefon\b|\bcep\s+telefonu\b|\btablet\b"
            r"|\btroy\s+ma[gğ]aza\w*\b|\bgürgençler\b|\bteknosa\b|\bmediamarkt\b|\bvatan\s+bilgisayar\b"
            r"|\bapple\b|\bsamsung\b|\bbyfix\b|\beve\s+elektronik\b"
        ),
        "Giyim ve Aksesuar": (
            r"\bgiyim\b|\btekstil\b|\bkiyafet\b|\bkonfeksiyon\b|\bayakkab[ıi]\b|\bçanta\b|\baksesuar\b"
            r"|\bsaat\b|\btak[ıi]\b|\bzarab|\bh&m\b|\blcw\b|\blc\s+waikiki\b|\bdefacto\b|\bmavi\b"
            r"|\bkoton\b|\bboyner\b|\byarg[ıi]\b|\bvakko\b|\bderimod\b|\bflo\b|\btergan\b"
        ),
        "Seyahat ve Turizm": (
            r"\bseyahat\b|\bturizm\b|\botel\b|\bkonaklama\b|\buçak\b|\bbilet\b|\bhavayolu\b|\bthy\b"
            r"|\btürk\s+hava\s+yollar[ıi]\b|\bpegasus\b|\bajet\b|\bsunexpress\b|\bturna\b|\benuygun\b"
            r"|\bobilet\b|\betstur\b|\bjolly\b|\btur\b|\baraç\s+kiralama\b|\brent\s+a\s+car\b"
        ),
        "Eğitim ve Kırtasiye": (
            r"\be[gğ]itim\b|\bokul\b|\bk[ıi]rtasiye\b|\bokula\s+dönü[şs]\b|\bnezih\b|\büniversite\b"
            r"|\bkurs\b|\bderse\w*\b|\bkitap\b|\bkitabevi\b|\bd&r\b|\bdr\b|\bbkm\s+kitap\b|\bdr\.com\.tr\b"
        )
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
        
        # Metin kontrolü (Ağırlık: 1 x Her eşleşme)
        metin_eslesmeleri = list(regex_obj.finditer(islenen_metin))
        skorlar[sektor] += len(metin_eslesmeleri)
        
        if metin_eslesmeleri and en_iyi_eslesmeler[sektor] is None:
            en_iyi_eslesmeler[sektor] = metin_eslesmeleri[0]
        
    en_yuksek_skor = max(skorlar.values())
    
    if en_yuksek_skor > 0:
        kazanan_sektor = max(skorlar, key=skorlar.get)
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
        tutar_cikar,
        tarihleri_cikar,
        masraf_cikar,
        hedef_kitle_cikar,
         #mgm_cikar,
        sektor_cikar,
        urun_kategori_cikar,
        mgm_detay_cikar,    # <-- YENİ EKLENDİ (5 kişi limiti ve MGM ödülleri için)
        odul_tipi_ve_metni_cikar,
        kazanc_metni_cikar,
    )

    for cikarici in cikaricilar:
        bulgular.update(cikarici(
            tam_metin
        ))

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
