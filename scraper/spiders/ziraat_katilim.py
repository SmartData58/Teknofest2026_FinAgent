import os
import re
import sys
from pathlib import Path
from collections import Counter

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


PROJE_KOK = Path(__file__).resolve().parent.parent.parent

if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))

from scraper.base_scraper import TabanScraper


# ============================================================
# PROJE YOLU
# ============================================================



# ============================================================
# SABİTLER
# ============================================================

TABAN_URL = os.getenv("URL_SPIDER_ZIRAATKATILIM", "https://www.ziraatkatilim.com.tr")


# ============================================================
# KAMPANYA KATEGORİLERİ
# ============================================================

KATEGORI_SAYFALARI = {
    "akaryakit": "Akaryakıt",
    "beyaz-esya-ve-ev-aletleri": "Beyaz Eşya ve Ev Aletleri",
    "diger-kampanyalar": "Diğer Kampanyalar",
    "e-ticaret": "E-Ticaret",
    "egitim-kitap-ve-kirtasiye": "Eğitim, Kitap ve Kırtasiye",
    "elektronik-ve-telekomunikasyon": "Elektronik ve Telekomünikasyon",
    "genel-kampanyalar": "Genel Kampanyalar",
    "giyim-ve-aksesuar": "Giyim ve Aksesuar",
    "hobi-ve-oyuncak": "Hobi ve Oyuncak",
    "kuyum-optik-ve-saat": "Kuyum, Optik ve Saat",
    "market-ve-gida": "Market ve Gıda",
    "mobilya-ve-dekorasyon": "Mobilya ve Dekorasyon",
    "turizm-ve-seyahat": "Turizm ve Seyahat",
    "yapi-sektoru-ve-iklimlendirme": "Yapı Sektörü ve İklimlendirme",
}


# ============================================================
# KAMPANYA URL
# ============================================================

DETAY_DESENI = re.compile(
    r"^/kart-kampanyalari/[a-z0-9-]+/?$",
    re.IGNORECASE
)


# ============================================================
# ÜRÜNLER / BİREYSEL FİNANSMANLAR
# ============================================================

URUN_LISTE_URL = (
    f"{TABAN_URL}/bireysel/finansman-urunleri"
)


URUN_LINK_DESENI = re.compile(
    r"^/bireysel/finansman-urunleri/"
    r"[a-z0-9-]+"
    r"(?:/[a-z0-9-]+)?/?$",
    re.IGNORECASE
)


GECERSIZ_URUN_BASLIKLARI = {
    "finansman ürünleri",
    "finansman ürünleri ve hizmetler",
    "bireysel",
    "finansman",
}


# ============================================================
# TARİH
# ============================================================

AYLAR = (
    "Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
    "Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
)


TARIH_YOK = "Belirtilmemiş"


# ------------------------------------------------------------
# 10-07-2025 - 31-08-2026
# ------------------------------------------------------------

TARIH_ARALIGI_SAYISAL = re.compile(
    r"""
    \b
    \d{1,2}
    [./-]
    \d{1,2}
    [./-]
    \d{4}
    \s*
    [-–—]
    \s*
    \d{1,2}
    [./-]
    \d{1,2}
    [./-]
    \d{4}
    \b
    """,
    re.VERBOSE
)


# ------------------------------------------------------------
# 01 Ocak 2026 - 31 Aralık 2026
# ------------------------------------------------------------

TARIH_ARALIGI_TAM = re.compile(
    rf"""
    \b
    \d{{1,2}}
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    \s*
    [-–—]
    \s*
    \d{{1,2}}
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# 8 Mayıs - 30 Kasım 2026
# ------------------------------------------------------------

TARIH_ARALIGI_ILK_YILSIZ = re.compile(
    rf"""
    \b
    \d{{1,2}}
    \s+
    (?:{AYLAR})
    \s*
    [-–—]
    \s*
    \d{{1,2}}
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# 31.08.2026
# ------------------------------------------------------------

TARIH_TEK_SAYISAL = re.compile(
    r"""
    \b
    \d{1,2}
    [./-]
    \d{1,2}
    [./-]
    \d{4}
    \b
    """,
    re.VERBOSE
)


# ------------------------------------------------------------
# 31 Ağustos 2026
# ------------------------------------------------------------

TARIH_TEK_YAZILI = re.compile(
    rf"""
    \b
    \d{{1,2}}
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ============================================================
# METİN NORMALİZE
# ============================================================

def normalize_metin(metin: str) -> str:
    if not metin:
        return ""

    return " ".join(
        metin
        .replace("\xa0", " ")
        .split()
    ).strip()


# ============================================================
# SAYFAYI PAYLAŞ SONRASINI KES
# ============================================================

def sayfayi_paylas_sonrasini_kes(
    metin: str
) -> str:
    """
    'SAYFAYI PAYLAŞ' ve sonrasındaki tüm metni atar.

    Örnek:

        ... Kampanya Koşulları ...
        SAYFAYI PAYLAŞ
        Diğer Kampanyalar
        ...
        Son Gün 31.08.2026

    çıktısı:

        ... Kampanya Koşulları ...
    """

    if not metin:
        return ""

    temiz = re.split(
        r"SAYFAYI\s+PAYLAŞ",
        metin,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]

    return normalize_metin(
        temiz
    )


# ============================================================
# SAYFAYI PAYLAŞ'I HTML'DE TEMİZLE
# ============================================================

def html_sayfayi_paylas_sonrasini_temizle(
    icerik
):
    """
    HTML ağacında SAYFAYI PAYLAŞ sonrasında kalan
    kardeş içerikleri temizlemeye çalışır.

    Bu işlem ham_metin'in temiz olması için ek güvenliktir.
    """

    if icerik is None:
        return

    bulunan_textler = list(
        icerik.find_all(
            string=re.compile(
                r"SAYFAYI\s+PAYLAŞ",
                re.IGNORECASE
            )
        )
    )

    for text_node in bulunan_textler:

        parent = text_node.parent

        if parent is None:
            continue

        # ----------------------------------------------------
        # Aynı text node içindeki SAYFAYI PAYLAŞ sonrasını kes
        # ----------------------------------------------------

        text = str(
            text_node
        )

        match = re.search(
            r"SAYFAYI\s+PAYLAŞ",
            text,
            re.IGNORECASE
        )

        if match:

            onceki = text[
                :match.start()
            ]

            if onceki.strip():

                text_node.replace_with(
                    onceki
                )

            else:

                try:
                    text_node.extract()
                except Exception:
                    pass

        # ----------------------------------------------------
        # Parent'ın sonrasındaki siblingleri temizle
        # ----------------------------------------------------

        try:

            current = parent

            # Fazla yukarı çıkmamak için sınırlı
            # sayıda parent kontrolü.
            for _ in range(4):

                if (
                    current is None
                    or current.parent is None
                ):
                    break

                current = current.parent

                # Çok büyük ana container'a çıkma
                current_text = normalize_metin(
                    current.get_text(
                        " ",
                        strip=True
                    )
                )

                if len(current_text) > 15000:
                    break

            # Text node'un bulunduğu parent'ın kardeşlerini
            # kaldırmak için önce uygun parent'a dön.
            hedef = parent

            for sibling in list(
                hedef.find_next_siblings()
            ):

                try:
                    sibling.decompose()
                except Exception:
                    pass

        except Exception:
            pass


# ============================================================
# TARİH ARALIĞI BUL
# ============================================================

def ilk_tarih_araligini_bul(
    metin: str
) -> str | None:

    if not metin:
        return None

    temiz = normalize_metin(
        metin
    )

    for desen in (
        TARIH_ARALIGI_SAYISAL,
        TARIH_ARALIGI_TAM,
        TARIH_ARALIGI_ILK_YILSIZ,
    ):

        match = desen.search(
            temiz
        )

        if match:
            return match.group(
                0
            ).strip()

    return None


# ============================================================
# TEK TARİH BUL
# ============================================================

def ilk_tek_tarihi_bul(
    metin: str
) -> str | None:

    if not metin:
        return None

    temiz = normalize_metin(
        metin
    )

    for desen in (
        TARIH_TEK_SAYISAL,
        TARIH_TEK_YAZILI,
    ):

        match = desen.search(
            temiz
        )

        if match:
            return match.group(
                0
            ).strip()

    return None


# ============================================================
# KAMPANYA TARİHİNİ BUL
# ============================================================

def tarih_metnini_bul(
    soup,
    icerik
) -> str | None:
    """
    ANA kampanyanın tarihini bulur.

    Öncelik:

    1. Kampanya Dönemi
    2. Kampanya Tarihleri
    3. Başlangıç/Bitiş Tarihi
    4. Kontrollü tarih alanı
    5. Son olarak yalnızca tarih ARALIĞI fallback'i

    ÖNEMLİ:
    'SAYFAYI PAYLAŞ' sonrasına kesinlikle bakılmaz.
    """

    if icerik is None:
        return None

    # ========================================================
    # ÖNCE TEMİZ KOPYA METNİ OLUŞTUR
    # ========================================================

    tam_metin = normalize_metin(
        icerik.get_text(
            " ",
            strip=True
        )
    )

    tam_metin = sayfayi_paylas_sonrasini_kes(
        tam_metin
    )

    if not tam_metin:
        return None


    # ========================================================
    # 1. KAMPANYA DÖNEMİ
    # ========================================================

    kampanya_donemi_pattern = re.compile(
        r"""
        Kampanya
        \s+
        Dönemi
        \s*:?
        \s*
        (?P<tarih>.*?)
        (?:
            Sektör
            |
            Kampanya\s+Koşulları
            |
            Kampanya\s+Koşulları:
            |
            Kampanya\s+Koşullari
            |
            Kampanya\s+Kosullari
        )
        """,
        re.IGNORECASE | re.VERBOSE
    )

    match = kampanya_donemi_pattern.search(
        tam_metin
    )


    if match:

        deger = normalize_metin(
            match.group(
                "tarih"
            )
        )


        tarih = (
            ilk_tarih_araligini_bul(
                deger
            )
        )

        if tarih:
            return tarih


        tarih = (
            ilk_tek_tarihi_bul(
                deger
            )
        )

        if tarih:
            return tarih


    # --------------------------------------------------------
    # Bazı sayfalarda "Kampanya Dönemi" sonrasında
    # doğrudan tarih geliyor ve "Sektör" daha sonra geliyor.
    # --------------------------------------------------------

    match = re.search(
        r"""
        Kampanya
        \s+
        Dönemi
        \s*:?
        \s*
        (
            \d{1,2}[./-]\d{1,2}[./-]\d{4}
            \s*[-–—]\s*
            \d{1,2}[./-]\d{1,2}[./-]\d{4}
        )
        """,
        tam_metin,
        re.IGNORECASE | re.VERBOSE
    )

    if match:

        return match.group(
            1
        ).strip()


    # Yazılı tarih aralığı
    match = re.search(
        rf"""
        Kampanya
        \s+
        Dönemi
        \s*:?
        \s*
        (
            \d{{1,2}}
            \s+
            (?:{AYLAR})
            (?:\s+\d{{4}})?
            \s*[-–—]\s*
            \d{{1,2}}
            \s+
            (?:{AYLAR})
            \s+
            \d{{4}}
        )
        """,
        tam_metin,
        re.IGNORECASE | re.VERBOSE
    )

    if match:

        return match.group(
            1
        ).strip()


    # ========================================================
    # 2. KAMPANYA TARİHLERİ / KAMPANYA TARİHİ
    # ========================================================

    for etiket in (
        "Kampanya Tarihleri",
        "Kampanya Tarihi",
        "Geçerlilik Tarihi",
        "Başlangıç Tarihi",
        "Bitiş Tarihi",
    ):

        pattern = re.compile(
            re.escape(etiket)
            + r"\s*:?\s*"
            + r"(.{0,150})",
            re.IGNORECASE
        )

        match = pattern.search(
            tam_metin
        )

        if not match:
            continue

        deger = normalize_metin(
            match.group(1)
        )


        tarih = (
            ilk_tarih_araligini_bul(
                deger
            )
        )

        if tarih:
            return tarih


        tarih = (
            ilk_tek_tarihi_bul(
                deger
            )
        )

        if tarih:
            return tarih


    # ========================================================
    # 3. ÖZEL TARİH HTML ALANLARI
    # ========================================================

    tarih_selectorleri = (
        "[class*='campaign-date'], "
        "[class*='campaign-period'], "
        "[class*='kampanya-tarih'], "
        "[class*='kampanya-donem'], "
        "[class*='date'], "
        "[class*='Date']"
    )

    try:

        for alan in icerik.select(
            tarih_selectorleri
        ):

            metin = normalize_metin(
                alan.get_text(
                    " ",
                    strip=True
                )
            )

            metin = sayfayi_paylas_sonrasini_kes(
                metin
            )


            if not metin:
                continue


            # "Son Gün" tek başına varsa kullanma.
            if (
                "Son Gün" in metin
                and
                "Kampanya Dönemi" not in metin
                and
                "Kampanya Tarihi" not in metin
            ):

                continue


            tarih = (
                ilk_tarih_araligini_bul(
                    metin
                )
            )

            if tarih:
                return tarih

    except Exception:
        pass


    # ========================================================
    # 4. <B> / <STRONG>
    # ========================================================

    for etiket in icerik.find_all(
        ["b", "strong"]
    ):

        metin = normalize_metin(
            etiket.get_text(
                " ",
                strip=True
            )
        )

        metin = sayfayi_paylas_sonrasini_kes(
            metin
        )


        if not metin:
            continue


        # "Son Gün" alanlarını fallback olarak kullanma.
        if re.search(
            r"Son\s+Gün",
            metin,
            re.IGNORECASE
        ):
            continue


        tarih = (
            ilk_tarih_araligini_bul(
                metin
            )
        )

        if tarih:
            return tarih


    # ========================================================
    # 5. SON FALLBACK
    # ========================================================
    #
    # Burada sadece TARİH ARALIĞI aranır.
    #
    # Tek tarih aramıyoruz.
    # Böylece:
    #
    # Son Gün 31.08.2026
    #
    # gibi başka kampanyaların tarihi alınamaz.
    # ========================================================

    tarih = (
        ilk_tarih_araligini_bul(
            tam_metin
        )
    )

    if tarih:
        return tarih


    return None


# ============================================================
# ZİRAAT KATILIM SPIDER
# ============================================================

class ZiraatKatilimSpider(
    TabanScraper
):

    banka_kodu = "ziraat_katilim"


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    def kampanyalari_topla(
        self
    ) -> list[dict]:

        kayitlar = []

        url_kategori_haritasi = {}

        suresi_gecmis_urller = set()


        # ====================================================
        # TÜM KATEGORİLER
        # ====================================================

        for kategori_slug, kategori_adi in KATEGORI_SAYFALARI.items():

            liste_url = (
                f"{TABAN_URL}/kampanyalar/"
                f"{kategori_slug}"
            )


            print(
                f"  Liste sayfası: "
                f"{liste_url}"
            )


            soup = self.getir(
                liste_url
            )


            if soup is None:
                continue


            for a in soup.select(
                "a[href]"
            ):

                href = (
                    a.get(
                        "href",
                        ""
                    )
                    .strip()
                )


                if not href:
                    continue


                # ------------------------------------------------
                # KAMPANYA LINKI (GÜNCEL & ARŞİV)
                # ------------------------------------------------

                temiz_href = (
                    href
                    .split("?")[0]
                    .split("#")[0]
                    .replace(
                        TABAN_URL,
                        ""
                    )
                    .rstrip("/")
                )

                if "IsArchived=true" in href:
                    suresi_gecmis_urller.add(
                        TABAN_URL
                        + temiz_href
                    )

                if not DETAY_DESENI.match(
                    temiz_href
                ):
                    continue

                tam_url = (
                    TABAN_URL
                    + temiz_href
                )

                url_kategori_haritasi.setdefault(
                    tam_url,
                    kategori_adi
                )


        print(
            f"\n  {len(url_kategori_haritasi)} "
            f"tekil kampanya linki bulundu"
        )


        print(
            f"  {len(suresi_gecmis_urller)} "
            f"tekil arşivlenmiş kampanya linki bulundu"
        )


        # ====================================================
        # DETAYLAR
        # ====================================================

        for url in sorted(
            url_kategori_haritasi
        ):

            if url in suresi_gecmis_urller:
                print(
                    "    SÜRESİ GEÇMİŞ "
                    "(arşiv işaretli), "
                    f"işleniyor: {url}"
                )


            kategori = (
                url_kategori_haritasi[
                    url
                ]
            )


            print(
                f"  Detay taranıyor: "
                f"{url}"
            )


            soup = self.getir(
                url
            )


            if soup is None:
                continue


            h1 = soup.select_one(
                "h1"
            )


            icerik = (
                soup.select_one(
                    ".field--name-body"
                )
                or
                soup.select_one(
                    "article"
                )
                or
                soup.select_one(
                    "main"
                )
            )


            if (
                h1 is None
                or
                icerik is None
            ):

                print(
                    f"    YAPI UYUŞMADI, "
                    f"atlandı: {url}"
                )

                continue


            # =================================================
            # HTML GÜRÜLTÜ TEMİZLE
            # =================================================

            try:

                for gurultu in icerik.select(
                    ".related, "
                    ".similar, "
                    ".recommended, "
                    ".recommended-campaigns, "
                    ".related-campaigns, "
                    "[class*='related'], "
                    "[class*='similar'], "
                    "[class*='recommended'], "
                    "[class*='ilgin']"
                ):

                    try:
                        gurultu.decompose()
                    except Exception:
                        pass

            except Exception:
                pass


            # =================================================
            # TARİHİ BUL
            # =================================================

            tarih_metni = (
                tarih_metnini_bul(
                    soup,
                    icerik
                )
            )


            if not tarih_metni:

                tarih_metni = TARIH_YOK


            # =================================================
            # HAM METİN
            # =================================================

            ham_metin = (
                self.metin_temizle(
                    icerik
                )
            )


            # =================================================
            # EN ÖNEMLİ TEMİZLİK
            #
            # SAYFAYI PAYLAŞ VE SONRASI YOK
            # =================================================

            ham_metin = (
                sayfayi_paylas_sonrasini_kes(
                    ham_metin
                )
            )


            # =================================================
            # KAYIT
            # =================================================

            kayit = {
                "banka": self.banka_kodu,
                "url": url,
                "baslik": self.metin_temizle(
                    h1
                ),
                "ham_metin": ham_metin,
                "kategori": kategori,
                "tarih_metni": tarih_metni,
            }


            kayitlar.append(
                kayit
            )


            print(
                f"    OK [{kategori}]: "
                f"{kayit['baslik'][:55]} "
                f"| Tarih: {tarih_metni}"
            )


        return kayitlar


    # ========================================================
    # ÜRÜN ADAYLARINI BUL
    # ========================================================

    def _urun_adaylarini_topla(
        self
    ) -> set[str]:

        ziyaret_edilen = set()

        kuyruk = [
            URUN_LISTE_URL
        ]

        adaylar = set()


        while kuyruk:

            sayfa_url = (
                kuyruk.pop(0)
            )


            if sayfa_url in ziyaret_edilen:
                continue


            ziyaret_edilen.add(
                sayfa_url
            )


            print(
                f"  Finansman sayfası "
                f"taranıyor: "
                f"{sayfa_url}"
            )


            soup = self.getir(
                sayfa_url
            )


            if soup is None:
                continue


            for a in soup.select(
                "a[href]"
            ):

                href = (
                    a.get(
                        "href",
                        ""
                    )
                    .strip()
                    .split("?")[0]
                    .split("#")[0]
                    .replace(
                        TABAN_URL,
                        ""
                    )
                    .rstrip("/")
                )


                if not href:
                    continue


                if not URUN_LINK_DESENI.match(
                    href
                ):
                    continue


                if (
                    href
                    == "/bireysel/finansman-urunleri"
                ):
                    continue


                tam_url = (
                    TABAN_URL
                    + href
                )


                adaylar.add(
                    tam_url
                )


                # ------------------------------------------------
                # Kategori olabilecek tek segmentli sayfaları
                # ayrıca tara.
                # ------------------------------------------------

                parcalar = (
                    href
                    .strip("/")
                    .split("/")
                )


                if (
                    len(parcalar) == 3
                    and
                    tam_url not in ziyaret_edilen
                ):

                    kuyruk.append(
                        tam_url
                    )


        return adaylar


    # ========================================================
    # ÜRÜN ALT LİNK SAYISI
    # ========================================================

    def _alt_urun_sayisini_bul(
        self,
        url: str,
        icerik
    ) -> int:

        mevcut_yol = (
            url
            .replace(
                TABAN_URL,
                ""
            )
            .rstrip("/")
        )


        sayi = 0


        for a in icerik.select(
            "a[href]"
        ):

            href = (
                a.get(
                    "href",
                    ""
                )
                .strip()
                .split("?")[0]
                .split("#")[0]
                .replace(
                    TABAN_URL,
                    ""
                )
                .rstrip("/")
            )


            if not href:
                continue


            if not URUN_LINK_DESENI.match(
                href
            ):
                continue


            if href == mevcut_yol:
                continue


            sayi += 1


        return sayi


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    def urunleri_topla(
        self
    ) -> list[dict]:

        kayitlar = []


        urun_adaylari = (
            self._urun_adaylarini_topla()
        )


        print(
            f"\n  Toplam "
            f"{len(urun_adaylari)} "
            f"aday finansman/kategori "
            f"linki bulundu."
        )


        for url in sorted(
            urun_adaylari
        ):

            print(
                f"  Ürün/kategori kontrol ediliyor: "
                f"{url}"
            )


            soup = self.getir(
                url
            )


            if soup is None:
                continue


            h1 = soup.select_one(
                "h1"
            )


            icerik = (
                soup.select_one(
                    ".field--name-body"
                )
                or
                soup.select_one(
                    "article"
                )
                or
                soup.select_one(
                    "main"
                )
            )


            if (
                h1 is None
                or
                icerik is None
            ):

                print(
                    f"    YAPI UYUŞMADI, "
                    f"atlandı: {url}"
                )

                continue


            # =================================================
            # BAŞLIK
            # =================================================

            baslik = self.metin_temizle(
                h1
            )


            if not baslik:

                print(
                    f"    Boş başlık, "
                    f"atlandı: {url}"
                )

                continue


            if (
                baslik.lower()
                in {
                    x.lower()
                    for x in
                    GECERSIZ_URUN_BASLIKLARI
                }
            ):

                print(
                    f"    Kategori/liste sayfası, "
                    f"atlandı: {url}"
                )

                continue


            # =================================================
            # ÜRÜN İÇERİK GÜRÜLTÜSÜ
            # =================================================

            try:

                for gurultu in icerik.select(
                    ".related, "
                    ".similar, "
                    ".recommended, "
                    ".recommended-campaigns, "
                    ".related-campaigns, "
                    "[class*='related'], "
                    "[class*='similar'], "
                    "[class*='recommended'], "
                    "[class*='ilgin']"
                ):

                    try:
                        gurultu.decompose()
                    except Exception:
                        pass

            except Exception:
                pass


            # =================================================
            # HAM METİN
            # =================================================

            ham_metin = self.metin_temizle(
                icerik
            )


            if len(
                ham_metin
            ) < 30:

                print(
                    f"    İçerik çok kısa, "
                    f"kategori/liste olabilir: "
                    f"{url}"
                )

                continue


            # =================================================
            # KATEGORİ SAYFASI KONTROLÜ
            # =================================================

            mevcut_yol = (
                url
                .replace(
                    TABAN_URL,
                    ""
                )
                .rstrip("/")
            )


            yol_parcalari = (
                mevcut_yol
                .strip("/")
                .split("/")
            )


            alt_urun_sayisi = (
                self._alt_urun_sayisini_bul(
                    url,
                    icerik
                )
            )


            # Tek segmentli kategori sayfalarında
            # alt ürünler varsa kategori olarak atla.
            if (
                len(yol_parcalari) == 3
                and
                alt_urun_sayisi > 0
            ):

                print(
                    f"    Kategori sayfası "
                    f"(altında "
                    f"{alt_urun_sayisi} ürün var), "
                    f"atlandı: {url}"
                )

                continue


            # =================================================
            # KATEGORİ
            # =================================================

            kalan = url.replace(
                f"{TABAN_URL}/bireysel/finansman-urunleri/",
                ""
            )


            urun_yol = (
                kalan
                .split("/")
            )


            kategori = (
                urun_yol[0]
                if len(urun_yol) > 1
                else None
            )


            # =================================================
            # ÜRÜN TARİHİ
            # =================================================

            tarih_metni = (
                tarih_metnini_bul(
                    soup,
                    icerik
                )
            )


            if not tarih_metni:

                tarih_metni = TARIH_YOK


            # =================================================
            # KAYIT
            # =================================================

            kayit = {
                "banka": self.banka_kodu,
                "url": url,
                "baslik": baslik,
                "ham_metin": ham_metin,
                "kategori": kategori,
                "tarih_metni": tarih_metni,
            }


            kayitlar.append(
                kayit
            )


            print(
                f"    OK [{kategori}]: "
                f"{baslik[:55]} "
                f"| Tarih: {tarih_metni}"
            )


        return kayitlar


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    spider = (
        ZiraatKatilimSpider()
    )


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    print(
        "Ziraat Katılım Spider "
        "(Kampanyalar) çalıştırılıyor..."
    )


    kampanya_kayitlari = (
        spider.kampanyalari_topla()
    )


    spider.kaydet(
        kampanya_kayitlari
    )


    spider.kaydet_mongoDB(
        kampanya_kayitlari,
        "ziraat_katilim"
    )


    # ========================================================
    # KAMPANYA ÖZETİ
    # ========================================================

    kampanya_ozet = Counter(
        k["kategori"]
        for k in kampanya_kayitlari
    )


    print(
        "\nKategori bazında dağılım:"
    )


    for kategori, sayi in sorted(
        kampanya_ozet.items()
    ):

        print(
            f"  {kategori}: {sayi}"
        )


    # ========================================================
    # TARİHSİZ KAMPANYALAR
    # ========================================================

    kampanya_tarihsiz = [
        k
        for k in kampanya_kayitlari
        if k["tarih_metni"] == TARIH_YOK
    ]


    print(
        f"\n"
        f"{len(kampanya_tarihsiz)} "
        f"kampanyada ana tarih bulunamadı."
    )


    if kampanya_tarihsiz:

        with open(
            "ziraat_katilim_tarih_bulunamayanlar.txt",
            "w",
            encoding="utf-8"
        ) as f:

            for k in kampanya_tarihsiz:

                print(
                    f"  - {k['url']}"
                )

                f.write(
                    f"URL: {k['url']}\n"
                )

                f.write(
                    f"BAŞLIK: {k['baslik']}\n"
                )

                f.write(
                    f"KATEGORİ: {k['kategori']}\n"
                )

                f.write(
                    f"HAM METİN:\n"
                    f"{k['ham_metin']}\n"
                )

                f.write(
                    "\n"
                    + "=" * 80
                    + "\n\n"
                )


        print(
            "Tarihi bulunamayan kampanya "
            "detayları "
            "'ziraat_katilim_tarih_bulunamayanlar.txt' "
            "dosyasına yazıldı."
        )


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    print(
        "\nZiraat Katılım Spider "
        "(Bireysel Finansman Ürünleri) "
        "çalıştırılıyor..."
    )


    urun_verileri = (
        spider.urunleri_topla()
    )


    spider.kaydet_mongoDB(
        urun_verileri,
        koleksiyon_adi="ziraat_katilim_ürün"
    )


    # ========================================================
    # ÜRÜN ÖZETİ
    # ========================================================

    urun_ozet = Counter(
        u["kategori"]
        for u in urun_verileri
    )


    print(
        "\nÜrün kategori bazında dağılım:"
    )


    for kategori, sayi in sorted(
        urun_ozet.items(),
        key=lambda x: (
            x[0] is None,
            x[0] or ""
        )
    ):

        print(
            f"  {kategori}: {sayi}"
        )


    # ========================================================
    # TARİHSİZ ÜRÜNLER
    # ========================================================

    urun_tarihsiz = [
        u
        for u in urun_verileri
        if u["tarih_metni"] == TARIH_YOK
    ]


    print(
        f"\n"
        f"{len(urun_tarihsiz)} "
        f"üründe tarih bulunamadı."
    )


    for u in urun_tarihsiz:

        print(
            f"  - "
            f"{u['baslik']} "
            f"| {u['url']}"
        )


    print(
        "\nZiraat Katılım Spider işlemi tamamlandı."
    )