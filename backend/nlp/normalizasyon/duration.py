# =============================================================================
# duration.py — Vade/Süre Normalizasyonu (şartname 5.6)
# =============================================================================
# HEDEF: Tüm vade ifadelerini AY cinsinden tam sayıya çevirmek.
#   "120 ay"        → 120
#   "10 yıl"        → 120
# =============================================================================

import re

# BURASI DEĞİŞTİ (normalization -> normalizasyon)
from backend.nlp.normalizasyon.money import sayi_ayikla

# ... (kodun geri kalanı aynı)
_VADE_DESENI = re.compile(
    r"""
    (?P<sayi>\d+(?:[.,]\d+)?)      # sayı: 120 | 1,5
    \s*
    (?P<birim>ay|yıl|yil|sene)     # birim kökü (ör. "ay", "yıl")
    [a-zçğıöşü]*                   # olası Türkçe ekler: -a, -lık, -e kadar...
    """,
    re.IGNORECASE | re.VERBOSE,
)

_AY_CARPANI = {"ay": 1, "yıl": 12, "yil": 12, "sene": 12}

def vade_normalize(metin: str) -> int | None:
    """Metindeki İLK vade ifadesini AY cinsinden tam sayıya çevirir."""
    if not metin:
        return None

    esles = _VADE_DESENI.search(metin)
    if not esles:
        return None

    sayi = sayi_ayikla(esles.group("sayi"))
    if sayi is None:
        return None

    carpan = _AY_CARPANI[esles.group("birim").lower()]
    return round(sayi * carpan)