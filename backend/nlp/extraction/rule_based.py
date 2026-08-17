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
from typing import Dict, Optional, Any

from ..normalizasyon.money import para_normalize
from ..normalizasyon.date import tarih_normalize
from ..normalizasyon.duration import vade_normalize
from ..normalizasyon.percentage import yuzde_normalize


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


def oranlari_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """
    Yüzde ifadelerini bağlamına göre:
        - indirim_orani_yuzde
        - nakit_iade_yuzde
        - k_kar_paylasim_orani
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

        if any(k in pencere for k in _INDIRIM_IPUCLARI):
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
            bulgular["nakit_iade_yuzde"] = _ilk_yuksek_guvenli(
                bulgular.get("nakit_iade_yuzde"), aday
            )

        elif any(k in pencere for k in _KARPAYI_ACIK):
            aday = _bulgu(
                metin,
                eslesme,
                float(deger),
                "yuzde+kar_paylasim_acik_baglami",
                guven=0.99,
                birim="percent",
            )
            bulgular["k_kar_paylasim_orani"] = _ilk_yuksek_guvenli(
                bulgular.get("k_kar_paylasim_orani"), aday
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
                bulgular["k_kar_paylasim_orani"] = _ilk_yuksek_guvenli(
                    bulgular.get("k_kar_paylasim_orani"), aday
                )

    return bulgular


# =============================================================================
# 2. VADE VE TAKSİT
# =============================================================================

_VADE_ADAYI = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:ay|yıl|yil|sene)[a-zçğıöşü]*",
    re.IGNORECASE,
)

_TAKSIT = re.compile(
    r"\b(\d+)\s*(?:ay\s*)?taksit\b",
    re.IGNORECASE,
)

_VADE_BAGLAMI = re.compile(
    r"(?:vade|vadeli|vadeye|vadesi|kadar)",
    re.IGNORECASE,
)


def vade_ve_taksit_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}

    taksit_bul = _TAKSIT.search(metin)
    if taksit_bul:
        bulgular["taksit"] = _bulgu(
            metin,
            taksit_bul,
            int(taksit_bul.group(1)),
            "sayi+taksit",
            guven=0.99,
            birim="adet",
        )

    for vade_bul in _VADE_ADAYI.finditer(metin):
        ifade = vade_bul.group()
        sonrasi = metin[
            vade_bul.end(): min(len(metin), vade_bul.end() + 35)
        ].lower()

        oncesi = metin[
            max(0, vade_bul.start() - 35): vade_bul.start()
        ].lower()

        baglam = f"{oncesi} {sonrasi}"

        # "12 ay vadeye kadar", "36 aya kadar", "24 ay vade"
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

        bulgular["k_vade_ay"] = _ilk_yuksek_guvenli(
            bulgular.get("k_vade_ay"), aday
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

    Ayrımlar:
        - min_harcama_tl
        - maks_harcama_tl
        - k_finansman_tutari
        - min_finansman_tutari
        - maks_finansman_tutari
        - puan_kazanc
        - odul_tutari_tl
        - k_tahsis_ucreti
        - mgm_limit_tl
        - kisi_basi_kazanc
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
        # 3.1 MGM
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
            # Üyelik/abonelik gibi ücretleri finansman masrafından ayır.
            if not re.search(r"\b(?:üyelik|abonelik)\b", pencere):
                aday = _bulgu(
                    metin,
                    tutar_bul,
                    deger,
                    "para+masraf_baglami",
                    guven=0.94,
                    birim="TL",
                )
                bulgular["k_tahsis_ucreti"] = _ilk_yuksek_guvenli(
                    bulgular.get("k_tahsis_ucreti"), aday
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
                    "para+maks_harcama_baglami",
                    guven=0.92,
                    birim="TL",
                )
                bulgular["maks_harcama_tl"] = _ilk_yuksek_guvenli(
                    bulgular.get("maks_harcama_tl"), aday
                )
                continue

        # -------------------------------------------------------------
        # 3.5 Finansman / kredi
        # -------------------------------------------------------------
        finansman_baglami = (
            _FINANSMAN_IPUCLARI.search(cumle)
            or _KREDI_IPUCLARI.search(cumle)
        )

        if finansman_baglami and not _LIMIT_IPUCLARI.search(cumle):
            if _MIN_IPUCLARI.search(onceki) or re.search(
                r"\b(?:en az|minimum|asgari)\b.{0,20}"
                r"(?:finansman|kredi)",
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

            if _MAX_IPUCLARI.search(pencere):
                aday = _bulgu(
                    metin,
                    tutar_bul,
                    deger,
                    "para+maks_finansman_baglami",
                    guven=0.95,
                    birim="TL",
                )
                bulgular["maks_finansman_tutari"] = _ilk_yuksek_guvenli(
                    bulgular.get("maks_finansman_tutari"), aday
                )
                continue

            aday = _bulgu(
                metin,
                tutar_bul,
                deger,
                "para+finansman_baglami",
                guven=0.93,
                birim="TL",
            )
            bulgular["k_finansman_tutari"] = _ilk_yuksek_guvenli(
                bulgular.get("k_finansman_tutari"), aday
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

        bulgular["k_tahsis_ucreti"] = AlanBulgusu(
            deger=0.0,
            ham_metin=cumle,
            kural="masraf_yok_kalibi",
            guven=0.99,
            kanit_metni=cumle,
            birim="TL",
        )

        bulgular["k_masraf_bilgi"] = AlanBulgusu(
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
            bulgular["k_masraf_bilgi"] = AlanBulgusu(
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
            r"|\bmüşteri\s+ol(?:an|acak|up|mak)\b",
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
]


_HEDEF_DISLAMA = re.compile(
    r"yararlanamaz|katılamaz|dahil\s+değil|yararlanamazlar|"
    r"faydalanamaz",
    re.IGNORECASE,
)


def hedef_kitle_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """
    Öncelik:
        maaş müşterisi
        segment
        yeni müşteri
        mevcut müşteri
    """
    bulgular: Dict[str, AlanBulgusu] = {}

    for etiket, desen in _HEDEF_KALIPLARI:
        for esles in desen.finditer(metin):
            oncesi = metin[
                max(0, esles.start() - 35):esles.start()
            ].lower()

            sonrasi = metin[
                esles.end():min(len(metin), esles.end() + 150)
            ].lower()

            # "mevcut veya yeni müşteriler" gibi ifadelerde
            # yalnızca "yeni müşteri" eşleşmesini engelle.
            if etiket == "yeni_musteri" and (
                "mevcut veya" in oncesi
                or "mevcut ve" in oncesi
                or "yeniden" in oncesi
            ):
                continue

            if _HEDEF_DISLAMA.search(sonrasi):
                continue

            guven = {
                "maas_musterisi": 0.98,
                "segment": 0.95,
                "yeni_musteri": 0.98,
                "mevcut_musteri": 0.98,
            }[etiket]

            aday = _bulgu(
                metin,
                esles,
                etiket,
                f"hedef+{etiket}",
                guven=guven,
                birim="metin",
            )

            bulgular["hedef_kitle"] = _ilk_yuksek_guvenli(
                bulgular.get("hedef_kitle"), aday
            )

    return bulgular


# =============================================================================
# 7. MGM / ARKADAŞINI GETİR
# =============================================================================

_MGM_KALIBI = re.compile(
    r"arkadaşını\s+(?:davet\s+et|getir)"
    r"|arkadaşınızı\s+(?:davet\s+edin|getirin)"
    r"|arkadaşı\w*\s+getir\w*"
    r"|arkadaş\w*\s+davet\s+et\w*"
    r"|yakınını\s+davet\s+et\w*"
    r"|yakınınızı\s+davet\s+edin"
    r"|davet\s+et(?:tiğin|tiğiniz)?\s+arkadaş"
    r"|referans\s+(?:kod|link|bağlant)"
    r"|referansın\w*\s+ile"
    r"|getir\s+kazan",
    re.IGNORECASE,
)


def mgm_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    esles = _MGM_KALIBI.search(metin)

    if not esles:
        return {}

    return {
        "is_mgm": _bulgu(
            metin,
            esles,
            True,
            "mgm_kalibi",
            guven=0.99,
            birim="boolean",
        )
    }


# =============================================================================
# 8. KAMPANYA TÜRÜ
# =============================================================================

_KAMPANYA_TURU: tuple[tuple[str, str, re.Pattern], ...] = (
    # Ürün bazlı kampanyalar önce gelir.
    (
        "ihtiyac_finansmani_kampanyasi",
        "hepsi",
        re.compile(
            r"\bihtiya[çc]\s+(?:finansman|finansmanı|kredi)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "konut_finansmani_kampanyasi",
        "hepsi",
        re.compile(
            r"\b(?:konut|ev)\s+(?:finansman|finansmanı|kredi)\b"
            r"|\bmortgage\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tasit_finansmani_kampanyasi",
        "hepsi",
        re.compile(
            r"\b(?:ta[şs][ıi]t|ara[çc]|oto)\s+"
            r"(?:finansman|finansmanı|kredi)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "yatirim_urunleri_kampanyasi",
        "baslik",
        re.compile(
            r"\bgünlük\s+hesap\b"
            r"|\byatırım\s+hesab\w*\b"
            r"|\bkatılma\s+hesab\w*\b"
            r"|\bBES\b|\bemeklilik\s+plan\w*"
            r"|\baltın\s+hesab\w*|\bgümüş\s+hesab\w*"
            r"|\bdeğerli\s+maden\w*",
            re.IGNORECASE,
        ),
    ),
    (
        "kart_kampanyasi",
        "hepsi",
        re.compile(
            r"\bkredi\s+kart\w*\b"
            r"|\bbanka\s+kart\w*\b"
            r"|\bdebit\b"
            r"|\bTROY\b"
            r"|\bMastercard\b"
            r"|\bVisa\b"
            r"|\bQR\s+(?:ile\s+)?öde\b"
            r"|\bkart(?:la|lı|ınız|ınıza)\b"
            r"|\bworldpuan\b|\bchip[- ]?para\b"
            r"|\bparafpuan\b|\bbonus\b"
            r"|\bharcama(?:ya|larda|larınız)?\s+"
            r"(?:kazan|puan|iade)",
            re.IGNORECASE,
        ),
    ),
    (
        "yeni_musteri_kampanyasi",
        "baslik",
        re.compile(
            r"\byeni\s+.*müşteri\b"
            r"|\bmüşteri(?:si|miz)?\s+ol\b"
            r"|\bho[şs]\s*geldin\b"
            r"|\barkadaşını\s+(?:getir|davet)\b"
            r"|\byakınını\s+davet\b"
            r"|\bmüşteri\s+kazan\b"
            r"|\bmüşteri\s+kazan(?:dır|dıran)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "finansman_kampanyasi",
        "erken",
        re.compile(
            r"\bfinansman\w*\b|\bfinansmanlı\b",
            re.IGNORECASE,
        ),
    ),
)


def kategori_cikar(
    baslik: str,
    metin: str,
) -> Dict[str, AlanBulgusu]:
    """
    Kampanyanın temel ürün/aksiyon türünü çıkarır.

    Hedef kitleyi kampanya türünden ayırıyoruz:
        kampanya_turu = konut_finansmani_kampanyasi
        hedef_kitle   = yeni_musteri
    """
    birlesik = f"{baslik or ''} {metin or ''}"

    for kat_turu, kapsam, desen in _KAMPANYA_TURU:
        aranacak = (
            baslik if kapsam == "baslik" else birlesik
        ) or ""

        esles = desen.search(aranacak)

        if esles:
            return {
                "kampanya_turu": _bulgu(
                    birlesik,
                    esles,
                    kat_turu,
                    f"kampanya_turu_{kat_turu}",
                    guven=0.94,
                    birim="metin",
                )
            }

    return {}


# =============================================================================
# 9. ALT KATEGORİ
# =============================================================================

_ALT_KATEGORILER: tuple[tuple[str, re.Pattern], ...] = (
    (
        "Konut",
        re.compile(
            r"\bkonut\b|\bev\s+sahibi\b|\bkonut\s+finansmanı\b"
            r"|\bmortgage\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Taşıt",
        re.compile(
            r"\bta[şs][ıi]t\b|\bara[çc]\b|\botomobil\b|\boto\b"
            r"|\btaşıt\s+finansmanı\b",
            re.IGNORECASE,
        ),
    ),
    (
        "İhtiyaç",
        re.compile(
            r"\bihtiyaç\b|\bihtiyaç\s+finansmanı\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Ticari",
        re.compile(
            r"\bticari\b|\bKOBİ\b|\besnaf\b|\bşirket\b"
            r"|\bişletme\b|\bticari\s+finansman\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Birikim",
        re.compile(
            r"\bbirikim\b|\bkatılma\s+hesabı\b|\byatırım\s+hesabı\b"
            r"|\bmevduat\b|\bgetiri\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Cari/Katılma",
        re.compile(
            r"\bcari\s+hesap\b|\bkatılma\s+hesab\w*\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Kredi Kartı",
        re.compile(
            r"\bkredi\s+kart\w*\b|\bworldpuan\b|\bchip[- ]?para\b"
            r"|\bparafpuan\b|\bbonus\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Banka Kartı",
        re.compile(
            r"\bbanka\s+kart\w*\b|\bdebit\b|\bTROY\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Sermaye Piyasaları",
        re.compile(
            r"\bhisse\b|\btahvil\b|\bbono\b|\byatırım\s+fonu\b"
            r"|\bsukuk\b|\bsermaye\s+piyas\w*\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Gayrimenkul",
        re.compile(
            r"\bgayrimenkul\b|\barsa\b|\bkonut\s+projesi\b",
            re.IGNORECASE,
        ),
    ),
)


def alt_kategori_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    for kategori, desen in _ALT_KATEGORILER:
        esles = desen.search(metin)

        if esles:
            return {
                "alt_kategori": _bulgu(
                    metin,
                    esles,
                    kategori,
                    f"alt_kategori_{kategori.lower()}",
                    guven=0.92,
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
        mgm_cikar,
        alt_kategori_cikar,
    )

    for cikarici in cikaricilar:
        bulgular.update(cikarici(tam_metin))

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
