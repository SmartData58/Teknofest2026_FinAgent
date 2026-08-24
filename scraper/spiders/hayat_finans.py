import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup


# ============================================================
# PROJE YOLU
# ============================================================

PROJE_KOK = Path(__file__).resolve().parent.parent.parent

if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))


from scraper.base_scraper import TabanScraper


# ============================================================
# SABİTLER
# ============================================================

TABAN_URL = "https://hayatfinans.com.tr"

LISTE_URL = f"{TABAN_URL}/kampanyalar"

KREDI_LISTE_URL = f"{TABAN_URL}/krediler"


# ============================================================
# KAMPANYA URL DESENİ
# ============================================================

DETAY_DESENI = re.compile(
    r"^/kampanyalar/[a-z0-9-]+/?$",
    re.IGNORECASE
)


# ============================================================
# ÜRÜN URL DESENİ
# ============================================================
#
# Hayat Finans'ın "Krediler" bölümündeki ürünler farklı
# URL segmentlerinde bulunabiliyor.
#
# Bu nedenle yalnızca krediler sayfasından bulunan gerçek
# ürün linklerini kullanıyoruz.
# ============================================================

URUN_URL_DESENLERI = [
    re.compile(
        r"^/krediler/[a-z0-9-]+/?$",
        re.IGNORECASE
    ),

    re.compile(
        r"^/finansmanlar/[a-z0-9-]+/?$",
        re.IGNORECASE
    ),
]


# ============================================================
# BİLİNEN HAYAT FİNANS KREDİ ÜRÜNLERİ
# ============================================================
#
# Güncel /krediler sayfasında bulunan 3 ürün:
#
# 1. Bana Bunu Al
# 2. Bana Bunu Al İş Ortağım
# 3. Eğitim Finansmanı Sistemi
#
# Sayfadaki link yapısı değişse bile bu allowlist sayesinde
# yanlış sayfaların ürün olarak alınması engellenir.
# ============================================================

BILINEN_URUN_URLLERI = {
    f"{TABAN_URL}/krediler/bana-bunu-al",
    f"{TABAN_URL}/finansmanlar/bana-bunu-al-is-ortagim",
    f"{TABAN_URL}/krediler/hayat-finans-egitim-finansmani-sistemi",
}


# ============================================================
# ÜRÜN BAŞLIK FİLTRESİ
# ============================================================

GECERSIZ_URUN_BASLIKLARI = {
    "krediler",
    "kredi",
    "finansmanlar",
    "finansman",
    "kendim için",
    "kendim icin",
}


# ============================================================
# KATEGORİLER
# ============================================================

KATEGORI_ETIKETLERI = [
    "Arkadaşını Getir",
    "Biz Kart",
    "Katılma Hesabı",
    "Teknoloji",
    "Yatırım",
    "Genel",
]

VARSAYILAN_KATEGORI = "Genel"


# ============================================================
# SÜRESİ GEÇMİŞ KAMPANYA İFADELERİ
# ============================================================

SURESI_GECMIS_IFADELERI = [
    "kampanyamız sona ermiştir",
    "kampanyamız sona erdi",
    "kampanya sona ermiştir",
    "kampanya sona erdi",
    "kampanya süresi dolmuştur",
    "kampanya süresi sona ermiştir",
]


# ============================================================
# AY İSİMLERİ
# ============================================================

AYLAR = (
    "Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
    "Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
)


# ============================================================
# TARİH REGEXLERİ
# ============================================================

# ------------------------------------------------------------
# 01 Ocak 2026 - 31 Aralık 2026
# ------------------------------------------------------------

TARIH_ARALIGI_TAM = re.compile(
    rf"""
    \b
    (?:0?[1-9]|[12][0-9]|3[01])
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    \s*
    [-–—]
    \s*
    (?:0?[1-9]|[12][0-9]|3[01])
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# 16 Haziran - 31 Ağustos 2026
# ------------------------------------------------------------

TARIH_ARALIGI_ILK_YILSIZ = re.compile(
    rf"""
    \b
    (?:0?[1-9]|[12][0-9]|3[01])
    \s+
    (?:{AYLAR})
    \s*
    [-–—]
    \s*
    (?:0?[1-9]|[12][0-9]|3[01])
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# 01.01.2026 - 31.12.2026
# ------------------------------------------------------------

TARIH_ARALIGI_SAYISAL = re.compile(
    r"""
    \b
    (?:0?[1-9]|[12][0-9]|3[01])
    [./-]
    (?:0?[1-9]|1[0-2])
    [./-]
    \d{4}

    \s*
    [-–—]
    \s*

    (?:0?[1-9]|[12][0-9]|3[01])
    [./-]
    (?:0?[1-9]|1[0-2])
    [./-]
    \d{4}
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# 31 Ağustos 2026
# ------------------------------------------------------------

TARIH_TEK_YAZILI = re.compile(
    rf"""
    \b
    (?:0?[1-9]|[12][0-9]|3[01])
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
    (?:0?[1-9]|[12][0-9]|3[01])
    [./-]
    (?:0?[1-9]|1[0-2])
    [./-]
    \d{4}
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
# TARİH YOK MU?
# ============================================================

def tarih_yok_mu(metin: str) -> bool:

    if metin is None:
        return True

    temiz = normalize_metin(
        metin
    ).lower()

    return temiz in {
        "",
        "-",
        "–",
        "—",
        "yok",
        "yoktur",
        "belirtilmemiş",
        "belirtilmemistir",
        "belirtilmemiştir",
        "belirtilmemistir",
        "bulunmuyor",
        "bulunmamaktadır",
        "bulunmamaktadir",
        "n/a",
        "na",
        "none",
        "null",
    }


# ============================================================
# TARİHLERİ BUL
# ============================================================

def tarihleri_bul(
    metin: str
) -> list[str]:

    if not metin:
        return []

    metin = normalize_metin(
        metin
    )

    sonuc = []


    # --------------------------------------------------------
    # 1. TAM TARİH ARALIĞI
    # --------------------------------------------------------

    desenler = [
        TARIH_ARALIGI_TAM,
        TARIH_ARALIGI_ILK_YILSIZ,
        TARIH_ARALIGI_SAYISAL,
    ]


    for desen in desenler:

        for match in desen.finditer(
            metin
        ):

            tarih = match.group(
                0
            ).strip()

            if tarih not in sonuc:
                sonuc.append(
                    tarih
                )


    # --------------------------------------------------------
    # 2. TEK TARİH
    # --------------------------------------------------------

    for desen in [
        TARIH_TEK_YAZILI,
        TARIH_TEK_SAYISAL,
    ]:

        for match in desen.finditer(
            metin
        ):

            tarih = match.group(
                0
            ).strip()

            if tarih not in sonuc:
                sonuc.append(
                    tarih
                )


    return sonuc


# ============================================================
# KATEGORİ BUL
# ============================================================

def kart_kategorisini_bul(
    a_etiketi
) -> str:

    for div in a_etiketi.find_all(
        "div"
    ):

        metin = normalize_metin(
            div.get_text(
                " ",
                strip=True
            )
        )

        if metin in KATEGORI_ETIKETLERI:
            return metin

    return VARSAYILAN_KATEGORI


# ============================================================
# KAMPANYA / ÜRÜN TARİHİNİ BUL
# ============================================================

def tarih_metnini_bul(
    icerik
) -> str | None:
    """
    Tarih çıkarma sırası:

    1. Kampanya Dönemi
    2. Başlangıç/Bitiş Tarihi
    3. Geçerlilik Tarihi
    4. Güçlü <b>/<strong> alanları
    5. İçerik metni

    Böylece önce anlamlı tarih bilgisi aranır.
    """

    if icerik is None:
        return None


    # ========================================================
    # ETİKETLER
    # ========================================================

    tarih_etiketleri = [
        "Kampanya Dönemi",
        "Kampanya Tarihi",
        "Başlangıç ve Bitiş Tarihi",
        "Başlangıç ve Bitiş Tarihleri",
        "Başlangıç Tarihi",
        "Bitiş Tarihi",
        "Geçerlilik Tarihi",
        "Geçerlilik",
        "Güncelleme Tarihi",
        "Güncellenme Tarihi",
        "Son Güncelleme Tarihi",
        "Son Güncelleme",
        "Yayın Tarihi",
        "Yayımlanma Tarihi",
        "Başvuru Tarihi",
    ]


    # ========================================================
    # 1. ETİKETLİ ALANLAR
    # ========================================================

    for etiket in tarih_etiketleri:

        regex = re.compile(
            re.escape(etiket),
            re.IGNORECASE
        )

        bulunanlar = icerik.find_all(
            string=regex
        )


        for text_node in bulunanlar:

            parent = text_node.parent

            if parent is None:
                continue


            # ------------------------------------------------
            # Aynı element
            # ------------------------------------------------

            parent_metin = normalize_metin(
                parent.get_text(
                    " ",
                    strip=True
                )
            )


            if parent_metin:

                parcalar = re.split(
                    re.escape(etiket),
                    parent_metin,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )


                if len(
                    parcalar
                ) == 2:

                    deger = normalize_metin(
                        parcalar[1]
                    )


                    # Başka bir etiket geliyorsa orada kes
                    deger = re.split(
                        r"(?:Kampanya Dönemi|"
                        r"Kampanya Tarihi|"
                        r"Başlangıç Tarihi|"
                        r"Bitiş Tarihi|"
                        r"Geçerlilik Tarihi|"
                        r"Geçerlilik|"
                        r"Güncelleme Tarihi|"
                        r"Son Güncelleme)",
                        deger,
                        maxsplit=1,
                        flags=re.IGNORECASE
                    )[0]


                    deger = normalize_metin(
                        deger
                    )


                    if tarih_yok_mu(
                        deger
                    ):

                        return None


                    tarihler = tarihleri_bul(
                        deger
                    )


                    if tarihler:

                        # Tarih aralığı
                        for tarih in tarihler:

                            if (
                                TARIH_ARALIGI_TAM.search(
                                    tarih
                                )
                                or
                                TARIH_ARALIGI_ILK_YILSIZ.search(
                                    tarih
                                )
                                or
                                TARIH_ARALIGI_SAYISAL.search(
                                    tarih
                                )
                            ):

                                return tarih


                        return tarihler[0]


            # ------------------------------------------------
            # Parent-parent fallback
            # ------------------------------------------------

            try:

                ust = parent.parent

                if ust:

                    ust_metin = normalize_metin(
                        ust.get_text(
                            " ",
                            strip=True
                        )
                    )


                    if ust_metin:

                        # Önce etiket sonrası kısmı al
                        parcalar = re.split(
                            re.escape(etiket),
                            ust_metin,
                            maxsplit=1,
                            flags=re.IGNORECASE
                        )


                        if len(
                            parcalar
                        ) == 2:

                            deger = normalize_metin(
                                parcalar[1]
                            )


                            deger = re.split(
                                r"(?:Kampanya Dönemi|"
                                r"Kampanya Tarihi|"
                                r"Başlangıç Tarihi|"
                                r"Bitiş Tarihi|"
                                r"Geçerlilik Tarihi|"
                                r"Geçerlilik)",
                                deger,
                                maxsplit=1,
                                flags=re.IGNORECASE
                            )[0]


                            tarihler = (
                                tarihleri_bul(
                                    deger
                                )
                            )


                            if tarihler:

                                for tarih in tarihler:

                                    if (
                                        TARIH_ARALIGI_TAM.search(
                                            tarih
                                        )
                                        or
                                        TARIH_ARALIGI_ILK_YILSIZ.search(
                                            tarih
                                        )
                                        or
                                        TARIH_ARALIGI_SAYISAL.search(
                                            tarih
                                        )
                                    ):

                                        return tarih


                                return tarihler[0]

            except Exception:
                pass


    # ========================================================
    # 2. BOLD / STRONG
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


        if not metin:
            continue


        tarihler = tarihleri_bul(
            metin
        )


        if tarihler:

            for tarih in tarihler:

                if (
                    TARIH_ARALIGI_TAM.search(
                        tarih
                    )
                    or
                    TARIH_ARALIGI_ILK_YILSIZ.search(
                        tarih
                    )
                    or
                    TARIH_ARALIGI_SAYISAL.search(
                        tarih
                    )
                ):

                    return tarih


            return tarihler[0]


    # ========================================================
    # 3. TAM İÇERİK FALLBACK
    # ========================================================

    tam_metin = normalize_metin(
        icerik.get_text(
            " ",
            strip=True
        )
    )


    if not tam_metin:
        return None


    # --------------------------------------------------------
    # "tarihine kadar" özel durumu
    # --------------------------------------------------------

    kadar_pattern = re.compile(
        rf"""
        (
            (?:0?[1-9]|[12][0-9]|3[01])
            \s+
            (?:{AYLAR})
            \s+
            \d{{4}}
        )
        \s*
        (?:tarihine\s+)?
        kadar
        """,
        re.IGNORECASE | re.VERBOSE
    )


    kadar_match = kadar_pattern.search(
        tam_metin
    )


    if kadar_match:

        return kadar_match.group(
            1
        ).strip()


    # --------------------------------------------------------
    # Tarih aralığı
    # --------------------------------------------------------

    for desen in [
        TARIH_ARALIGI_TAM,
        TARIH_ARALIGI_ILK_YILSIZ,
        TARIH_ARALIGI_SAYISAL,
    ]:

        match = desen.search(
            tam_metin
        )

        if match:

            return match.group(
                0
            ).strip()


    # --------------------------------------------------------
    # Tek tarih
    # --------------------------------------------------------

    for desen in [
        TARIH_TEK_YAZILI,
        TARIH_TEK_SAYISAL,
    ]:

        match = desen.search(
            tam_metin
        )

        if match:

            return match.group(
                0
            ).strip()


    return None


# ============================================================
# HAYAT FİNANS SPIDER
# ============================================================

class HayatFinansSpider(
    TabanScraper
):

    banka_kodu = "hayat_finans"


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    def kampanyalari_topla(
        self
    ) -> list[dict]:

        kayitlar: list[dict] = []


        print(
            f"  Liste sayfası: "
            f"{LISTE_URL}"
        )


        soup = self.getir(
            LISTE_URL
        )


        if soup is None:

            print(
                "  Kampanya liste sayfası alınamadı."
            )

            return kayitlar


        # ====================================================
        # KAMPANYA URL -> KATEGORİ
        # ====================================================

        url_kategori_haritasi: dict[
            str,
            str
        ] = {}


        for a in soup.select(
            "a[href]"
        ):

            href = (
                a["href"]
                .strip()
                .split("?")[0]
                .split("#")[0]
            )


            href_temiz = (
                href
                .replace(
                    TABAN_URL,
                    ""
                )
                .replace(
                    "https://www.hayatfinans.com.tr",
                    ""
                )
            )


            if not DETAY_DESENI.match(
                href_temiz
            ):

                continue


            tam_url = (
                TABAN_URL
                + href_temiz
            )


            kategori = (
                kart_kategorisini_bul(
                    a
                )
            )


            url_kategori_haritasi.setdefault(
                tam_url,
                kategori
            )


        print(
            f"  {len(url_kategori_haritasi)} "
            f"tekil kampanya linki bulundu"
        )


        # ====================================================
        # DETAY SAYFALARI
        # ====================================================

        for url in sorted(
            url_kategori_haritasi
        ):

            kategori = (
                url_kategori_haritasi[
                    url
                ]
            )


            soup = self.getir(
                url
            )


            if soup is None:
                continue


            h1 = (
                soup.select_one(
                    "main h1"
                )
                or
                soup.select_one(
                    "h1"
                )
            )


            icerik = (
                soup.select_one(
                    "main"
                )
            )


            if h1 is None or icerik is None:

                print(
                    f"    YAPI UYUŞMADI, "
                    f"atlandı: {url}"
                )

                continue


            # ------------------------------------------------
            # İÇERİK
            # ------------------------------------------------

            ham_metin = (
                self.metin_temizle(
                    icerik
                )
            )


            # ------------------------------------------------
            # SÜRESİ GEÇMİŞ KONTROLÜ
            # ------------------------------------------------

            ham_metin_kucuk = (
                ham_metin.lower()
            )


            sureli = any(
                ifade in ham_metin_kucuk
                for ifade in SURESI_GECMIS_IFADELERI
            )


            if sureli:

                print(
                    f"    SÜRESİ GEÇMİŞ, "
                    f"atlandı: {url}"
                )

                continue


            # ------------------------------------------------
            # TARİH
            # ------------------------------------------------

            tarih_metni = (
                tarih_metnini_bul(
                    icerik
                )
            )


            # ------------------------------------------------
            # KAYIT
            # ------------------------------------------------

            kayitlar.append(
                {
                    "banka": self.banka_kodu,
                    "url": url,
                    "baslik": self.metin_temizle(
                        h1
                    ),
                    "ham_metin": ham_metin,
                    "kategori": kategori,
                    "tarih_metni": tarih_metni,
                }
            )


            print(
                f"    OK [{kategori}]: "
                f"{kayitlar[-1]['baslik'][:55]} "
                f"| Tarih: "
                f"{tarih_metni or 'Bulunamadı'}"
            )


        return kayitlar


    # ========================================================
    # ÜRÜNLER / KREDİLER
    # ========================================================

    def urunleri_topla(
        self
    ) -> list[dict]:

        kayitlar: list[dict] = []


        print(
            f"  Ürün/Kredi liste sayfası: "
            f"{KREDI_LISTE_URL}"
        )


        soup = self.getir(
            KREDI_LISTE_URL
        )


        if soup is None:

            print(
                "  Kredi liste sayfası alınamadı."
            )

            return kayitlar


        # ====================================================
        # ÜRÜN LİNKLERİ
        # ====================================================

        urun_linkleri: set[str] = set()


        # ----------------------------------------------------
        # Önce doğrudan bilinen 3 ürünü al
        # ----------------------------------------------------

        urun_linkleri.update(
            BILINEN_URUN_URLLERI
        )


        # ----------------------------------------------------
        # Sayfadaki linkleri de kontrol et
        # ----------------------------------------------------

        for a in soup.select(
            "a[href]"
        ):

            href = (
                a["href"]
                .strip()
                .split("?")[0]
                .split("#")[0]
                .rstrip("/")
            )


            # Relative -> absolute
            if href.startswith("/"):
                tam_url = (
                    TABAN_URL
                    + href
                )

            elif href.startswith(
                TABAN_URL
            ):

                tam_url = href

            elif href.startswith(
                "https://www.hayatfinans.com.tr"
            ):

                tam_url = href.replace(
                    "https://www.hayatfinans.com.tr",
                    TABAN_URL
                )

            else:

                continue


            temiz_url = (
                tam_url
                .split("?")[0]
                .split("#")[0]
                .rstrip("/")
            )


            # ------------------------------------------------
            # Sadece bilinen 3 ürün
            # ------------------------------------------------

            if temiz_url in BILINEN_URUN_URLLERI:

                urun_linkleri.add(
                    temiz_url
                )


        urun_linkleri_sirali = sorted(
            urun_linkleri
        )


        print(
            f"  {len(urun_linkleri_sirali)} "
            f"tekil ürün linki bulundu"
        )


        # ====================================================
        # ÜRÜN DETAYLARI
        # ====================================================

        for url in urun_linkleri_sirali:

            print(
                f"  Ürün taranıyor: "
                f"{url}"
            )


            soup = self.getir(
                url
            )


            if soup is None:

                print(
                    f"    Sayfa alınamadı, "
                    f"atlandı: {url}"
                )

                continue


            # ------------------------------------------------
            # BAŞLIK
            # ------------------------------------------------

            h1 = (
                soup.select_one(
                    "main h1"
                )
                or
                soup.select_one(
                    "h1"
                )
            )


            # ------------------------------------------------
            # İÇERİK
            # ------------------------------------------------

            icerik = (
                soup.select_one(
                    "main"
                )
            )


            if h1 is None:

                print(
                    f"    Ürün başlığı bulunamadı, "
                    f"atlandı: {url}"
                )

                continue


            if icerik is None:

                print(
                    f"    Ürün içeriği bulunamadı, "
                    f"atlandı: {url}"
                )

                continue


            # ------------------------------------------------
            # BAŞLIK
            # ------------------------------------------------

            baslik = (
                self.metin_temizle(
                    h1
                )
            )


            if (
                not baslik
                or
                baslik.lower()
                in GECERSIZ_URUN_BASLIKLARI
            ):

                print(
                    f"    Geçersiz ürün başlığı, "
                    f"atlandı: {url}"
                )

                continue


            # ------------------------------------------------
            # HAM METİN
            # ------------------------------------------------

            ham_metin = (
                self.metin_temizle(
                    icerik
                )
            )


            if len(
                ham_metin
            ) < 30:

                print(
                    f"    Ürün içeriği çok kısa, "
                    f"atlandı: {url}"
                )

                continue


            # ------------------------------------------------
            # KATEGORİ
            # ------------------------------------------------

            #kategori = "Krediler"


            if "bana-bunu-al-is-ortagim" in url:

                kategori = (
                    "İş Ortağım"
                )

            elif "eğitim-finansmani" in url:

                kategori = (
                    "Eğitim Finansmanı"
                )

            elif "bana-bunu-al" in url:

                kategori = (
                    "İhtiyaç Finansmanı"
                )


            # ------------------------------------------------
            # TARİH
            # ------------------------------------------------
            #
            # Ürün sayfasında gerçek tarih varsa alınır.
            # Yoksa None kalır.
            # ------------------------------------------------

            tarih_metni = (
                tarih_metnini_bul(
                    icerik
                )
            )


            # ------------------------------------------------
            # KAYIT
            # ------------------------------------------------

            kayitlar.append(
                {
                    "banka": self.banka_kodu,
                    "url": url,
                    "baslik": baslik,
                    "ham_metin": ham_metin,
                    #"kategori": kategori,
                    "tarih_metni": tarih_metni,
                }
            )


            print(
                f"    OK: "
                f"{baslik[:55]} "
                #f"| Kategori: {kategori} "
                f"| Tarih: "
                f"{tarih_metni or 'Bulunamadı'}"
            )


        return kayitlar


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    from collections import Counter


    spider = HayatFinansSpider()


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    print(
        "Hayat Finans Spider "
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
        "hayat_finans"
    )


    # ========================================================
    # KATEGORİ ÖZETİ
    # ========================================================

    ozet = Counter(
        k["kategori"]
        for k in kampanya_kayitlari
    )


    print(
        "\nKategori bazında dağılım:"
    )


    for kategori, sayi in sorted(
        ozet.items()
    ):

        print(
            f"  {kategori}: {sayi}"
        )


    # ========================================================
    # TARİHİ OLMAYAN KAMPANYALAR
    # ========================================================

    tarihi_olmayanlar = [
        k
        for k in kampanya_kayitlari
        if k["tarih_metni"] is None
    ]


    print(
        f"\n{len(tarihi_olmayanlar)} "
        f"kampanyada tarih bulunamadı:"
    )


    for k in tarihi_olmayanlar:

        print(
            f"  - {k['url']}"
        )


    # ========================================================
    # BULUNAMAYAN TARİHLER DOSYASI
    # ========================================================

    with open(
        "hayatfinans_tarih_bulunamayanlar.txt",
        "w",
        encoding="utf-8"
    ) as f:

        for k in tarihi_olmayanlar:

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
                "HAM METİN:\n"
                f"{k['ham_metin']}\n"
            )

            f.write(
                "\n"
                + "=" * 80
                + "\n\n"
            )


    print(
        "Detaylar "
        "'hayatfinans_tarih_bulunamayanlar.txt' "
        "dosyasına yazıldı."
    )


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    print(
        "\nHayat Finans Spider "
        "(Krediler / Ürünler) çalıştırılıyor..."
    )


    urun_verileri = (
        spider.urunleri_topla()
    )


    spider.kaydet_mongoDB(
        urun_verileri,
        "hayat_finans_ürün"
    )


    # ========================================================
    # ÜRÜN ÖZETİ
    # ========================================================

    print(
        f"\nToplam ürün: "
        f"{len(urun_verileri)}"
    )


    urun_tarihi_olmayanlar = [
        u
        for u in urun_verileri
        if u["tarih_metni"] is None
    ]


    print(
        f"Tarihi bulunan ürün: "
        f"{len(urun_verileri) - len(urun_tarihi_olmayanlar)}"
    )


    print(
        f"Tarihi bulunamayan ürün: "
        f"{len(urun_tarihi_olmayanlar)}"
    )


    for urun in urun_tarihi_olmayanlar:

        print(
            f"  - {urun['baslik']}"
            f" | {urun['url']}"
        )