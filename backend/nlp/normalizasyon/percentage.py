# =============================================================================
# percentage.py — Yüzde/Oran Normalizasyonu (şartname 5.6)
# =============================================================================
# HEDEF: "%2,05" = "% 2.05" = "2.05 %" → 2.05
# Ek olarak sözel biçim: "yüzde 2,05" → 2.05
# =============================================================================

import re

# BURASI DEĞİŞTİ (normalization -> normalizasyon)
from backend.nlp.normalizasyon.money import sayi_ayikla

# ... (kodun geri kalanı aynı)
_YUZDE_DESENI = re.compile(
    r"""
    (?:%|yüzde|yuzde)\s*(?P<on>\d+(?:[.,]\d+)?)     # işaret/kelime ÖNDE
    |
    (?P<son>\d+(?:[.,]\d+)?)\s*%                     # işaret SONDA
    """,
    re.IGNORECASE | re.VERBOSE,
)

def yuzde_normalize(metin: str) -> float | None:
    """Metindeki İLK yüzde ifadesini float'a çevirir."""
    if not metin:
        return None

    esles = _YUZDE_DESENI.search(metin)
    if not esles:
        return None

    sayi_metni = esles.group("on") or esles.group("son")
    return sayi_ayikla(sayi_metni)