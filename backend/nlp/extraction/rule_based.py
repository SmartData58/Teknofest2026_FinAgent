import re
from dataclasses import dataclass
from typing import Any

from ..normalizasyon import date, duration, money, percentage


@dataclass
class AlanBulgusu:
    deger: Any              # Normalize edilmiş değer (float, int, str, list)
    ham_metin: str          # Metindeki orijinal ham ifade
    kural: str              # Tetiklenen kural adı
    yontem: str = "regex"   # Jüri izlenebilirliği için yöntem adı
    guven: float = 1.0      # Kural tabanlı çıkarım güven skoru
    kanit_metni: str = ""   # Cümle içi kanıt metni
    baslangic_konum: int | None = None
    bitis_konum: int | None = None
    birim: str = "metin"    # ["percent", "TL", "ay", "adet", "metin", "boolean"]


def _pencere(metin: str, baslangic: int, bitis: int, genislik: int = 60) -> str:
    """Eşleşmenin çevresinden ±genislik karakterlik bağlam penceresi keser."""
    return metin[max(0, baslangic - genislik): bitis + genislik].lower()


# -----------------------------------------------------------------------------
# 1. ORANLAR: Kâr payı, faiz, indirim ve cashback
# -----------------------------------------------------------------------------
_YUZDE = re.compile(r"(?:%|yüzde)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%", re.IGNORECASE)

_INDIRIM_IPUCLARI = ("indirim", "iskonto", "ucuz", "fiyat düşüşü")
_KARPAYI_IPUCLARI = ("kâr payı", "kar payı", "faiz", "oran", "maliyet")
_KARPAYI_NEGATIF = ("iade", "ödül", "odul", "kazan", "mil", "puan", "bonus", "çekiliş", "komisyon", "cashback")


def oranlari_cikar(metin: str) -> dict[str, AlanBulgusu]:
    sonuclar: dict[str, AlanBulgusu] = {}

    for find_yuzde in _YUZDE.finditer(metin):
        start, end = find_yuzde.start(), find_yuzde.end()
        raw_str = find_yuzde.group()
        pencere_get = _pencere(metin, start, end)

        yuzde_val = percentage.yuzde_normalize(raw_str)
        if yuzde_val is None:
            continue

        if any(kelime in pencere_get for kelime in _INDIRIM_IPUCLARI):
            sonuclar.setdefault(
                "indirim_orani",
                AlanBulgusu(
                    deger=yuzde_val,
                    ham_metin=raw_str,
                    kural="yuzde+indirim_baglami",
                    kanit_metni=pencere_get.strip(),
                    baslangic_konum=start,
                    bitis_konum=end,
                    birim="percent"
                )
            )
        elif any(kelime in pencere_get for kelime in _KARPAYI_IPUCLARI):
            if not any(kn in pencere_get for kn in _KARPAYI_NEGATIF):
                sonuclar.setdefault(
                    "kar_orani",
                    AlanBulgusu(
                        deger=yuzde_val,
                        ham_metin=raw_str,
                        kural="yuzde+oran_baglami",
                        kanit_metni=pencere_get.strip(),
                        baslangic_konum=start,
                        bitis_konum=end,
                        birim="percent"
                    )
                )

    return sonuclar


# -----------------------------------------------------------------------------
# 2. VADE VE TAKSİT ÇIKARIMI
# -----------------------------------------------------------------------------
_VADE_ADAYI = re.compile(r"\d+(?:[.,]\d+)?\s*(?:ay|yıl|yil|sene)[a-zçğıöşü]*", re.IGNORECASE)
_TAKSIT = re.compile(r"(\d+)\s*(?:ay\s*)?taksit", re.IGNORECASE)


def vade_ve_taksit_cikar(metin: str) -> dict[str, AlanBulgusu]:
    sonuclar: dict[str, AlanBulgusu] = {}

    # Taksit Sayısı Yakalama
    taksit_match = _TAKSIT.search(metin)
    if taksit_match:
        taksit_sayisi = int(taksit_match.group(1))
        sonuclar["taksit_sayisi"] = AlanBulgusu(
            deger=taksit_sayisi,
            ham_metin=taksit_match.group(),
            kural="sayi+taksit",
            kanit_metni=_pencere(metin, taksit_match.start(), taksit_match.end()),
            baslangic_konum=taksit_match.start(),
            bitis_konum=taksit_match.end(),
            birim="adet"
        )

    # Vade Ay Yakalama
    for vade_iter in _VADE_ADAYI.finditer(metin):
        ifade = vade_iter.group()
        start, end = vade_iter.start(), vade_iter.end()
        sonrasi = metin[end: end + 25].lower().strip()

        if "vade" in sonrasi or sonrasi.startswith("kadar") or "aylık" in ifade.lower():
            deger = duration.vade_normalize(ifade)
            if deger is not None:
                sonuclar["vade"] = AlanBulgusu(
                    deger=deger,
                    ham_metin=ifade,
                    kural="sayi+vade_baglami",
                    kanit_metni=_pencere(metin, start, end),
                    baslangic_konum=start,
                    bitis_konum=end,
                    birim="ay"
                )
                break

    return sonuclar


# -----------------------------------------------------------------------------
# 3. PARASAL DEĞERLER (Finansman Tutarı, Ödül, Puan, Min Harcama)
# -----------------------------------------------------------------------------
_PARA_DESENI = re.compile(
    r"(?:\b\d{1,3}(?:\.\d{3})*|\b\d+)(?:[.,]\d+)?\s*(?:TL|tl|₺|bin|milyon)",
    re.IGNORECASE
)


def para_tutarlari_cikar(metin: str) -> dict[str, AlanBulgusu]:
    sonuclar: dict[str, AlanBulgusu] = {}

    for match in _PARA_DESENI.finditer(metin):
        start, end = match.start(), match.end()
        raw_str = match.group()
        pencere = _pencere(metin, start, end, genislik=50)

        tutari_val = money.para_normalize(raw_str)
        if tutari_val is None:
            continue

        # Finansman / Kredi Tutarı
        if any(k in pencere for k in ("kredi", "finansman", "kadar", "limit", "kullandırıl")):
            sonuclar.setdefault(
                "finansman_tutari",
                AlanBulgusu(
                    deger=tutari_val,
                    ham_metin=raw_str,
                    kural="para+finansman_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=start,
                    bitis_konum=end,
                    birim="TL"
                )
            )

        # Minimum Harcama Koşulu
        elif any(k in pencere for k in ("üzeri", "uzeri", "harcama", "alışveriş", "alisveris", "harcamaya")):
            sonuclar.setdefault(
                "minimum_harcama",
                AlanBulgusu(
                    deger=tutari_val,
                    ham_metin=raw_str,
                    kural="para+min_harcama_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=start,
                    bitis_konum=end,
                    birim="TL"
                )
            )

        # Puan / Worldpuan / Chip-Para
        elif any(k in pencere for k in ("puan", "worldpuan", "chip", "bonus")):
            sonuclar.setdefault(
                "puan_tutari",
                AlanBulgusu(
                    deger=tutari_val,
                    ham_metin=raw_str,
                    kural="para+puan_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=start,
                    bitis_konum=end,
                    birim="TL"
                )
            )

        # Ödül / Nakit İade
        elif any(k in pencere for k in ("ödül", "odul", "iade", "kazan", "hediye", "nakit")):
            sonuclar.setdefault(
                "odul_tutari",
                AlanBulgusu(
                    deger=tutari_val,
                    ham_metin=raw_str,
                    kural="para+odul_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=start,
                    bitis_konum=end,
                    birim="TL"
                )
            )

    return sonuclar


# -----------------------------------------------------------------------------
# 4. TARİHLER
# -----------------------------------------------------------------------------
_TARIH_ARALIGI = re.compile(r"(\d{1,2}[./]\d{1,2}[./]\d{4})\s*-\s*(\d{1,2}[./]\d{1,2}[./]\d{4})")
_BITIS_TARIHI = re.compile(
    r"((?:\d{1,2}\s+[a-zçğıöşü]+\s+\d{4}|\d{1,2}[./]\d{1,2}[./]\d{4}))"
    r"[a-z' ]{0,15}kadar",
    re.IGNORECASE
)


def tarihleri_cikar(metin: str) -> dict[str, AlanBulgusu]:
    bulgular: dict[str, AlanBulgusu] = {}

    aralik_match = _TARIH_ARALIGI.search(metin)
    if aralik_match:
        baslangic = date.tarih_normalize(aralik_match.group(1))
        bitis = date.tarih_normalize(aralik_match.group(2))

        if baslangic:
            bulgular["baslangic_tarihi"] = AlanBulgusu(
                deger=baslangic, ham_metin=aralik_match.group(1), kural="tarih_araligi_baslangic"
            )
        if bitis:
            bulgular["bitis_tarihi"] = AlanBulgusu(
                deger=bitis, ham_metin=aralik_match.group(2), kural="tarih_araligi_bitis"
            )
        return bulgular

    bitis_match = _BITIS_TARIHI.search(metin)
    if bitis_match:
        bitis = date.tarih_normalize(bitis_match.group(1))
        if bitis:
            bulgular["bitis_tarihi"] = AlanBulgusu(
                deger=bitis, ham_metin=bitis_match.group(1), kural="tarih_bitis_kalibi"
            )

    return bulgular


# -----------------------------------------------------------------------------
# 5. MASRAF, TAHSİS VE ÜCRETSİZ İŞLEMLER
# -----------------------------------------------------------------------------
_MASRAF_YOK = re.compile(
    r"[^.!?]*(?:masraf\w*\s+al[ıi]nmamaktad[ıi]r|masrafs[ıi]z|ücret\w*\s+al[ıi]nmamaktad[ıi]r|tahsis\s+ücret\w*\s+yok)[^.!?]*[.!?]?",
    re.IGNORECASE
)


def masraf_cikar(metin: str) -> dict[str, AlanBulgusu]:
    esles = _MASRAF_YOK.search(metin)
    if esles:
        cumle = esles.group().strip()
        return {
            "tahsis_ucreti": AlanBulgusu(
                deger=0.0, ham_metin=cumle, kural="masraf_yok_kalibi", birim="TL"
            ),
            "masraf_bilgisi": AlanBulgusu(
                deger=cumle, ham_metin=cumle, kural="masraf_yok_kalibi"
            )
        }
    return {}


# -----------------------------------------------------------------------------
# 6. HEDEF KİTLE VE İŞARETLER (Erteleme, MGM, Vade Farksız)
# -----------------------------------------------------------------------------
_HEDEF_KALIPLARI = [
    ("maas_musterisi", re.compile(r"maaş\s+müşteri\w*|maaş[ıi]n[ıi]\s+taş[ıi]yan", re.IGNORECASE)),
    ("yeni_musteri", re.compile(r"yeni\s+müşteri\w*|müşteri\s+ol(?:an|acak|up)\w*", re.IGNORECASE)),
    ("emekli", re.compile(r"emekli\w*", re.IGNORECASE)),
    ("kobi_esnaf", re.compile(r"esnaf|çiftçi|KOBİ|işletme\s+sahi\w*", re.IGNORECASE)),
]


def hedef_kitle_ve_isaretler_cikar(metin: str) -> dict[str, AlanBulgusu]:
    bulgular: dict[str, AlanBulgusu] = {}

    # Hedef Kitle
    for etiket, desen in _HEDEF_KALIPLARI:
        esles = desen.search(metin)
        if esles:
            bulgular["hedef_kitle"] = AlanBulgusu(
                deger=[etiket], ham_metin=esles.group(), kural=f"hedef+{etiket}"
            )
            break

    # Taksit Erteleme
    if re.search(r"erteleme|ertelene|sonra\s+öde", metin, re.IGNORECASE):
        bulgular["taksit_erteleme"] = AlanBulgusu(
            deger=True, ham_metin="taksit erteleme", kural="erteleme_kalibi", birim="boolean"
        )

    # Arkadaşını Getir (MGM)
    if re.search(r"davet\s+et|arkadaşı|getir\s+kazan", metin, re.IGNORECASE):
        bulgular["is_mgm"] = AlanBulgusu(
            deger=True, ham_metin="arkadaşını getir", kural="mgm_kalibi", birim="boolean"
        )

    # Vade Farksız / Sıfır Kâr Oranı
    if re.search(r"vade\s+farksız|0\s*kâr\s*payı|%0\s*faiz", metin, re.IGNORECASE):
        bulgular["vade_farksiz"] = AlanBulgusu(
            deger=True, ham_metin="vade farksız", kural="vade_farksiz_kalibi", birim="boolean"
        )

    return bulgular


# -----------------------------------------------------------------------------
# 7. KATEGORİLEŞTİRME VE ÖZELLİK TÜRÜ
# -----------------------------------------------------------------------------
_KATEGORI_HARITASI = [
    ("tasit_finansmani", re.compile(r"taşıt|araç|otomobil|motosiklet", re.IGNORECASE)),
    ("konut_finansmani", re.compile(r"konut|ev\s+al|gayrimenkul", re.IGNORECASE)),
    ("ihtiyac_finansmani", re.compile(r"ihtiyaç|bireysel|nakit|finansman", re.IGNORECASE)),
    ("egitim", re.compile(r"eğitim|okul|üniversite|kolej", re.IGNORECASE)),
    ("saglik", re.compile(r"sağlık|hastane|eczane", re.IGNORECASE)),
    ("seyahat_turizm", re.compile(r"seyahat|otel|uçak|turizm|bilet", re.IGNORECASE)),
    ("gida_restoran", re.compile(r"gıda|restoran|market|yeme\s+içme", re.IGNORECASE)),
]


def kategori_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    birlesik = f"{baslik} {metin}"
    for kat_kodu, desen in _KATEGORI_HARITASI:
        if desen.search(birlesik):
            return {
                "alt_kategori": AlanBulgusu(
                    deger=kat_kodu, ham_metin=kat_kodu, kural="kategori_regex_haritasi"
                ),
                "ana_kategori": AlanBulgusu(
                    deger="Finansman" if "finansmani" in kat_kodu else "Sektörel Ödül",
                    ham_metin=kat_kodu,
                    kural="kategori_regex_haritasi"
                )
            }
    return {}


# -----------------------------------------------------------------------------
# ANA GİRİŞ NOKTASI
# -----------------------------------------------------------------------------
def kurallarla_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    """
    Başlık ve metinden tüm alanları yüksek kesinlikli kurallarla çıkarır.
    Yalnızca tespit edilen alanları döndürür. Eksik kalan alanlar hybrid.py
    içinde belirlenip sadece o eksikler için LLM çağrısı yapılır.
    """
    tam_metin = f"{baslik or ''} . {metin or ''}"

    bulgular: dict[str, AlanBulgusu] = {}

    # Çıkarıcıları sırayla çalıştırıp birleştir
    bulgular.update(oranlari_cikar(tam_metin))
    bulgular.update(vade_ve_taksit_cikar(tam_metin))
    bulgular.update(para_tutarlari_cikar(tam_metin))
    bulgular.update(tarihleri_cikar(tam_metin))
    bulgular.update(masraf_cikar(tam_metin))
    bulgular.update(hedef_kitle_ve_isaretler_cikar(tam_metin))
    bulgular.update(kategori_cikar(baslik or "", metin or ""))

    return bulgular