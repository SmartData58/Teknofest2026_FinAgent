# --- Banka -> Desteklenen ürünler ---
BANKA_URUNLERI = {
    "kuveyt":          ["ihtiyac", "tasit", "konut"],
    "vakif":           ["ihtiyac", "konut"],              # taşıt yok
    "ziraat":          ["ihtiyac", "tasit", "konut"],
    "albaraka":        ["ihtiyac", "tasit", "konut"],
    "turkiye_finans":  ["ihtiyac", "tasit", "konut"],
    "emlak_katilim":   ["ihtiyac", "tasit", "konut"],
    "dunya_katilim":   ["ihtiyac", "tasit", "konut"],
}

# --- Taşıt Finansmanı'nda 800.000'in HESAPLANMAYACAĞI bankalar ---
# (bu bankalarda max finansman tutarı 400.000 ile sınırlı)
TASIT_800K_HESAPLANMAYAN_BANKALAR = {
    "dunya_katilim", "vakif", "albaraka", "ziraat"
}

# --- Ürün bazında (tutar, vade) kombinasyonları ---
def ihtiyac_kombinasyonlari():
    return [
        (200000, v) for v in (12, 24)
    ] + [
        (100000, v) for v in (12, 24, 36)
    ] + [
        (50000, v) for v in (12, 24, 36)
    ]

def konut_kombinasyonlari():
    return [
        (2000000, 120),
        (1000000, 120),
    ]

def tasit_kombinasyonlari(banka_key: str):
    kombinasyonlar = [(400000, v) for v in (24, 36)]
    if banka_key not in TASIT_800K_HESAPLANMAYAN_BANKALAR:
        kombinasyonlar.append((800000, 36))
    return kombinasyonlar


def get_kombinasyonlar(banka_key: str, urun: str):
    """Belirli bir banka + ürün için (tutar, vade) listesi döndürür."""
    if urun == "ihtiyac":
        return ihtiyac_kombinasyonlari()
    elif urun == "konut":
        return konut_kombinasyonlari()
    elif urun == "tasit":
        return tasit_kombinasyonlari(banka_key)
    else:
        raise ValueError(f"Bilinmeyen ürün: {urun}")


# --- Her ürün için MongoDB'ye çekilecek alanlar (referans amaçlı) ---
ALINACAK_ALANLAR = {
    "ihtiyac": ["finansman_tutari", "vade", "aylik_taksit_tutari",
                "geri_odenecek_toplam_tutar", "kar_orani", "tahsis_ucreti"],
    "konut":   ["finansman_tutari", "vade", "aylik_taksit_tutari",
                "geri_odenecek_toplam_tutar", "kar_orani_aylik", "tahsis_ucreti"],
    "tasit":   ["finansman_tutari", "vade", "aylik_taksit_tutari",
                "geri_odenecek_toplam_tutar", "kar_orani_aylik", "tahsis_ucreti"],
}