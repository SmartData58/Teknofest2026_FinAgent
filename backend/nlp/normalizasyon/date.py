# =============================================================================
# dates.py — Tarih Normalizasyonu (şartname 5.6)
# =============================================================================
# HEDEF: Türkçe tarih ifadelerini Python date nesnesine çevirmek.
#   "31 Aralık 2026"  → date(2026, 12, 31)
#   "31.12.2026"      → date(2026, 12, 31)
#   "31/12/2026"      → date(2026, 12, 31)
#   "2026-12-31"      → date(2026, 12, 31)  (ISO biçimi)
#
# YENİ ÖZELLİKLER:
#   - 2 haneli yıl desteği (örn. "31.12.26" → 2026-12-31)
#   - Metindeki TÜM tarihleri bulur ve EN GEÇ olanı döndürür.
#     Örn: "1.02.2026 ve 5.03.2026 arasında" → 2026-03-05
#
# NEDEN date NESNESİ? Metin olarak saklanan tarih karşılaştırılamaz
# ("31.12.2026" > "1.1.2026" metin karşılaştırmasında YANLIŞ sonuç verir).
# date nesnesi veritabanında DATE kolonuna yazılır, "hâlâ geçerli kampanyalar"
# sorgusu doğru çalışır.
#
# NEDEN HAZIR KÜTÜPHANE KULLANMADIK? dateparser gibi kütüphaneler var ama
# ağır bağımlılık getiriyor; banka kampanya metinlerindeki tarih çeşitliliği
# bu kalıpları geçmiyor. Az bağımlılık = on-prem kriterine (+%20) uyum.
# =============================================================================

import re
from datetime import date

# Türkçe ay adı → ay numarası. Hem tam ad hem yaygın 3 harfli kısaltma.
TURKCE_AYLAR = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "agustos": 8, "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11,
    "kasim": 11, "aralık": 12, "aralik": 12,
    "oca": 1, "şub": 2, "mar": 3, "nis": 4, "may": 5, "haz": 6,
    "tem": 7, "ağu": 8, "eyl": 9, "eki": 10, "kas": 11, "ara": 12,
}

# Kalıp 1: "31 Aralık 2026" (gün + Türkçe ay adı + yıl)
_SOZEL = re.compile(r"(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})", re.IGNORECASE)

# Kalıp 2: "2026-12-31" (ISO 8601)
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

# Yıl kısmı artık 2 veya 4 haneli olabilir ("26" veya "2026").
# Kalıp 3: "31.12.2026" veya "31/12/2026" (gün.ay.yıl — Türkçe sıralama!)
_RAKAMSAL = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})")


def _yil_duzelt(yil_str: str) -> int:
    """
    2 haneli yılı 4 haneliye çevirir.
    Eşik: 50-99 → 1900'lü, 00-49 → 2000'li.
    """
    yil = int(yil_str)
    if len(yil_str) == 2:
        return 1900 + yil if yil >= 50 else 2000 + yil
    return yil


def tarih_normalize(metin: str) -> date | None:
    """
    Metindeki TÜM geçerli tarihleri bulur ve bunlardan EN GEÇ olanını döndürür.
    Hiç tarih bulamazsa None döner.

    Örnekler:
    >>> tarih_normalize("Kampanya 1.02.2026 ve 5.03.2026 arasında geçerlidir")
    datetime.date(2026, 3, 5)

    >>> tarih_normalize("son gün 31/12/26!")
    datetime.date(2026, 12, 31)

    >>> tarih_normalize("2026-12-31")
    datetime.date(2026, 12, 31)

    >>> tarih_normalize("31 Aralık 2026")
    datetime.date(2026, 12, 31)

    Geçersiz tarihler (örn. 31 Şubat) otomatik olarak elenir.
    """
    if not metin:
        return None

    bulunanlar = []

    # 1. Sözel tarihleri tara
    for esles in _SOZEL.finditer(metin):
        gun, ay_adi, yil = esles.groups()
        ay = TURKCE_AYLAR.get(ay_adi.lower())
        if ay:
            try:
                bulunanlar.append(date(int(yil), ay, int(gun)))
            except ValueError:
                pass  # geçersiz gün/ay kombinasyonu

    # 2. ISO formatını tara (yıl-ay-gün)
    for esles in _ISO.finditer(metin):
        yil, ay, gun = esles.groups()
        try:
            bulunanlar.append(date(int(yil), int(ay), int(gun)))
        except ValueError:
            pass

    # 3. Rakamsal formatları tara (gün.ay.yıl veya gün/ay/yıl veya gün-ay-yıl)
    #    Yıl 2 veya 4 haneli olabilir.
    for esles in _RAKAMSAL.finditer(metin):
        gun, ay, yil_str = esles.groups()
        yil = _yil_duzelt(yil_str)
        try:
            bulunanlar.append(date(yil, int(ay), int(gun)))
        except ValueError:
            pass

    # En geç tarihi döndür, yoksa None
    return max(bulunanlar) if bulunanlar else None
