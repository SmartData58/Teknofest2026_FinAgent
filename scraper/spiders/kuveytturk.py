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


from scraper.playwright_scraper import PlaywrightTabanScraper


# ============================================================
# SABİTLER
# ============================================================

TABAN_URL = "https://www.kuveytturk.com.tr"


# ============================================================
# KAMPANYA KATEGORİLERİ
# ============================================================

BOLUM_KATEGORILERI = {

    "kendim-icin": {
        "kart_kampanyalari": "kart-kampanyalari",
        "seyahat_kampanyalari": "seyahat-kampanyalari",
        "musteri_ol_kampanyalari": "musteri-ol-kampanyalari",
        "finansman_kampanyalari": "finansman-kampanyalari",
    },

    "isim-icin": {
        "kart_kampanyalari": "kart-kampanyalari",
        "kobi_kampanyalari": "kobi-kampanyalari",
        "musteri_ol_kampanyalari": "musteri-ol-kampanyalari",
        "pos_kampanyalari": "pos-kampanyalari",
    },
}


# ============================================================
# DAHA FAZLA BUTONU
# ============================================================

DAHA_FAZLA_SECICI = (
    "a:has-text('Daha Fazla'), "
    "button:has-text('Daha Fazla'), "
    "a:has-text('Daha Fazla Göster'), "
    "button:has-text('Daha Fazla Göster')"
)


# ============================================================
# CLEVERTAP POPUP TEMİZLEME
# ============================================================

POPUP_TEMIZLEME_JS = """
document.querySelectorAll(
    'ct-web-popup-imageonly, #wzrkImageOnlyDiv, [id^="wzrk"]'
).forEach(el => el.remove());
"""


# ============================================================
# ÜRÜNLER
# ============================================================

URUN_LISTE_URL = (
    f"{TABAN_URL}/kendim-icin/finansmanlar"
)


URUN_DETAY_DESENI = re.compile(
    r"^/kendim-icin/finansmanlar/"
    r"[a-z0-9-]+"
    r"(?:/[a-z0-9-]+)?/?$",
    re.IGNORECASE
)


GECERSIZ_URUN_BASLIKLARI = {
    "finansmanlar",
    "finansman",
    "kendim için",
    "kendim icin",
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

# Ör:
# 20 Ocak 2026 - 31 Aralık 2026
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


# Ör:
# 8 Mayıs - 30 Kasım 2026
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


# Ör:
# 01.01.2026 - 31.12.2026
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


# Ör:
# 31 Aralık 2026
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


# Ör:
# 31.12.2026
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
# TARİH YOK DEĞERİ
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
    # Tarih aralıkları
    # --------------------------------------------------------

    for desen in [
        TARIH_ARALIGI_TAM,
        TARIH_ARALIGI_ILK_YILSIZ,
        TARIH_ARALIGI_SAYISAL,
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


    # --------------------------------------------------------
    # Tek tarihler
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
# TARİHİ FORMAT OLARAK DOĞRULA
# ============================================================

def tarih_araligi_mi(
    tarih: str
) -> bool:

    if not tarih:
        return False

    return bool(
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
    )


# ============================================================
# TARİH METNİNİ BUL
# ============================================================

def tarih_metnini_bul(
    icerik
) -> str | None:
    """
    Kampanya ve ürün sayfalarında tarih bilgisini bulur.

    Öncelik:

    1. Kampanya Aralığı
    2. Kampanya Tarihi
    3. Başlangıç / Bitiş Tarihi
    4. Geçerlilik Tarihi
    5. Güncelleme Tarihi
    6. Vurgulanmış <b>/<strong> alanları
    7. İçerik içindeki açık tarih aralığı
    """

    if icerik is None:
        return None


    # ========================================================
    # TARİH ETİKETLERİ
    # ========================================================

    etiketler = [
        "Kampanya Aralığı",
        "Kampanya Araligi",
        "Kampanya Tarihi",
        "Kampanya Dönemi",
        "Kampanya Donemi",
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
    ]


    # ========================================================
    # 1. ETİKETLİ ALANLAR
    # ========================================================

    for etiket in etiketler:

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


                    # Sonraki tarih alanında kes
                    deger = re.split(
                        r"(?:Kampanya Aralığı|"
                        r"Kampanya Araligi|"
                        r"Kampanya Tarihi|"
                        r"Kampanya Dönemi|"
                        r"Kampanya Donemi|"
                        r"Başlangıç Tarihi|"
                        r"Bitiş Tarihi|"
                        r"Geçerlilik Tarihi|"
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

                        # Önce tam tarih aralığını tercih et
                        for tarih in tarihler:

                            if tarih_araligi_mi(
                                tarih
                            ):
                                return tarih


                        return tarihler[0]


            # ------------------------------------------------
            # Parent-parent
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


                            tarihler = (
                                tarihleri_bul(
                                    deger
                                )
                            )


                            if tarihler:

                                for tarih in tarihler:

                                    if tarih_araligi_mi(
                                        tarih
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

                if tarih_araligi_mi(
                    tarih
                ):
                    return tarih


            return tarihler[0]


    # ========================================================
    # 3. "TARİHİNE KADAR"
    # ========================================================

    tam_metin = normalize_metin(
        icerik.get_text(
            " ",
            strip=True
        )
    )


    if not tam_metin:
        return None


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


    kadar = kadar_pattern.search(
        tam_metin
    )


    if kadar:

        return kadar.group(
            1
        ).strip()


    # ========================================================
    # 4. AÇIK TARİH ARALIĞI
    # ========================================================

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


    # ========================================================
    # 5. TEK TARİH
    # ========================================================

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
# SPIDER
# ============================================================

class KuveytTurkSpider(
    PlaywrightTabanScraper
):

    banka_kodu = "kuveytturk"

    render_bekleme = "networkidle"


    # ========================================================
    # POPUP TEMİZLE
    # ========================================================

    def _popup_temizle(
        self
    ):

        try:

            self._sayfa.evaluate(
                POPUP_TEMIZLEME_JS
            )

        except Exception:

            pass


    # ========================================================
    # KATEGORİ LINKLERİNİ TOPLA
    # ========================================================

    def _kategori_linklerini_topla(
        self,
        bolum: str,
        kategori_slug: str
    ) -> set[str]:

        liste_url = (
            f"{TABAN_URL}"
            f"/kampanyalar/"
            f"{bolum}/"
            f"{kategori_slug}"
        )


        print(
            f"  Liste sayfası (render): "
            f"{liste_url}"
        )


        soup = self.getir(
            liste_url
        )


        if soup is None:

            print(
                f"  Liste sayfası açılamadı: "
                f"{liste_url}"
            )

            return set()


        detay_deseni = re.compile(
            rf"^/kampanyalar/"
            rf"{re.escape(bolum)}/"
            rf"{re.escape(kategori_slug)}/"
            rf"[a-z0-9-]+/?$",
            re.IGNORECASE
        )


        self._popup_temizle()


        # ====================================================
        # DAHA FAZLA
        # ====================================================

        tiklama_sayisi = 0


        while True:

            if self._sayfa.is_closed():

                print(
                    "  [UYARI] Sayfa kapanmış, "
                    "döngüden çıkılıyor."
                )

                break


            try:

                buton = self._sayfa.locator(
                    DAHA_FAZLA_SECICI
                ).first


                if not buton.is_visible(
                    timeout=2000
                ):
                    break


                onceki_sayisi = len(
                    self._sayfa.locator(
                        "a[href]"
                    ).all()
                )


                self._popup_temizle()


                try:

                    buton.click(
                        timeout=5000
                    )

                except Exception as tiklama_hatasi:

                    print(
                        f"  İlk tıklama denemesi "
                        f"engellendi "
                        f"({tiklama_hatasi.__class__.__name__}), "
                        f"tekrar deneniyor..."
                    )


                    self._popup_temizle()

                    self._sayfa.wait_for_timeout(
                        500
                    )

                    buton.click(
                        timeout=5000
                    )


                tiklama_sayisi += 1


                self._sayfa.wait_for_timeout(
                    1500
                )


                yeni_sayisi = len(
                    self._sayfa.locator(
                        "a[href]"
                    ).all()
                )


                print(
                    f"  'Daha Fazla' tıklandı "
                    f"({tiklama_sayisi}). "
                    f"Link: "
                    f"{onceki_sayisi} -> "
                    f"{yeni_sayisi}"
                )


                if (
                    yeni_sayisi
                    == onceki_sayisi
                ):
                    break


            except Exception as e:

                print(
                    f"  'Daha Fazla' "
                    f"aranırken/tıklanırken "
                    f"durdu: {e}"
                )

                break


        # ====================================================
        # LINKLER
        # ====================================================

        html = self._sayfa.content()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        detaylar: set[str] = set()


        for a in soup.select(
            "a[href]"
        ):

            href = (
                a["href"]
                .split("?")[0]
                .split("#")[0]
                .rstrip("/")
            )


            if detay_deseni.match(
                href
            ):

                detaylar.add(
                    TABAN_URL + href
                )


        return detaylar


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    def kampanyalari_topla(
        self
    ) -> list[dict]:

        kayitlar: list[dict] = []


        with self.oturum():

            url_bilgi_haritasi: dict[
                str,
                tuple[str, str]
            ] = {}


            # ==================================================
            # BÜTÜN KATEGORİLER
            # ==================================================

            for bolum, kategoriler in BOLUM_KATEGORILERI.items():

                for kategori_adi, kategori_slug in kategoriler.items():

                    print(
                        f"\n=== Bölüm: "
                        f"{bolum} | "
                        f"Kategori: "
                        f"{kategori_adi} "
                        f"({kategori_slug}) ==="
                    )


                    linkler = (
                        self._kategori_linklerini_topla(
                            bolum,
                            kategori_slug
                        )
                    )


                    print(
                        f"  {bolum}/"
                        f"{kategori_adi}: "
                        f"{len(linkler)} "
                        f"tekil kampanya "
                        f"linki bulundu"
                    )


                    for link in linkler:

                        url_bilgi_haritasi.setdefault(
                            link,
                            (
                                bolum,
                                kategori_adi
                            )
                        )


            print(
                f"\nToplam "
                f"{len(url_bilgi_haritasi)} "
                f"tekil kampanya linki bulundu."
            )


            # ==================================================
            # DETAYLAR
            # ==================================================

            for url in sorted(
                url_bilgi_haritasi
            ):

                bolum, kategori = (
                    url_bilgi_haritasi[
                        url
                    ]
                )


                soup = self.getir(
                    url
                )


                if soup is None:
                    continue


                h1 = soup.select_one(
                    "h1"
                )


                icerik = soup.select_one(
                    ".subpage-content"
                )


                # ------------------------------------------------
                # Tarih alanını mümkün olduğunca doğrudan yakala
                # ------------------------------------------------

                tarih_alani = (
                    soup.select_one(
                        ".campaign-date"
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


                # =================================================
                # TARİH
                # =================================================
                #
                # Önce sitenin özel campaign-date alanı.
                # Yoksa içerikten tarih çıkarıyoruz.
                # =================================================

                if tarih_alani is not None:

                    tarih_metni = (
                        self.metin_temizle(
                            tarih_alani
                        )
                    )


                    if not tarih_metni:

                        tarih_metni = (
                            tarih_metnini_bul(
                                icerik
                            )
                        )

                else:

                    tarih_metni = (
                        tarih_metnini_bul(
                            icerik
                        )
                    )


                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": self.metin_temizle(
                            h1
                        ),
                        "ham_metin": self.metin_temizle(
                            icerik
                        ),
                        "bolum": bolum,
                        "kategori": kategori,
                        "tarih_metni": tarih_metni,
                    }
                )


                print(
                    f"    OK "
                    f"[{bolum}/{kategori}]: "
                    f"{kayitlar[-1]['baslik'][:60]} "
                    f"| Tarih: "
                    f"{tarih_metni or 'Bulunamadı'}"
                )


        return kayitlar


    # ========================================================
    # ÜRÜN LİNKLERİNİ TOPLA
    # ========================================================

    def _urun_linklerini_topla(
        self
    ) -> set[str]:

        print(
            f"  Ürün liste sayfası (render): "
            f"{URUN_LISTE_URL}"
        )


        soup = self.getir(
            URUN_LISTE_URL
        )


        if soup is None:

            print(
                f"  Liste sayfası açılamadı: "
                f"{URUN_LISTE_URL}"
            )

            return set()


        self._popup_temizle()


        # ====================================================
        # DAHA FAZLA
        # ====================================================

        try:

            buton = self._sayfa.locator(
                DAHA_FAZLA_SECICI
            ).first


            while buton.is_visible(
                timeout=2000
            ):

                self._popup_temizle()


                try:

                    buton.click(
                        timeout=5000
                    )

                except Exception:

                    self._popup_temizle()

                    self._sayfa.wait_for_timeout(
                        500
                    )

                    buton.click(
                        timeout=5000
                    )


                self._sayfa.wait_for_timeout(
                    1500
                )


        except Exception:

            pass


        # ====================================================
        # LINKLER
        # ====================================================

        html = self._sayfa.content()


        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        detaylar: set[str] = set()


        for a in soup.select(
            "a[href]"
        ):

            href = (
                a["href"]
                .split("?")[0]
                .split("#")[0]
                .replace(
                    TABAN_URL,
                    ""
                )
                .rstrip("/")
            )


            if (
                href
                == "/kendim-icin/finansmanlar"
            ):
                continue


            if URUN_DETAY_DESENI.match(
                href
            ):

                detaylar.add(
                    TABAN_URL + href
                )


        print(
            f"  {len(detaylar)} "
            f"adet aday ürün linki bulundu."
        )


        return detaylar


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    def urunleri_topla(
        self
    ) -> list[dict]:

        kayitlar: list[dict] = []


        with self.oturum():

            urun_linkleri = sorted(
                self._urun_linklerini_topla()
            )


            print(
                f"\nToplam "
                f"{len(urun_linkleri)} "
                f"tekil ürün linki bulundu."
            )


            # ==================================================
            # ÜRÜN DETAYLARI
            # ==================================================

            for url in urun_linkleri:

                print(
                    f"  Ürün taranıyor: "
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


                icerik = soup.select_one(
                    ".subpage-content"
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


                # =================================================
                # BAŞLIK
                # =================================================

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
                        f"(kategori/menü olabilir), "
                        f"atlandı: {url}"
                    )

                    continue


                # =================================================
                # İÇERİK
                # =================================================

                ham_metin = self.metin_temizle(
                    icerik
                )


                if len(
                    ham_metin
                ) < 30:

                    print(
                        f"    İçerik çok kısa, "
                        f"atlandı: {url}"
                    )

                    continue


                # =================================================
                # KATEGORİ
                # =================================================

                kalan = url.replace(
                    f"{URUN_LISTE_URL}/",
                    ""
                )


                yol_parcalari = (
                    kalan.split("/")
                )


                kategori = (
                    yol_parcalari[0]
                    if len(
                        yol_parcalari
                    ) > 1
                    else None
                )


                # =================================================
                # TARİH
                # =================================================

                tarih_metni = (
                    tarih_metnini_bul(
                        icerik
                    )
                )


                # =================================================
                # KAYIT
                # =================================================

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
                    f"    OK "
                    f"[{kategori}]: "
                    f"{baslik[:60]} "
                    f"| Tarih: "
                    f"{tarih_metni or 'Bulunamadı'}"
                )


        return kayitlar


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    from collections import Counter


    spider = KuveytTurkSpider()


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    print(
        "Kuveyt Türk Spider "
        "(Kampanyalar) çalıştırılıyor..."
    )


    kayitlar = (
        spider.kampanyalari_topla()
    )


    spider.kaydet(
        kayitlar
    )


    spider.kaydet_mongoDB(
        kayitlar,
        "kuveyt_katilim"
    )


    # ========================================================
    # KAMPANYA ÖZET
    # ========================================================

    ozet = Counter(
        f"{k['bolum']}/{k['kategori']}"
        for k in kayitlar
    )


    print(
        "\nBölüm/Kategori bazında dağılım:"
    )


    for anahtar, sayi in sorted(
        ozet.items()
    ):

        print(
            f"  {anahtar}: {sayi}"
        )


    # ========================================================
    # TARİHİ OLMAYAN KAMPANYALAR
    # ========================================================

    kampanya_tarihi_olmayan = [
        k
        for k in kayitlar
        if k["tarih_metni"] is None
    ]


    print(
        f"\nTarihi bulunamayan kampanya: "
        f"{len(kampanya_tarihi_olmayan)}"
    )


    for kayit in kampanya_tarihi_olmayan:

        print(
            f"  - {kayit['url']}"
        )


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    print(
        "\nKuveyt Türk Spider "
        "(Ürünler / Bireysel Finansmanlar) "
        "çalıştırılıyor..."
    )


    urun_verileri = (
        spider.urunleri_topla()
    )


    spider.kaydet_mongoDB(
        urun_verileri,
        koleksiyon_adi="kuveyt_katilim_ürün"
    )


    # ========================================================
    # ÜRÜN ÖZET
    # ========================================================

    urun_ozet = Counter(
        k["kategori"]
        for k in urun_verileri
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
    # TARİHİ OLMAYAN ÜRÜNLER
    # ========================================================

    urun_tarihi_olmayan = [
        u
        for u in urun_verileri
        if u["tarih_metni"] is None
    ]


    print(
        f"\nTarihi bulunamayan ürün: "
        f"{len(urun_tarihi_olmayan)}"
    )


    for urun in urun_tarihi_olmayan:

        print(
            f"  - {urun['baslik']}"
            f" | {urun['url']}"
        )