# =============================================================================
# urun_kurallari.py — ÜRÜN Sayfaları için Çapalı Alan Çıkarımı
# =============================================================================
import re
from typing import Dict, List, Optional, Tuple

from nlp.classification.campaign_classifier import siniflandir
from nlp.extraction.rule_based import AlanBulgusu
from nlp.normalization.percentage import yuzde_normalize

KATEGORI_TUR_ESLEME = {
    "konut-finansmanlari": "konut_finansmani",
    "arac-finansmanlari": "tasit_finansmani",
    "ihtiyac-finansmanlari": "ihtiyac_finansmani",
    "alisveris-finansmanlari": "finansman",
}


def urun_turu_belirle(kategori: Optional[str], baslik: str, metin: str) -> Optional[AlanBulgusu]:
    if kategori and kategori in KATEGORI_TUR_ESLEME:
        tur = KATEGORI_TUR_ESLEME[kategori]
        return AlanBulgusu(
            tur, f"URL kategorisi: {kategori}", f"urun_kategorisi:{kategori}", birim="metin"
        )
    
    sinif_sonuc = siniflandir(baslik, metin, llm_aktif=False)
    if sinif_sonuc and "hedef_kitle" in sinif_sonuc:
        bulgu = sinif_sonuc["hedef_kitle"]
        return bulgu if isinstance(bulgu, AlanBulgusu) else None
    return None


_CUMLE_AYRACI = re.compile(r"(?<!\d)\.(?:\s+|$)")


def _cumleler(metin: str) -> List[str]:
    return [c.strip() for c in _CUMLE_AYRACI.split(metin or "") if c.strip()]


_VADE_KALIPLARI = (
    re.compile(r"(\d{1,3})\s*ay[ae]?\s+kadar\s+vade", re.IGNORECASE),
    re.compile(r"(?:maksimum|azami|en\s+fazla)\s+(\d{1,3})\s*ay", re.IGNORECASE),
    re.compile(r"(\d{1,3})\s*ay\s+vade\s+ile", re.IGNORECASE),
    re.compile(r"vade(?:si|niz)?\s+(?:en\s+fazla\s+)?(\d{1,3})\s*ay", re.IGNORECASE),
)


def azami_vade_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    en_iyi: Optional[Tuple[int, str]] = None
    for cumle in _cumleler(metin):
        if cumle.rstrip().endswith("?"):
            continue
        for desen in _VADE_KALIPLARI:
            for esles in desen.finditer(cumle):
                ay = int(esles.group(1))
                if 0 < ay <= 600 and (en_iyi is None or ay > en_iyi[0]):
                    en_iyi = (ay, esles.group().strip())
    if en_iyi is None:
        return {}
    return {
        "max_vade_ay": AlanBulgusu(
            en_iyi[0], en_iyi[1], "urun_capa:azami_vade", birim="ay", kanit_metni=en_iyi[1]
        )
    }


_YUZDE_IFADESI = re.compile(r"(?:%\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%)")
_TAHSIS_ORANI = re.compile(
    r"tahsis\s+ücreti[^.]{0,120}?(%\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%)",
    re.IGNORECASE
)


def tahsis_orani_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    for esles in _TAHSIS_ORANI.finditer(metin or ""):
        deger = yuzde_normalize(esles.group(1))
        if deger is not None:
            f_deger = float(deger)
            if 0 < f_deger <= 10:
                return {
                    "tahsis_ucreti": AlanBulgusu(
                        f_deger, esles.group()[:200], "urun_capa:tahsis_orani", birim="yüzde", kanit_metni=esles.group()
                    )
                }
    return {}


_ORAN_TABLOSU_CAPASI = re.compile(
    r"(?:maksimum|azami|en\s+fazla)\s+finansman(?:\s+tutar[ıi]?)?\s+oran"
    r"|finansman\s+tutar[ıi]\s+oranlar[ıi]", re.IGNORECASE
)
_TABLO_PENCERESI = 400


def azami_finansman_orani_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    esles = _ORAN_TABLOSU_CAPASI.search(metin or "")
    if not esles:
        return {}
    pencere = metin[esles.end(): esles.end() + _TABLO_PENCERESI]
    oranlar: List[float] = []
    for y in _YUZDE_IFADESI.finditer(pencere):
        norm = yuzde_normalize(y.group())
        if norm is not None:
            f_val = float(norm)
            if 0 < f_val <= 100:
                oranlar.append(f_val)
    
    if not oranlar:
        return {}
    return {
        "kar_payi_orani": AlanBulgusu(
            max(oranlar), metin[esles.start(): esles.end() + 120],
            "urun_capa:azami_finansman_orani", birim="yüzde", kanit_metni=pencere
        )
    }


_MASRAF_CAPASI = re.compile(
    r"\b(?:tahsis\s+ücreti|dosya\s+masraf|ipotek\s+tesis|ekspertiz\s+ücret"
    r"|sigorta\s+(?:ücret|bedel)|masrafs[ıi]z|ücretsiz)", re.IGNORECASE
)


def masraf_bilgisi_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    cumleler = [c for c in _cumleler(metin) if _MASRAF_CAPASI.search(c)]
    if not cumleler:
        return {}
    ozet = ". ".join(cumleler[:3])[:500]
    return {
        "masraf_bilgisi": AlanBulgusu(
            ozet, ozet[:200], "urun_capa:masraf", birim="metin", kanit_metni=ozet
        )
    }


def urun_kurallarla_cikar(baslik: str, metin: str,
                          kategori: Optional[str] = None) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}
    bulgular.update(azami_vade_cikar(metin))
    bulgular.update(tahsis_orani_cikar(metin))
    bulgular.update(azami_finansman_orani_cikar(metin))
    bulgular.update(masraf_bilgisi_cikar(metin))
    
    tur = urun_turu_belirle(kategori, baslik, metin)
    if tur:
        bulgular["kampanya_turu"] = tur
    return bulgular