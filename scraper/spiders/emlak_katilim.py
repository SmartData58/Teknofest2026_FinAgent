import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJE_KOK = Path(__file__).resolve().parent.parent.parent

if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))


from scraper.playwright_scraper import PlaywrightTabanScraper
from scraper.base_scraper import TabanScraper


# ============================================================
# SABİTLER
# ============================================================

TABAN_URL = os.getenv("URL_SPIDER_EMLAKKATILIM", "https://www.emlakkatilim.com.tr")


LISTELER = {
    f"{TABAN_URL}/tr/bireysel/kampanyalar": "bireysel",
    f"{TABAN_URL}/tr/kurumsal/kampanyalar": "kurumsal",
}


DETAY_DESENLERI = [
    re.compile(
        r"^/tr/bireysel/kampanyalar/kampanya/[a-z0-9-]+/?$",
        re.IGNORECASE
    ),

    re.compile(
        r"^/tr/kurumsal/kampanyalar/[a-z0-9-]+/?$",
        re.IGNORECASE
    ),
]


# ============================================================
# ÜRÜNLER
# ============================================================

URUN_LISTE_URL = (
    f"{TABAN_URL}/tr/bireysel/finansmanlar"
)


URUN_DETAY_DESENI = re.compile(
    r"^/tr/bireysel/finansmanlar/"
    r"[a-z0-9-]+"
    r"(?:/[a-z0-9-]+)?/?$",
    re.IGNORECASE
)


GECERSIZ_URUN_BASLIKLARI = {
    "finansmanlar",
    "bireysel finansmanlar",
    "bireysel",
    "krediler",
    "finansman",
}


# ============================================================
# TARİHSİZ OLDUĞU BİLİNEN ÜRÜNLER
# ============================================================

TARIHSIZ_URUN_URLLERI = {
    f"{TABAN_URL}/tr/bireysel/finansmanlar/birlikte-isyeri-finansmani",
    f"{TABAN_URL}/tr/bireysel/finansmanlar/ihtiyac-finansmani",
}


# ============================================================
# AY İSİMLERİ
# ============================================================

AYLAR = (
    "Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
    "Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
)


# ============================================================
# TARİH DESENLERİ
# ============================================================

TARIH_ARALIGI_YAZILI = re.compile(
    rf"""
    \b
    (?:0?[1-9]|[12][0-9]|3[01])
    \s+
    (?:{AYLAR})
    (?:\s+\d{{4}})?
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
# GENEL YARDIMCI FONKSİYONLAR
# ============================================================

def metin_normalize(metin: str) -> str:

    if not metin:
        return ""

    return " ".join(
        metin
        .replace("\xa0", " ")
        .split()
    ).strip()


def tarih_yok_mu(deger: str) -> bool:

    if deger is None:
        return True

    temiz = metin_normalize(
        deger
    ).lower()

    return temiz in {
        "",
        "-",
        "–",
        "—",
        "yok",
        "yoktur",
        "yoktur.",
        "belirtilmemiş",
        "belirtilmemistir",
        "belirtilmemiştir",
        "belirtilmemistir",
        "bulunmuyor",
        "bulunmamaktadır",
        "bulunmamaktadir",
        "n/a",
        "na",
        "null",
        "none",
    }


def tarihleri_bul(metin: str) -> list[str]:

    if not metin:
        return []

    metin = metin_normalize(
        metin
    )

    sonuc = []

    # --------------------------------------------------------
    # Tarih aralığı - yazılı
    # --------------------------------------------------------

    for match in TARIH_ARALIGI_YAZILI.finditer(
        metin
    ):

        tarih = match.group(0).strip()

        if tarih not in sonuc:
            sonuc.append(tarih)

    # --------------------------------------------------------
    # Tarih aralığı - sayısal
    # --------------------------------------------------------

    for match in TARIH_ARALIGI_SAYISAL.finditer(
        metin
    ):

        tarih = match.group(0).strip()

        if tarih not in sonuc:
            sonuc.append(tarih)

    # --------------------------------------------------------
    # Tek yazılı tarih
    # --------------------------------------------------------

    for match in TARIH_TEK_YAZILI.finditer(
        metin
    ):

        tarih = match.group(0).strip()

        if tarih not in sonuc:
            sonuc.append(tarih)

    # --------------------------------------------------------
    # Tek sayısal tarih
    # --------------------------------------------------------

    for match in TARIH_TEK_SAYISAL.finditer(
        metin
    ):

        tarih = match.group(0).strip()

        if tarih not in sonuc:
            sonuc.append(tarih)

    return sonuc


# ============================================================
# TARİH METNİNİ BUL
# ============================================================

def tarih_metnini_bul(
    icerik
) -> str | None:

    """
    Kampanya ve ürünler için ortak tarih çıkarıcı.
    """

    if icerik is None:
        return None


    # ========================================================
    # 1. ANLAMLI TARİH ETİKETLERİ
    # ========================================================

    etiketler = [
        "Başlangıç Tarihi",
        "Bitiş Tarihi",
        "Başlangıç ve Bitiş Tarihi",
        "Başlangıç ve Bitiş Tarihleri",
        "Kampanya Tarihi",
        "Kampanya Dönemi",
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


    for etiket in etiketler:

        regex = re.compile(
            re.escape(etiket),
            re.IGNORECASE
        )

        bulunan_elementler = icerik.find_all(
            string=regex
        )

        for text_node in bulunan_elementler:

            parent = text_node.parent

            if parent is None:
                continue

            parent_metin = metin_normalize(
                parent.get_text(
                    " ",
                    strip=True
                )
            )

            if not parent_metin:
                continue


            etiket_sonrasi = re.split(
                re.escape(etiket),
                parent_metin,
                maxsplit=1,
                flags=re.IGNORECASE
            )


            if len(
                etiket_sonrasi
            ) == 2:

                deger = metin_normalize(
                    etiket_sonrasi[1]
                )


                deger = re.split(
                    r"(?:Başlangıç Tarihi|"
                    r"Bitiş Tarihi|"
                    r"Kampanya Tarihi|"
                    r"Geçerlilik Tarihi|"
                    r"Güncelleme Tarihi|"
                    r"Son Güncelleme)",
                    deger,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0]


                deger = metin_normalize(
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

                    if len(
                        tarihler
                    ) >= 2:

                        return (
                            f"{tarihler[0]} - "
                            f"{tarihler[1]}"
                        )

                    return tarihler[0]


            # ------------------------------------------------
            # Parent-parent fallback
            # ------------------------------------------------

            try:

                parent_parent = (
                    parent.parent
                )

                if parent_parent:

                    metin = metin_normalize(
                        parent_parent.get_text(
                            " ",
                            strip=True
                        )
                    )

                    if metin:

                        tarihler = (
                            tarihleri_bul(
                                metin
                            )
                        )

                        if tarihler:

                            if len(
                                tarihler
                            ) >= 2:

                                return (
                                    f"{tarihler[0]} - "
                                    f"{tarihler[1]}"
                                )

                            return tarihler[0]

            except Exception:
                pass


    # ========================================================
    # 2. VURGULANMIŞ TARİH ALANLARI
    # ========================================================

    for etiket in icerik.find_all(
        ["b", "strong", "th", "label"]
    ):

        metin = metin_normalize(
            etiket.get_text(
                " ",
                strip=True
            )
        )

        if not metin:
            continue


        if tarih_yok_mu(
            metin
        ):
            continue


        anahtar_var = any(
            anahtar.lower() in metin.lower()
            for anahtar in [
                "başlangıç",
                "bitiş",
                "kampanya tarihi",
                "kampanya dönemi",
                "geçerlilik",
                "güncelleme",
                "yayın tarihi",
                "başvuru tarihi",
            ]
        )


        tarihler = tarihleri_bul(
            metin
        )


        if tarihler and anahtar_var:

            if len(
                tarihler
            ) >= 2:

                return (
                    f"{tarihler[0]} - "
                    f"{tarihler[1]}"
                )

            return tarihler[0]


    # ========================================================
    # 3. BOLD / STRONG TARİH
    # ========================================================

    for etiket in icerik.find_all(
        ["b", "strong"]
    ):

        metin = metin_normalize(
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

            if len(
                tarihler
            ) >= 2:

                return (
                    f"{tarihler[0]} - "
                    f"{tarihler[1]}"
                )

            return tarihler[0]


    # ========================================================
    # 4. TAM İÇERİK FALLBACK
    # ========================================================

    tam_metin = metin_normalize(
        icerik.get_text(
            " ",
            strip=True
        )
    )


    if not tam_metin:
        return None


    tarihler = tarihleri_bul(
        tam_metin
    )


    if not tarihler:
        return None


    # --------------------------------------------------------
    # Önce tarih aralığını tercih et
    # --------------------------------------------------------

    for tarih in tarihler:

        if (
            TARIH_ARALIGI_YAZILI.search(
                tarih
            )
            or
            TARIH_ARALIGI_SAYISAL.search(
                tarih
            )
        ):

            return tarih


    return tarihler[0]


# ============================================================
# SPIDER
# ============================================================

class EmlakKatilimSpider(
    PlaywrightTabanScraper
):

    banka_kodu = "emlak_katilim"

    render_bekleme = "domcontentloaded"

    challenge_bekleme_ms = 5000

    kimlik_maskesi = False


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    def kampanyalari_topla(
        self
    ) -> list[dict]:

        kayitlar: list[dict] = []


        with self.oturum():

            detaylar: dict[str, str] = {}


            # ------------------------------------------------
            # LİSTE SAYFALARI
            # ------------------------------------------------

            for liste_url, kategori in LISTELER.items():

                print(
                    f"  Liste sayfası (render): "
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
                        a["href"]
                        .strip()
                        .split("?")[0]
                        .split("#")[0]
                    )


                    href = href.replace(
                        TABAN_URL,
                        ""
                    )


                    if any(
                        desen.match(href)
                        for desen in DETAY_DESENLERI
                    ):

                        detaylar.setdefault(
                            TABAN_URL + href,
                            kategori
                        )


            print(
                f"  {len(detaylar)} "
                f"tekil kampanya linki bulundu"
            )


            # ------------------------------------------------
            # KAMPANYA DETAYLARI
            # ------------------------------------------------

            for url in sorted(
                detaylar
            ):

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
                        "article.o-page__content"
                    )
                    or
                    soup.select_one(
                        ".o-page__content"
                    )
                )


                if (
                    h1 is None
                    or icerik is None
                ):

                    print(
                        f"    YAPI UYUŞMADI, "
                        f"atlandı: {url}"
                    )

                    continue


                baslik = self.metin_temizle(
                    h1
                )


                ham_metin = self.metin_temizle(
                    icerik
                )


                # ------------------------------------------------
                # KAMPANYA TARİHİ
                # ------------------------------------------------

                tarih_metni = (
                    tarih_metnini_bul(
                        icerik
                    )
                )


                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": baslik,
                        "ham_metin": ham_metin,
                        "kategori": detaylar[url],
                        "tarih_metni": tarih_metni,
                    }
                )


                print(
                    f"    OK: "
                    f"[{detaylar[url]}] "
                    f"{baslik[:55]} "
                    f"| Tarih: "
                    f"{tarih_metni or 'Bulunamadı'}"
                )


        return kayitlar


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    def urunleri_topla(
        self
    ) -> list[dict]:

        kayitlar: list[dict] = []


        with self.oturum():

            print(
                f"  Liste sayfası (render): "
                f"{URUN_LISTE_URL}"
            )


            soup = self.getir(
                URUN_LISTE_URL
            )


            if soup is None:

                print(
                    "  Ürün liste sayfası açılamadı."
                )

                return kayitlar


            # ------------------------------------------------
            # ÜRÜN LİNKLERİ
            # ------------------------------------------------

            urun_linkleri: set[str] = set()


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


                yol = href.replace(
                    TABAN_URL,
                    ""
                )


                if not yol.startswith(
                    "/"
                ):
                    continue


                if (
                    URUN_DETAY_DESENI.match(
                        yol
                    )
                    and
                    yol !=
                    "/tr/bireysel/finansmanlar"
                ):

                    urun_linkleri.add(
                        TABAN_URL + yol
                    )


            urun_linkleri_sirali = sorted(
                urun_linkleri
            )


            print(
                f"  {len(urun_linkleri_sirali)} "
                f"tekil aday ürün linki bulundu"
            )


            # ------------------------------------------------
            # ÜRÜN DETAYLARI
            # ------------------------------------------------

            for url in urun_linkleri_sirali:

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
                        "article.o-page__content"
                    )
                    or
                    soup.select_one(
                        ".o-page__content"
                    )
                )


                if (
                    h1 is None
                    or icerik is None
                ):

                    print(
                        f"    YAPI UYUŞMADI, "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # BAŞLIK
                # ------------------------------------------------

                baslik = self.metin_temizle(
                    h1
                )


                if (
                    not baslik
                    or
                    baslik.lower()
                    in GECERSIZ_URUN_BASLIKLARI
                ):

                    print(
                        f"    Ürün detayı değil "
                        f"(kategori/liste sayfası olabilir), "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # İÇERİK
                # ------------------------------------------------

                ham_metin = self.metin_temizle(
                    icerik
                )


                if len(
                    ham_metin
                ) < 30:

                    print(
                        f"    İçerik çok kısa, "
                        f"muhtemelen liste sayfası, "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # KATEGORİ
                # ------------------------------------------------

                yol_kalan = url.replace(
                    f"{TABAN_URL}/tr/bireysel/finansmanlar/",
                    ""
                )


                yol_parcalari = (
                    yol_kalan.split("/")
                )


                kategori = (
                    yol_parcalari[0]
                    if len(
                        yol_parcalari
                    ) > 1
                    else None
                )


                # ------------------------------------------------
                # TARİH
                # ------------------------------------------------

                # BU İKİ ÜRÜNDE TARİH YOK.
                # SADECE BU İKİ URL İÇİN None ZORUNLU.
                if url in TARIHSIZ_URUN_URLLERI:

                    tarih_metni = None

                else:

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
                        "kategori": kategori,
                        "tarih_metni": tarih_metni,
                    }
                )


                print(
                    f"    OK: "
                    f"{baslik[:55]} "
                    f"| Tarih: "
                    f"{tarih_metni or 'Bulunamadı'}"
                )


        return kayitlar


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    from collections import Counter


    spider = EmlakKatilimSpider()


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    print(
        "Emlak Katılım Spider "
        "(Kampanyalar) çalıştırılıyor..."
    )


    kampanya_kayitlari = (
        spider.kampanyalari_topla()
    )


    spider.kaydet_mongoDB(
        kampanya_kayitlari,
        koleksiyon_adi="emlak_katilim"
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
    # TARİHİ OLMAYANLARI DOSYAYA YAZ
    # ========================================================

    with open(
        "emlak_tarih_bulunamayanlar.txt",
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
        "'emlak_tarih_bulunamayanlar.txt' "
        "dosyasına yazıldı."
    )


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    print(
        "\nEmlak Katılım Spider "
        "(Bireysel Finansmanlar / Ürünler) "
        "çalıştırılıyor..."
    )


    urun_verileri = (
        spider.urunleri_topla()
    )


    spider.kaydet_mongoDB(
        urun_verileri,
        koleksiyon_adi="emlak_katilim_ürün"
    )


    # ========================================================
    # ÜRÜN TARİH ÖZETİ
    # ========================================================

    urun_tarihi_olmayanlar = [
        u
        for u in urun_verileri
        if u["tarih_metni"] is None
    ]


    print(
        f"\nToplam ürün: "
        f"{len(urun_verileri)}"
    )


    print(
        f"Tarihi bulunan ürün: "
        f"{len(urun_verileri) - len(urun_tarihi_olmayanlar)}"
    )


    print(
        f"Tarihi bulunamayan ürün: "
        f"{len(urun_tarihi_olmayanlar)}"
    )


    if urun_tarihi_olmayanlar:

        print(
            "\nTarihi bulunamayan ürünler:"
        )

        for urun in urun_tarihi_olmayanlar:

            print(
                f"  - {urun['baslik']}"
                f" | {urun['url']}"
            )