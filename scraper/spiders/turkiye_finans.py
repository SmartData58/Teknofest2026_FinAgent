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

from bs4 import BeautifulSoup


# ============================================================
# PROJE YOLU
# ============================================================

PROJE_KOK = Path(__file__).resolve().parent.parent.parent

if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))


from scraper.playwright_scraper import PlaywrightTabanScraper


# ============================================================
# SABİTLER
# ============================================================

TABAN_URL = os.getenv("URL_SPIDER_TURKIYEFINANS", "https://www.turkiyefinans.com.tr")


# ============================================================
# KAMPANYA
# ============================================================

FINANSMAN_KAMPANYA_URL = (
    f"{TABAN_URL}/tr-tr/kampanyalar/"
    f"Sayfalar/finansman-kampanyalari.aspx"
)


# Finansman kampanyasında yalnızca bunlar alınacak.
HEDEF_KAMPANYA_TIPLERI = {
    "ihtiyac": "İhtiyaç Finansmanı",
    "tasit": "Taşıt Finansmanı",
}


# ============================================================
# ÜRÜNLER
# ============================================================

# Ana ürün sayfaları.
#
# Alt ürünler bu sayfalardaki linklerden dinamik olarak
# keşfedilecek.
#
URUN_KATEGORI_URLLERI = {
    "ihtiyac": (
        f"{TABAN_URL}/tr-tr/bireysel/"
        f"ihtiyac-finansmani"
    ),

    "egitim": (
        f"{TABAN_URL}/tr-tr/bireysel/"
        f"ihtiyac-finansmani"
    ),

    "tasit": (
        f"{TABAN_URL}/tr-tr/bireysel/"
        f"tasit-finansmani"
    ),

    "motosiklet": (
        f"{TABAN_URL}/tr-tr/bireysel/"
        f"tasit-finansmani"
    ),
}


# Ürün detayları için kabul edilecek ana yollar.
URUN_YOL_DESENLERI = [
    re.compile(
        r"^/tr-tr/bireysel/"
        r"ihtiyac-finansmani/"
        r"sayfalar/[a-z0-9-]+\.aspx/?$",
        re.IGNORECASE
    ),

    re.compile(
        r"^/tr-tr/bireysel/"
        r"tasit-finansmani/"
        r"sayfalar/[a-z0-9-]+\.aspx/?$",
        re.IGNORECASE
    ),
]


# ============================================================
# GEÇERSİZ ÜRÜN BAŞLIKLARI
# ============================================================

GECERSIZ_URUN_BASLIKLARI = {
    "ihtiyaç finansmanı",
    "ihtiyac finansmani",
    "taşıt finansmanı",
    "tasit finansmani",
    "motosiklet finansmanı",
    "motosiklet finansmani",
    "finansman",
    "finansman ürünleri",
    "finansman ürünleri ve hizmetler",
}


# ============================================================
# TARİH DESENLERİ
# ============================================================

AYLAR = (
    "Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
    "Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
)


# 01 Ocak 2026 - 31 Aralık 2026
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


# 8 Mayıs - 30 Kasım 2026
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


# 01.01.2026 - 31.12.2026
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


# 31 Aralık 2026 tarihine kadar
TARIH_KADAR_YAZILI = re.compile(
    rf"""
    \b
    \d{{1,2}}
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    (?:['’]\w+)?
    \s*
    (?:
        tarihine
        \s+
    )?
    kadar
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# 31.12.2026 tarihine kadar
TARIH_KADAR_SAYISAL = re.compile(
    r"""
    \b
    \d{1,2}
    [./-]
    \d{1,2}
    [./-]
    \d{4}
    (?:['’]\w+)?
    \s*
    (?:
        tarihine
        \s+
    )?
    kadar
    \b
    """,
    re.VERBOSE
)


# 31 Aralık 2026
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


# 31.12.2026
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


# ============================================================
# METİN
# ============================================================

def normalize_metin(
    metin: str
) -> str:

    if not metin:
        return ""

    return " ".join(
        metin
        .replace("\xa0", " ")
        .split()
    ).strip()


# ============================================================
# URL
# ============================================================

def normalize_url(
    href: str
) -> str:

    if not href:
        return ""

    href = (
        href
        .strip()
        .split("?")[0]
        .split("#")[0]
        .replace(":443", "")
    )

    if href.startswith(
        "https://"
    ):

        return href.rstrip("/")

    if href.startswith(
        "http://"
    ):

        return (
            href
            .replace(
                "http://",
                "https://",
                1
            )
            .rstrip("/")
        )

    if not href.startswith(
        "/"
    ):

        href = "/" + href

    return (
        TABAN_URL
        + href.rstrip("/")
    )


# ============================================================
# TARİH
# ============================================================

def tarih_metnini_bul(
    icerik
) -> str | None:
    """
    Kampanya içeriğindeki gerçek tarih bilgisini bulur.

    Öncelik:
        1. güçlü tarih alanları
        2. bold/strong
        3. tüm içerik

    Tarih yoksa None.
    """

    if icerik is None:
        return None


    # --------------------------------------------------------
    # Önce sayfanın üst kısmındaki anlamlı tarih etiketleri.
    # --------------------------------------------------------

    guclu_etiketler = [
        "Kampanya Tarihleri",
        "Kampanya Tarihi",
        "Kampanya Dönemi",
        "Kampanya Donemi",
        "Başlangıç Tarihi",
        "Bitiş Tarihi",
        "Geçerlilik Tarihi",
    ]


    for etiket in guclu_etiketler:

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


            parent_text = normalize_metin(
                parent.get_text(
                    " ",
                    strip=True
                )
            )


            parcalar = re.split(
                re.escape(etiket),
                parent_text,
                maxsplit=1,
                flags=re.IGNORECASE
            )


            if len(parcalar) != 2:
                continue


            deger = normalize_metin(
                parcalar[1]
            )


            # ------------------------------------------------
            # Tarih aralığı
            # ------------------------------------------------

            for desen in (
                TARIH_ARALIGI_SAYISAL,
                TARIH_ARALIGI_TAM,
                TARIH_ARALIGI_ILK_YILSIZ,
            ):

                match = desen.search(
                    deger
                )

                if match:
                    return match.group(
                        0
                    ).strip()


            # ------------------------------------------------
            # "tarihine kadar"
            # ------------------------------------------------

            for desen in (
                TARIH_KADAR_SAYISAL,
                TARIH_KADAR_YAZILI,
            ):

                match = desen.search(
                    deger
                )

                if match:
                    return match.group(
                        0
                    ).strip()


            # ------------------------------------------------
            # Tek tarih
            # ------------------------------------------------

            for desen in (
                TARIH_TEK_SAYISAL,
                TARIH_TEK_YAZILI,
            ):

                match = desen.search(
                    deger
                )

                if match:
                    return match.group(
                        0
                    ).strip()


    # --------------------------------------------------------
    # Bold / strong
    # --------------------------------------------------------

    for etiket in icerik.find_all(
        ["b", "strong"]
    ):

        metin = normalize_metin(
            etiket.get_text(
                " ",
                strip=True
            )
        )


        for desen in (
            TARIH_ARALIGI_SAYISAL,
            TARIH_ARALIGI_TAM,
            TARIH_ARALIGI_ILK_YILSIZ,
            TARIH_KADAR_SAYISAL,
            TARIH_KADAR_YAZILI,
            TARIH_TEK_SAYISAL,
            TARIH_TEK_YAZILI,
        ):

            match = desen.search(
                metin
            )

            if match:
                return match.group(
                    0
                ).strip()


    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    tam_metin = normalize_metin(
        icerik.get_text(
            " ",
            strip=True
        )
    )


    for desen in (
        TARIH_ARALIGI_SAYISAL,
        TARIH_ARALIGI_TAM,
        TARIH_ARALIGI_ILK_YILSIZ,
        TARIH_KADAR_SAYISAL,
        TARIH_KADAR_YAZILI,
    ):

        match = desen.search(
            tam_metin
        )

        if match:
            return match.group(
                0
            ).strip()


    return None


# ============================================================
# TABLO ÇIKARMA
# ============================================================

def tabloları_cikar(
    icerik
) -> list[dict]:
    """
    Sayfadaki tüm HTML tablolarını yapılandırılmış olarak alır.

    Sonuç örneği:

    [
        {
            "baslik": "...",
            "sutunlar": ["Vade", "Kar Oranı", ...],
            "satirlar": [
                {
                    "Vade": "12",
                    "Kar Oranı": "..."
                }
            ]
        }
    ]
    """

    sonuc = []

    if icerik is None:
        return sonuc


    tablolar = icerik.find_all(
        "table"
    )


    for index, tablo in enumerate(
        tablolar,
        start=1
    ):

        # ----------------------------------------------------
        # Başlık
        # ----------------------------------------------------

        baslik = ""


        onceki = tablo.find_previous(
            ["h2", "h3", "h4", "strong"]
        )


        if onceki:

            baslik = normalize_metin(
                onceki.get_text(
                    " ",
                    strip=True
                )
            )


        # ----------------------------------------------------
        # Satırları al
        # ----------------------------------------------------

        tum_satirlar = []


        for tr in tablo.find_all(
            "tr"
        ):

            hucreler = tr.find_all(
                ["th", "td"]
            )


            if not hucreler:
                continue


            satir = [
                normalize_metin(
                    hucre.get_text(
                        " ",
                        strip=True
                    )
                )
                for hucre in hucreler
            ]


            if any(satir):

                tum_satirlar.append(
                    satir
                )


        if not tum_satirlar:
            continue


        # ----------------------------------------------------
        # Başlık satırı
        # ----------------------------------------------------

        kolonlar = []

        veri_satirlari = []


        ilk_satir = (
            tum_satirlar[0]
        )


        ilk_tr = tablo.find(
            "tr"
        )


        if (
            ilk_tr is not None
            and
            ilk_tr.find("th") is not None
        ):

            kolonlar = [
                x
                for x in ilk_satir
            ]

            veri_satirlari = (
                tum_satirlar[1:]
            )

        else:

            # İlk satırı header kabul ediyoruz.
            kolonlar = [
                x
                if x
                else f"Kolon_{i + 1}"
                for i, x
                in enumerate(
                    ilk_satir
                )
            ]

            veri_satirlari = (
                tum_satirlar[1:]
            )


        # ----------------------------------------------------
        # Dictionary satırlar
        # ----------------------------------------------------

        satirlar = []


        for satir in veri_satirlari:

            satir_dict = {}


            for i, kolon in enumerate(
                kolonlar
            ):

                if i < len(
                    satir
                ):

                    satir_dict[
                        kolon
                    ] = satir[i]

                else:

                    satir_dict[
                        kolon
                    ] = ""


            satirlar.append(
                satir_dict
            )


        sonuc.append(
            {
                "tablo_no": index,
                "baslik": baslik,
                "sutunlar": kolonlar,
                "satirlar": satirlar,
            }
        )


    return sonuc


# ============================================================
# ÜRÜN SINIFLANDIRMA
# ============================================================

def urun_kategorisini_belirle(
    url: str,
    baslik: str,
    ham_metin: str
) -> str | None:

    metin = (
        f"{url} "
        f"{baslik} "
        f"{ham_metin}"
    ).lower()


    # --------------------------------------------------------
    # Motosiklet önce kontrol edilmeli.
    # Çünkü taşıt içinde geçiyor.
    # --------------------------------------------------------

    if (
        "motosiklet" in metin
        or
        "motosiklet-finansmani" in metin
        or
        "motosiklet finansmanı" in metin
    ):

        return "motosiklet"


    # --------------------------------------------------------
    # Eğitim
    # --------------------------------------------------------

    if (
        "eğitim finansmanı" in metin
        or
        "egitim finansmani" in metin
        or
        "eğitim-finansmani" in metin
        or
        "egitim-finansmani" in metin
        or
        "eğitim finansmanı" in baslik.lower()
        or
        "yurt içi ve yurt dışı eğitim finansmanı"
        in metin
    ):

        return "egitim"


    # --------------------------------------------------------
    # Taşıt
    # --------------------------------------------------------

    if (
        "taşıt finansmanı" in metin
        or
        "tasit finansmani" in metin
        or
        "tasit-finansmani" in metin
        or
        "dijital taşıt finansmanı" in metin
        or
        "dijital tasit finansmani" in metin
    ):

        return "tasit"


    # --------------------------------------------------------
    # İhtiyaç
    # --------------------------------------------------------

    if (
        "ihtiyaç finansmanı" in metin
        or
        "ihtiyac finansmani" in metin
        or
        "ihtiyac-finansmani" in metin
        or
        "dijital ihtiyaç finansmanı" in metin
        or
        "dijital ihtiyac finansmani" in metin
    ):

        return "ihtiyac"


    return None


# ============================================================
# KAMPANYA TİPİ BELİRLE
# ============================================================

def kampanya_tipini_belirle(
    metin: str
) -> str | None:

    if not metin:
        return None


    metin = metin.lower()


    # Önce taşıt
    if (
        "motosiklet finansmanı" in metin
        or
        "taşıt finansmanı" in metin
        or
        "taşıt finansman" in metin
        or
        "tasit finansmani" in metin
        or
        "tasit finansman" in metin
        or
        "dijital taşıt" in metin
        or
        "dijital tasit" in metin
    ):

        return "tasit"


    if (
        "ihtiyaç finansmanı" in metin
        or
        "ihtiyac finansmani" in metin
        or
        "ihtiyaç finansman" in metin
        or
        "ihtiyac finansman" in metin
        or
        "dijital ihtiyaç" in metin
        or
        "dijital ihtiyac" in metin
    ):

        return "ihtiyac"


    return None


# ============================================================
# DAHA FAZLA YÜKLE BUTONU
# ============================================================

def daha_fazla_yukle(
    spider,
    bekleme_ms: int = 1500
):
    """
    Sayfadaki 'Daha fazla yükle' / 'Daha Fazla Yükle'
    butonlarına gerektiği kadar tıklar.

    Link sayısı artmıyorsa döngüyü sonlandırır.
    """

    tiklama = 0


    seciciler = [
        "button",
        "a",
        "[role='button']",
    ]


    while True:

        if spider._sayfa.is_closed():
            break


        buton = None


        # ----------------------------------------------------
        # Butonu bul
        # ----------------------------------------------------

        for secici in seciciler:

            try:

                aday = (
                    spider._sayfa
                    .locator(secici)
                    .filter(
                        has_text=re.compile(
                            r"Daha\s+fazla\s+yükle|"
                            r"Daha\s+Fazla\s+Yükle|"
                            r"Daha\s+fazla\s+göster",
                            re.IGNORECASE
                        )
                    )
                    .first
                )


                if (
                    aday.count() > 0
                    and
                    aday.is_visible(
                        timeout=1000
                    )
                ):

                    buton = aday
                    break

            except Exception:
                continue


        if buton is None:
            break


        # ----------------------------------------------------
        # Önceki link sayısı
        # ----------------------------------------------------

        try:

            onceki = len(
                spider._sayfa
                .locator("a[href]")
                .all()
            )

        except Exception:

            onceki = 0


        # ----------------------------------------------------
        # Tıklama
        # ----------------------------------------------------

        try:

            buton.scroll_into_view_if_needed(
                timeout=5000
            )

            spider._sayfa.wait_for_timeout(
                300
            )

            buton.click(
                timeout=5000
            )


        except Exception as e:

            print(
                "    'Daha fazla yükle' "
                f"tıklanamadı: {e}"
            )

            break


        tiklama += 1


        spider._sayfa.wait_for_timeout(
            bekleme_ms
        )


        # ----------------------------------------------------
        # Yeni link sayısı
        # ----------------------------------------------------

        try:

            yeni = len(
                spider._sayfa
                .locator("a[href]")
                .all()
            )

        except Exception:

            yeni = onceki


        print(
            f"    'Daha fazla yükle' "
            f"tıklandı ({tiklama}): "
            f"{onceki} -> {yeni}"
        )


        if yeni <= onceki:

            # Bir kez daha kontrol et.
            spider._sayfa.wait_for_timeout(
                800
            )


            try:

                son = len(
                    spider._sayfa
                    .locator("a[href]")
                    .all()
                )

            except Exception:

                son = yeni


            if son <= onceki:
                break


    return tiklama


# ============================================================
# SPIDER
# ============================================================

class TurkiyeFinansSpider(
    PlaywrightTabanScraper
):

    banka_kodu = "turkiye_finans"

    render_bekleme = "networkidle"


    # ========================================================
    # KAMPANYA LİNKLERİ
    # ========================================================

    def finansman_kampanya_linklerini_topla(
        self
    ) -> dict[str, str]:

        url_tip_haritasi = {}


        print(
            "  Finansman kampanyaları liste "
            f"sayfası: {FINANSMAN_KAMPANYA_URL}"
        )


        soup = self.getir(
            FINANSMAN_KAMPANYA_URL
        )


        if soup is None:

            print(
                "  Finansman kampanyaları "
                "sayfası açılamadı."
            )

            return url_tip_haritasi


        # ====================================================
        # TÜM KAMPANYALAR YÜKLENSİN
        # ====================================================

        print(
            "  Kampanyaların tamamı yükleniyor..."
        )


        daha_fazla_yukle(
            self
        )


        # ====================================================
        # GÜNCEL HTML
        # ====================================================

        html = self._sayfa.content()


        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        # ====================================================
        # DETAY LINKLERİ
        # ====================================================

        adaylar = []


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
            )


            if not href:
                continue


            tam_url = normalize_url(
                href
            )


            if not tam_url:
                continue


            # Sadece Türkiye Finans kampanya sayfaları
            if not tam_url.startswith(
                f"{TABAN_URL}/tr-tr/kampanyalar/"
            ):
                continue


            # Biten kampanyaları da dahil et (atlanmıyor)


            # Kategori/liste sayfalarını alma
            temiz_yol = (
                tam_url
                .replace(
                    TABAN_URL,
                    ""
                )
                .rstrip("/")
            )


            if not re.match(
                r"^/tr-tr/kampanyalar/"
                r"Sayfalar/"
                r"[A-Za-z0-9-]+\.aspx$",
                temiz_yol,
                re.IGNORECASE
            ):

                continue


            sayfa_adi = (
                a.get_text(
                    " ",
                    strip=True
                )
            )


            if not sayfa_adi:
                sayfa_adi = ""


            adaylar.append(
                (
                    tam_url,
                    normalize_metin(
                        sayfa_adi
                    )
                )
            )


        # ====================================================
        # DUPLICATE TEMİZLE
        # ====================================================

        benzersiz = {}


        for url, link_metni in adaylar:

            mevcut = (
                benzersiz.get(
                    url
                )
            )


            if mevcut is None:

                benzersiz[url] = (
                    link_metni
                )

            elif len(link_metni) > len(
                mevcut
            ):

                benzersiz[url] = (
                    link_metni
                )


        print(
            f"  {len(benzersiz)} "
            f"benzersiz kampanya linki bulundu."
        )


        # ====================================================
        # DETAY SAYFALARINI KONTROL ET
        #
        # Link kartındaki kategori metni yeterli değilse
        # detay sayfasının başlık + içeriğinden belirle.
        # ====================================================

        for url in sorted(
            benzersiz
        ):

            link_metni = (
                benzersiz[url]
            )


            tip = (
                kampanya_tipini_belirle(
                    link_metni
                )
            )


            # Tip linkten belirlenemiyorsa detay sayfasını
            # daha sonra kampanyalari_topla() aşamasında
            # kesinleştireceğiz.
            if tip is not None:

                url_tip_haritasi[
                    url
                ] = tip

            else:

                url_tip_haritasi[
                    url
                ] = "belirsiz"


        return url_tip_haritasi


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    def kampanyalari_topla(
        self
    ) -> list[dict]:

        kayitlar = []


        with self.oturum():

            print(
                "\n=== Türkiye Finans "
                "Finansman Kampanyaları ==="
            )


            url_tip_haritasi = (
                self.finansman_kampanya_linklerini_topla()
            )


            print(
                f"\nToplam "
                f"{len(url_tip_haritasi)} "
                f"aday finansman kampanyası bulundu."
            )


            # ------------------------------------------------
            # DETAYLARI TARA
            # ------------------------------------------------

            for url in sorted(
                url_tip_haritasi
            ):

                print(
                    f"  Detay taranıyor: "
                    f"{url}"
                )


                soup = self.getir(
                    url
                )


                if soup is None:
                    continue


                h1 = (
                    soup.select_one(
                        "h1"
                    )
                    or
                    soup.select_one(
                        ".page-title"
                    )
                )


                icerik = (
                    soup.select_one(
                        ".subpage-content"
                    )
                    or
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
                        "    YAPI UYUŞMADI, "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # Gürültü
                # ------------------------------------------------

                for gurultu in icerik.select(
                    ".breadcrumbs, "
                    ".tool, "
                    ".noindex, "
                    ".related, "
                    ".similar, "
                    ".recommended, "
                    ".recommended-campaigns"
                ):

                    try:
                        gurultu.decompose()
                    except Exception:
                        pass


                baslik = self.metin_temizle(
                    h1
                )


                ham_metin = self.metin_temizle(
                    icerik
                )


                # ------------------------------------------------
                # Kesin kampanya tipi
                # ------------------------------------------------

                detay_tip_metni = (
                    f"{baslik} {ham_metin} "
                    f"{url}"
                )


                tip = kampanya_tipini_belirle(
                    detay_tip_metni
                )


                # İhtiyaç veya taşıt değilse alma.
                if tip not in {
                    "ihtiyac",
                    "tasit",
                }:

                    print(
                        "    İhtiyaç/Taşıt "
                        "kampanyası değil, "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # Tarih
                # ------------------------------------------------

                tarih_metni = (
                    tarih_metnini_bul(
                        icerik
                    )
                )


                # ------------------------------------------------
                # Kategori
                # ------------------------------------------------

                kategori = (
                    HEDEF_KAMPANYA_TIPLERI[
                        tip
                    ]
                )


                kayit = {
                    "banka": self.banka_kodu,
                    "url": url,
                    "baslik": baslik,
                    "ham_metin": ham_metin,
                    "kategori": kategori,
                    "tarih_metni": tarih_metni,
                    "kampanya_tipi": tip,
                }


                kayitlar.append(
                    kayit
                )


                print(
                    f"    OK [{kategori}]: "
                    f"{baslik[:60]} "
                    f"| Tarih: "
                    f"{tarih_metni or 'Bulunamadı'}"
                )


        return kayitlar


    # ========================================================
    # ÜRÜN LİNKLERİNİ TOPLA
    # ========================================================

    def finansman_urun_linklerini_topla(
        self
    ) -> dict[str, str]:

        urunler = {}


        with self.oturum():

            for ana_kategori, liste_url in (
                URUN_KATEGORI_URLLERI.items()
            ):

                print(
                    f"\n  Ürün kategori sayfası "
                    f"taranıyor [{ana_kategori}]: "
                    f"{liste_url}"
                )


                soup = self.getir(
                    liste_url
                )


                if soup is None:
                    continue


                html = self._sayfa.content()


                soup = BeautifulSoup(
                    html,
                    "html.parser"
                )


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
                    )


                    tam_url = normalize_url(
                        href
                    )


                    if not tam_url:
                        continue


                    # ------------------------------------------------
                    # İHTİYAÇ / EĞİTİM
                    # ------------------------------------------------

                    if (
                        ana_kategori
                        in {
                            "ihtiyac",
                            "egitim",
                        }
                    ):

                        if not re.match(
                            r"^/tr-tr/bireysel/"
                            r"ihtiyac-finansmani/"
                            r"sayfalar/"
                            r"[a-z0-9-]+\.aspx/?$",
                            tam_url.replace(
                                TABAN_URL,
                                ""
                            ),
                            re.IGNORECASE
                        ):

                            continue


                    # ------------------------------------------------
                    # TAŞIT / MOTOSİKLET
                    # ------------------------------------------------

                    elif (
                        ana_kategori
                        in {
                            "tasit",
                            "motosiklet",
                        }
                    ):

                        if not re.match(
                            r"^/tr-tr/bireysel/"
                            r"tasit-finansmani/"
                            r"sayfalar/"
                            r"[a-z0-9-]+\.aspx/?$",
                            tam_url.replace(
                                TABAN_URL,
                                ""
                            ),
                            re.IGNORECASE
                        ):

                            continue


                    # ------------------------------------------------
                    # Liste/kategori sayfasını ürün olarak alma
                    # ------------------------------------------------

                    if tam_url.rstrip(
                        "/"
                    ) == liste_url.rstrip(
                        "/"
                    ):

                        continue


                    # ------------------------------------------------
                    # Link metni
                    # ------------------------------------------------

                    link_metni = normalize_metin(
                        a.get_text(
                            " ",
                            strip=True
                        )
                    )


                    eski = urunler.get(
                        tam_url
                    )


                    if eski is None:

                        urunler[
                            tam_url
                        ] = {
                            "kaynak_kategori":
                                ana_kategori,
                            "link_metni":
                                link_metni,
                        }

                    else:

                        if (
                            len(link_metni)
                            >
                            len(
                                eski["link_metni"]
                            )
                        ):

                            eski[
                                "link_metni"
                            ] = link_metni


        print(
            f"\n  {len(urunler)} "
            f"aday finansman ürün linki bulundu."
        )


        return urunler


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    def urunleri_topla(
        self
    ) -> list[dict]:

        kayitlar = []


        # ====================================================
        # Linkleri keşfet
        # ====================================================

        adaylar = (
            self.finansman_urun_linklerini_topla()
        )


        print(
            f"\nToplam "
            f"{len(adaylar)} "
            f"tekil ürün adayı bulundu."
        )


        with self.oturum():

            # =================================================
            # ÜRÜN DETAYLARI
            # =================================================

            for url in sorted(
                adaylar
            ):

                kaynak = (
                    adaylar[url]
                )


                print(
                    f"  Ürün taranıyor: "
                    f"{url}"
                )


                soup = self.getir(
                    url
                )


                if soup is None:
                    continue


                h1 = (
                    soup.select_one(
                        "h1"
                    )
                    or
                    soup.select_one(
                        ".page-title"
                    )
                )


                icerik = (
                    soup.select_one(
                        ".subpage-content"
                    )
                    or
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
                        "    YAPI UYUŞMADI, "
                        f"atlandı: {url}"
                    )

                    continue


                baslik = self.metin_temizle(
                    h1
                )


                if not baslik:

                    print(
                        "    Başlık bulunamadı, "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # Gereksiz alanları temizle
                # ------------------------------------------------

                for gurultu in icerik.select(
                    ".breadcrumbs, "
                    ".tool, "
                    ".noindex, "
                    ".related, "
                    ".similar, "
                    ".recommended, "
                    ".recommended-campaigns"
                ):

                    try:
                        gurultu.decompose()
                    except Exception:
                        pass


                ham_metin = self.metin_temizle(
                    icerik
                )


                if len(
                    ham_metin
                ) < 30:

                    print(
                        "    İçerik çok kısa, "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # Kategori belirleme
                # ------------------------------------------------

                urun_tipi = urun_kategorisini_belirle(
                    url,
                    baslik,
                    ham_metin
                )


                # ------------------------------------------------
                # Sadece hedef 4 kategori
                # ------------------------------------------------

                if urun_tipi not in {
                    "ihtiyac",
                    "egitim",
                    "tasit",
                    "motosiklet",
                }:

                    print(
                        "    Hedeflenen dört "
                        "ürün türünden biri değil, "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # Başlık sadece genel kategori ismiyse atla
                # ------------------------------------------------

                if (
                    baslik.strip().lower()
                    in {
                        x.lower()
                        for x in
                        GECERSIZ_URUN_BASLIKLARI
                    }
                ):

                    print(
                        "    Kategori sayfası, "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # Tarih
                # ------------------------------------------------

                tarih_metni = (
                    tarih_metnini_bul(
                        icerik
                    )
                )


                # ------------------------------------------------
                # TABLOLAR
                # ------------------------------------------------

                tablolar = (
                    tabloları_cikar(
                        icerik
                    )
                )


                # ------------------------------------------------
                # Kayıt
                # ------------------------------------------------

                kayit = {
                    "banka": self.banka_kodu,
                    "url": url,
                    "baslik": baslik,
                    "ham_metin": ham_metin,
                    "kategori": urun_tipi,
                    "kaynak_kategori":
                        kaynak[
                            "kaynak_kategori"
                        ],
                    "tarih_metni":
                        tarih_metni,
                    "tablolar":
                        tablolar,
                }


                kayitlar.append(
                    kayit
                )


                print(
                    f"    OK [{urun_tipi}]: "
                    f"{baslik[:60]} "
                    f"| Tablo: "
                    f"{len(tablolar)} "
                    f"| Tarih: "
                    f"{tarih_metni or 'Bulunamadı'}"
                )


        return kayitlar


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    spider = (
        TurkiyeFinansSpider()
    )


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    print(
        "\n"
        "Türkiye Finans Spider "
        "(İhtiyaç + Taşıt Finansman Kampanyaları) "
        "çalıştırılıyor..."
    )


    kampanya_kayitlari = (
        spider.kampanyalari_topla()
    )


    # --------------------------------------------------------
    # JSON / RAW
    # --------------------------------------------------------

    spider.kaydet(
        kampanya_kayitlari
    )


    # --------------------------------------------------------
    # MongoDB
    # --------------------------------------------------------

    spider.kaydet_mongoDB(
        kampanya_kayitlari,
        "turkiye_finans"
    )


    # ========================================================
    # KAMPANYA ÖZETİ
    # ========================================================

    kampanya_ozet = Counter(
        k["kategori"]
        for k in kampanya_kayitlari
    )


    print(
        "\nKampanya kategori dağılımı:"
    )


    for kategori, sayi in sorted(
        kampanya_ozet.items()
    ):

        print(
            f"  {kategori}: {sayi}"
        )


    tarihi_olmayan_kampanyalar = [
        k
        for k in kampanya_kayitlari
        if not k["tarih_metni"]
    ]


    print(
        f"\nTarihi bulunamayan kampanya: "
        f"{len(tarihi_olmayan_kampanyalar)}"
    )


    for kayit in (
        tarihi_olmayan_kampanyalar
    ):

        print(
            f"  - "
            f"{kayit['baslik']} "
            f"| {kayit['url']}"
        )


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    print(
        "\n"
        "Türkiye Finans Spider "
        "(İhtiyaç + Eğitim + Taşıt + Motosiklet "
        "Finansman Ürünleri) "
        "çalıştırılıyor..."
    )


    urun_kayitlari = (
        spider.urunleri_topla()
    )


    # --------------------------------------------------------
    # MongoDB
    # --------------------------------------------------------

    spider.kaydet_mongoDB(
        urun_kayitlari,
        koleksiyon_adi="turkiye_finans_ürün"
    )


    # ========================================================
    # ÜRÜN ÖZETİ
    # ========================================================

    urun_ozet = Counter(
        u["kategori"]
        for u in urun_kayitlari
    )


    print(
        "\nÜrün kategori dağılımı:"
    )


    for kategori, sayi in sorted(
        urun_ozet.items()
    ):

        print(
            f"  {kategori}: {sayi}"
        )


    # ========================================================
    # TABLO ÖZETİ
    # ========================================================

    toplam_tablo = sum(
        len(
            u.get(
                "tablolar",
                []
            )
        )
        for u in urun_kayitlari
    )


    print(
        f"\nToplam çıkarılan HTML tablo: "
        f"{toplam_tablo}"
    )


    # ========================================================
    # TARİHSİZ ÜRÜNLER
    # ========================================================

    urun_tarih_yok = [
        u
        for u in urun_kayitlari
        if not u["tarih_metni"]
    ]


    print(
        f"Tarihi bulunamayan ürün: "
        f"{len(urun_tarih_yok)}"
    )


    # ========================================================
    # ÜRÜN TABLO ÖZETLERİ
    # ========================================================

    print(
        "\nÜrün tabloları:"
    )


    for urun in urun_kayitlari:

        tablo_sayisi = len(
            urun.get(
                "tablolar",
                []
            )
        )


        if tablo_sayisi > 0:

            print(
                f"  - {urun['baslik']}: "
                f"{tablo_sayisi} tablo"
            )


    print(
        "\nTürkiye Finans Spider "
        "işlemi tamamlandı."
    )