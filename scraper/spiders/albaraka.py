import os
import re
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


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

TABAN_URL = os.getenv("URL_SPIDER_ALBARAKA", "https://www.albaraka.com.tr")

LISTE_URL = f"{TABAN_URL}/tr/kampanyalar"

URUN_LISTE_URL = (
    f"{TABAN_URL}/tr/bireysel/finansmanlar"
)


# Sadece gerçek kampanya detay URL'lerini kabul et.
KAMPANYA_URL_DESENI = re.compile(
    r"^https://www\.albaraka\.com\.tr/"
    r"tr/kampanyalar/detay/"
    r"[^/?#]+/?$",
    re.IGNORECASE
)


# Ürün detay URL'leri
URUN_LINK_DESENI = re.compile(
    r"^/tr/bireysel/finansmanlar/"
    r"[a-z0-9-]+"
    r"(?:/[a-z0-9-]+)?/?$",
    re.IGNORECASE
)


GECERSIZ_URUN_BASLIKLARI = {
    "finansmanlar",
    "bireysel",
    "krediler",
    "finansman",
}


# ============================================================
# CSS SEÇİCİLERİ
# ============================================================

ICERIK_SECICILERI = [
    ".campaign-detail-content",
    ".campaign-detail",
    ".page-left-content",
    "article",
    "main",
]


# ============================================================
# ANA SINIF
# ============================================================

class AlbarakaSpider(TabanScraper):

    banka_kodu = "albaraka"


    # ========================================================
    # GENEL METİN TEMİZLEME
    # ========================================================

    def _metin_temizle(self, metin: Optional[str]) -> str:

        if not metin:
            return ""

        bitis_desenleri = [
            r"Diğer Kampanyalar",
            r"İlginizi Çekebilecek",
            r"Bizi Takip Edin",
            r"Telif Hakları",
            r"©",
        ]

        temiz = metin

        for desen in bitis_desenleri:

            eslesme = re.search(
                desen,
                temiz,
                re.IGNORECASE
            )

            if eslesme:
                temiz = temiz[:eslesme.start()]
                break

        return " ".join(temiz.split()).strip()


    # ========================================================
    # COOKIE
    # ========================================================

    def _cookie_kapat(self, page):

        seciciler = [
            "button:has-text('Kabul Et')",
            "a:has-text('Kabul Et')",
            "#onetrust-accept-btn-handler",
            ".cookie-accept",
        ]

        for secici in seciciler:

            try:

                locator = page.locator(secici).first

                if locator.is_visible(timeout=1000):

                    locator.click(
                        timeout=2000
                    )

                    page.wait_for_timeout(500)

                    return

            except Exception:
                continue


    # ========================================================
    # ORTAK SAYFA BEKLEME
    # ========================================================

    def _sayfayi_hazirla(
        self,
        page,
        url: str,
        timeout: int = 30000
    ):

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout
        )

        page.wait_for_timeout(1200)

        self._cookie_kapat(page)


    # ========================================================
    # İÇERİK AL
    # ========================================================

    def _icerik_al(self, page) -> str:

        for secici in ICERIK_SECICILERI:

            try:

                locator = page.locator(secici).first

                if not locator.is_visible(
                    timeout=800
                ):
                    continue

                metin = locator.inner_text(
                    timeout=2000
                ).strip()

                if len(metin) > 30:
                    return metin

            except Exception:
                continue


        # Fallback
        try:

            paragraflar = page.locator(
                "p"
            ).all_inner_texts()

            paragraflar = [
                p.strip()
                for p in paragraflar
                if len(p.strip()) > 20
            ]

            return " ".join(paragraflar)

        except Exception:
            return ""


    # ========================================================
    # BAŞLIK AL
    # ========================================================

    def _baslik_al(self, page) -> Optional[str]:

        try:

            h1 = page.locator("h1").first

            if h1.is_visible(timeout=2000):

                baslik = h1.inner_text().strip()

                return baslik or None

        except Exception:
            pass

        return None


    # ========================================================
    # TARİH AYIKLAMA
    # ========================================================

    def _tarihleri_bul(self, metin: str) -> list[str]:
        """
        Verilen küçük metin parçası içerisinden tarihleri bulur.

        Desteklenen örnekler:

        01.08.2026
        01/08/2026
        01-08-2026
        1 Ağustos 2026
        """

        if not metin:
            return []

        tarih_regex = re.compile(
            r"""
            (?:
                \b
                (?:0?[1-9]|[12][0-9]|3[01])
                [./-]
                (?:0?[1-9]|1[0-2])
                [./-]
                \d{4}
                \b

                |

                \b
                (?:0?[1-9]|[12][0-9]|3[01])
                \s+
                (?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|
                Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)
                \s+
                \d{4}
                \b
            )
            """,
            re.IGNORECASE | re.VERBOSE
        )

        bulunan = tarih_regex.findall(
            metin
        )

        sonuc = []

        for tarih in bulunan:

            tarih = " ".join(
                tarih.split()
            ).strip()

            if tarih and tarih not in sonuc:
                sonuc.append(tarih)

        return sonuc


    # ========================================================
    # KAMPANYA TARİHİ
    # ========================================================

    def _kampanya_tarihi_al(self, page) -> Optional[str]:
        """
        Kampanyanın üst kısmındaki gerçek
        'Kampanya Başlangıç ve Bitiş' alanını bulur.

        Sayfanın bütün body'sini taramaz.
        Böylece içerikte tekrar eden tarihler alınmaz.
        """

        # ----------------------------------------------------
        # 1. Tam etiket
        # ----------------------------------------------------

        etiketler = [
            "Kampanya Başlangıç ve Bitiş",
            "Kampanya Başlangıç ve Bitiş Tarihi",
            "Kampanya Başlangıç ve Bitiş Tarihleri",
            "Başlangıç ve Bitiş",
            "Başlangıç ve Bitiş Tarihi",
            "Başlangıç – Bitiş Tarihleri",
            "Başlangıç - Bitiş Tarihleri",
        ]


        for etiket in etiketler:

            try:

                locator = page.get_by_text(
                    etiket,
                    exact=True
                ).first

                if not locator.is_visible(
                    timeout=1000
                ):
                    continue


                # ------------------------------------------------
                # Etiketin bulunduğu elementin parent'ı
                # ------------------------------------------------

                metinler = []

                for expression in [
                    "el => el.parentElement?.innerText || ''",
                    """
                    el => el.parentElement?.parentElement?.innerText || ''
                    """,
                ]:

                    try:

                        parent_metin = locator.evaluate(
                            expression
                        )

                        if parent_metin:

                            parent_metin = (
                                " ".join(
                                    parent_metin.split()
                                )
                            )

                            metinler.append(
                                parent_metin
                            )

                    except Exception:
                        continue


                # ------------------------------------------------
                # Yakındaki text node'lardan tarih bul
                # ------------------------------------------------

                for aday in metinler:

                    tarihler = self._tarihleri_bul(
                        aday
                    )

                    if tarihler:

                        # En temiz sonuç:
                        if len(tarihler) == 1:
                            return tarihler[0]

                        return " - ".join(
                            tarihler[:2]
                        )


            except Exception:
                continue


        # ----------------------------------------------------
        # 2. Daha dayanıklı XPath fallback
        # ----------------------------------------------------

        try:

            xpath = (
                "//*["
                "contains("
                "translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ',"
                "'abcdefghijklmnopqrstuvwxyzçğiöşü'),"
                "'kampanya başlangıç ve bitiş'"
                ")"
                "]"
            )

            adaylar = page.locator(
                f"xpath={xpath}"
            )

            adet = adaylar.count()

            for i in range(min(adet, 10)):

                try:

                    locator = adaylar.nth(i)

                    metin = locator.inner_text(
                        timeout=1000
                    )

                    tarihler = self._tarihleri_bul(
                        metin
                    )

                    if tarihler:

                        if len(tarihler) == 1:
                            return tarihler[0]

                        return " - ".join(
                            tarihler[:2]
                        )

                except Exception:
                    continue

        except Exception:
            pass


        # ----------------------------------------------------
        # 3. Son fallback:
        # içerik içinde "Kampanya Başlangıç..."
        # başlığı + hemen arkasındaki ilk tarih aralığı
        # ----------------------------------------------------

        try:

            body = page.locator(
                "body"
            ).inner_text(
                timeout=2000
            )

            pattern = re.compile(
                r"Kampanya\s+Başlangıç\s+ve\s+Bitiş"
                r"(?:\s+Tarihi|\s+Tarihleri)?"
                r"\s*"
                r"([^.\n]{0,100}?\d{4}[^.\n]{0,30})",
                re.IGNORECASE
            )

            eslesme = pattern.search(body)

            if eslesme:

                parca = eslesme.group(1)

                tarihler = self._tarihleri_bul(
                    parca
                )

                if tarihler:

                    return " - ".join(
                        tarihler[:2]
                    )

        except Exception:
            pass


        return None


    # ========================================================
    # ÜRÜN TARİHİ
    # ========================================================

    def _urun_tarihi_al(self, page) -> Optional[str]:
        """
        Ürünlerde kampanya tarihi olmadığı için
        yalnızca gerçekten mevcut olan tarih alanlarını arar.

        Örn:
        Güncelleme Tarihi
        Son Güncelleme
        Geçerlilik Tarihi

        Sayfada bunlar yoksa None döndürür.
        """

        etiketler = [
            "Güncelleme Tarihi",
            "Güncellenme Tarihi",
            "Son Güncelleme",
            "Son Güncelleme Tarihi",
            "Geçerlilik Tarihi",
            "Başlangıç Tarihi",
            "Bitiş Tarihi",
        ]

        for etiket in etiketler:

            try:

                locator = page.get_by_text(
                    etiket,
                    exact=True
                ).first

                if not locator.is_visible(
                    timeout=700
                ):
                    continue


                aday_parentlar = [
                    "el => el.parentElement?.innerText || ''",
                    """
                    el => el.parentElement?.parentElement?.innerText || ''
                    """,
                ]

                for expression in aday_parentlar:

                    try:

                        metin = locator.evaluate(
                            expression
                        )

                        tarihler = self._tarihleri_bul(
                            metin
                        )

                        if tarihler:

                            if len(tarihler) == 1:
                                return tarihler[0]

                            return " - ".join(
                                tarihler[:2]
                            )

                    except Exception:
                        continue

            except Exception:
                continue


        return None


    # ========================================================
    # KAMPANYA LINK FİLTRELEME
    # ========================================================

    def _kampanya_linki_gecerli_mi(
        self,
        url: str
    ) -> bool:

        if not url:
            return False

        url = (
            url
            .split("?")[0]
            .split("#")[0]
            .rstrip("/")
        )

        # Sosyal medya / paylaşım linkleri
        yasak_domainler = (
            "twitter.com",
            "x.com",
            "facebook.com",
            "linkedin.com",
            "instagram.com",
            "whatsapp.com",
        )

        url_lower = url.lower()

        if any(
            domain in url_lower
            for domain in yasak_domainler
        ):
            return False

        # Sadece Albaraka kampanya detayları
        if not url.startswith(
            f"{TABAN_URL}/tr/kampanyalar/detay/"
        ):
            return False

        return bool(
            KAMPANYA_URL_DESENI.match(url)
        )


    # ========================================================
    # KAMPANYA LİNKLERİNİ TOPLA
    # ========================================================

    def _kampanya_linklerini_topla(
        self,
        page
    ) -> list[str]:

        hrefler = page.locator(
            "a[href*='/kampanyalar/detay/']"
        ).evaluate_all(
            "els => els.map(e => e.href)"
        )

        linkler = set()

        for href in hrefler:

            if not href:
                continue

            href = (
                href
                .split("?")[0]
                .split("#")[0]
                .rstrip("/")
            )

            if self._kampanya_linki_gecerli_mi(
                href
            ):
                linkler.add(href)

        return sorted(linkler)


    # ========================================================
    # TÜM KAMPANYALARI YÜKLE
    # ========================================================

    def _tum_kampanyalari_yukle(
        self,
        page
    ):

        buton_secici = (
            "text='Daha Fazla Kampanya Göster'"
        )

        tiklama_sayisi = 0

        while True:

            try:

                buton = page.locator(
                    buton_secici
                ).first

                if not buton.is_visible(
                    timeout=1500
                ):
                    break

                buton.scroll_into_view_if_needed()

                page.wait_for_timeout(400)

                buton.click(
                    timeout=2000
                )

                tiklama_sayisi += 1

                print(
                    f"    -> 'Daha Fazla Kampanya "
                    f"Göster' "
                    f"{tiklama_sayisi}. kez tıklandı."
                )

                page.wait_for_timeout(1800)

            except (
                PlaywrightTimeoutError,
                Exception
            ):
                break


    # ========================================================
    # KAMPANYALARI TOPLA
    # ========================================================

    def kampanyalari_topla(self) -> list[dict]:

        kayitlar = []

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                slow_mo=200,
                args=[
                    "--disable-blink-features="
                    "AutomationControlled"
                ]
            )

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={
                    "width": 1920,
                    "height": 1080
                }
            )

            page = context.new_page()

            try:

                print(
                    f"  Liste sayfasına gidiliyor: "
                    f"{LISTE_URL}"
                )

                self._sayfayi_hazirla(
                    page,
                    LISTE_URL
                )

                print(
                    "  Tüm kampanyaları yüklemek "
                    "için butona tıklanıyor..."
                )

                self._tum_kampanyalari_yukle(
                    page
                )

                kampanya_linkleri = (
                    self._kampanya_linklerini_topla(
                        page
                    )
                )

                print(
                    f"\n  Toplam "
                    f"{len(kampanya_linkleri)} "
                    f"adet gerçek kampanya "
                    f"adresi bulundu."
                )


                for idx, url in enumerate(
                    kampanya_linkleri,
                    1
                ):

                    print(
                        f"  [{idx}/"
                        f"{len(kampanya_linkleri)}] "
                        f"Detay taranıyor: {url}"
                    )

                    try:

                        self._sayfayi_hazirla(
                            page,
                            url,
                            timeout=25000
                        )

                        baslik = self._baslik_al(
                            page
                        )

                        if (
                            not baslik
                            or baslik.lower()
                            in {
                                "kampanyalar",
                                "kampanya"
                            }
                        ):

                            print(
                                "    Geçersiz "
                                "kampanya sayfası, atlandı."
                            )

                            continue


                        # ----------------------------------------
                        # TARİH
                        # ----------------------------------------

                        tarih_metni = (
                            self._kampanya_tarihi_al(
                                page
                            )
                        )


                        # ----------------------------------------
                        # İÇERİK
                        # ----------------------------------------

                        aciklama = self._icerik_al(
                            page
                        )

                        ham_metin = (
                            self._metin_temizle(
                                aciklama
                            )
                        )


                        kayit = {
                            "banka": self.banka_kodu,
                            "url": url,
                            "baslik": baslik,
                            "ham_metin": ham_metin,
                            "kategori": None,
                            "tarih_metni": tarih_metni,
                        }

                        kayitlar.append(
                            kayit
                        )


                        print(
                            f"    OK: "
                            f"{baslik[:60]}..."
                        )

                        print(
                            f"    TARİH: "
                            f"{tarih_metni or 'Bulunamadı'}"
                        )


                    except Exception as err:

                        print(
                            f"    Kampanya detay hatası: "
                            f"{url}"
                        )

                        print(
                            f"    HATA: {err}"
                        )


            finally:

                context.close()
                browser.close()


        return kayitlar


    # ========================================================
    # ÜRÜN LİNKLERİNİ TOPLA
    # ========================================================

    def _urun_linklerini_topla(
        self,
        page
    ) -> list[str]:

        hrefler = page.locator(
            "a[href*='/bireysel/finansmanlar/']"
        ).evaluate_all(
            "els => els.map(e => e.href)"
        )

        linkler = set()

        for href in hrefler:

            if not href:
                continue

            href = (
                href
                .split("?")[0]
                .split("#")[0]
                .rstrip("/")
            )

            if not href.startswith(
                f"{TABAN_URL}/tr/bireysel/finansmanlar/"
            ):
                continue

            yol = href.replace(
                TABAN_URL,
                ""
            )

            if URUN_LINK_DESENI.match(
                yol
            ):

                if yol != (
                    "/tr/bireysel/finansmanlar"
                ):

                    linkler.add(href)

        return sorted(linkler)


    # ========================================================
    # ÜRÜNLERİ TOPLA
    # ========================================================

    def urunleri_topla(self) -> list[dict]:

        kayitlar = []

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                slow_mo=200,
                args=[
                    "--disable-blink-features="
                    "AutomationControlled"
                ]
            )

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={
                    "width": 1920,
                    "height": 1080
                }
            )

            page = context.new_page()

            try:

                print(
                    f"  Liste sayfasına gidiliyor: "
                    f"{URUN_LISTE_URL}"
                )

                self._sayfayi_hazirla(
                    page,
                    URUN_LISTE_URL
                )

                urun_linkleri = (
                    self._urun_linklerini_topla(
                        page
                    )
                )

                print(
                    f"\n  Toplam "
                    f"{len(urun_linkleri)} "
                    f"adet aday ürün adresi bulundu."
                )


                for idx, url in enumerate(
                    urun_linkleri,
                    1
                ):

                    print(
                        f"  [{idx}/"
                        f"{len(urun_linkleri)}] "
                        f"Detay taranıyor: {url}"
                    )

                    try:

                        self._sayfayi_hazirla(
                            page,
                            url,
                            timeout=25000
                        )

                        baslik = self._baslik_al(
                            page
                        )

                        if (
                            not baslik
                            or baslik.lower()
                            in GECERSIZ_URUN_BASLIKLARI
                        ):

                            print(
                                "    Ürün detayı değil, "
                                "atlandı."
                            )

                            continue


                        aciklama = (
                            self._icerik_al(
                                page
                            )
                        )

                        ham_metin = (
                            self._metin_temizle(
                                aciklama
                            )
                        )


                        if len(
                            ham_metin
                        ) < 30:

                            print(
                                "    İçerik çok kısa, "
                                "atlandı."
                            )

                            continue


                        # ----------------------------------------
                        # KATEGORİ
                        # ----------------------------------------

                        prefix = (
                            f"{TABAN_URL}"
                            "/tr/bireysel/"
                            "finansmanlar/"
                        )

                        yol = url.replace(
                            prefix,
                            ""
                        )

                        parcalar = yol.split("/")

                        kategori = (
                            parcalar[0]
                            if len(parcalar) > 1
                            else None
                        )


                        # ----------------------------------------
                        # ÜRÜN TARİHİ
                        # ----------------------------------------

                        tarih_metni = (
                            self._urun_tarihi_al(
                                page
                            )
                        )


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
                            f"{baslik[:60]}..."
                        )

                        print(
                            f"    TARİH: "
                            f"{tarih_metni or 'Bulunamadı'}"
                        )


                    except Exception as err:

                        print(
                            f"    Ürün detay hatası: "
                            f"{url}"
                        )

                        print(
                            f"    HATA: {err}"
                        )


            finally:

                context.close()
                browser.close()


        return kayitlar


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    spider = AlbarakaSpider()

    # --------------------------------------------------------
    # KAMPANYALAR
    # --------------------------------------------------------

    print(
        "Albaraka Spider (Kampanyalar) çalıştırılıyor..."
    )

    kampanya_verileri = (
        spider.kampanyalari_topla()
    )

    scraper = TabanScraper()

    scraper.kaydet_mongoDB(
        kampanya_verileri,
        koleksiyon_adi="albaraka"
    )


    # --------------------------------------------------------
    # ÜRÜNLER
    # --------------------------------------------------------

    print(
        "\nAlbaraka Spider "
        "(Ürünler / Finansmanlar) çalıştırılıyor..."
    )

    urun_verileri = (
        spider.urunleri_topla()
    )

    scraper.kaydet_mongoDB(
        urun_verileri,
        koleksiyon_adi="albaraka_ürün"
    )