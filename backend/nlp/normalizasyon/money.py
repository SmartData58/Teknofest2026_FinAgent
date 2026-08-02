# =============================================================================
# money.py — Para Tutarı Normalizasyonu (şartname 5.6)
# =============================================================================
# HEDEF: "500 TL" = "500₺" = "500 Türk Lirası" → 500.0
#        "50.000 TL" → 50000.0   |   "1.250,50 TL" → 1250.50
#        "5 bin TL" → 5000.0     |   "1,5 milyon TL" → 1500000.0
#
# TÜRKÇE SAYI BİÇİMİ PROBLEMİ
# -----------------------------------------------
# Türkçede NOKTA binlik ayracı, VİRGÜL ondalık ayracıdır (İngilizcenin tersi):
#   1. Hem nokta hem virgül varsa → nokta binlik, virgül ondalık ("1.250,50")
#   2. Yalnız virgül varsa        → virgül ondalıktır ("2,05")
#   3. Yalnız nokta varsa:
#      a. Noktadan sonra TAM 3 hane ve öncesinde 1-3 hane → binlik ("50.000")
#      b. Aksi hâlde → ondalık ("2.05")
# =============================================================================

import re

CARPANLAR = {
    "bin": 1_000,
    "milyon": 1_000_000,
    "milyar": 1_000_000_000,
}

_PARA_BIRIMLERI = r"(?:TL\b|₺|TRY\b|Türk\s+Liras[ıi]|lira\b)"
_SAYI = r"\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?|\d+(?:[.,]\d+)?"

def sayi_ayikla(metin: str) -> float | None:
    """Türkçe/İngilizce karışık biçimli bir sayı metnini float'a çevirir."""
    if not metin:
        return None
    s = metin.strip().replace(" ", "")

    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        if re.fullmatch(r"\d{1,3}(?:,000)+", s):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif "." in s:
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
            s = s.replace(".", "")

    try:
        return float(s)
    except ValueError:
        return None

def para_normalize(metin: str) -> float | None:
    """Metindeki İLK para tutarını TL cinsinden float olarak döndürür."""
    if not metin:
        return None

    desen_a = re.compile(
        rf"({_SAYI})\s*(bin|milyon|milyar)?\s*{_PARA_BIRIMLERI}",
        re.IGNORECASE,
    )
    desen_b = re.compile(rf"{_PARA_BIRIMLERI}\s*({_SAYI})", re.IGNORECASE)

    esles = desen_a.search(metin)
    if esles:
        sayi = sayi_ayikla(esles.group(1))
        if sayi is None:
            return None
        carpan_kelime = (esles.group(2) or "").lower()
        return sayi * CARPANLAR.get(carpan_kelime, 1)

    esles = desen_b.search(metin)
    if esles:
        return sayi_ayikla(esles.group(1))

    return None