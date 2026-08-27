import os
import re
import sys
from pathlib import Path

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

TABAN_URL = os.getenv("URL_SPIDER_DUNYAKATILIM", "https://dunyakatilim.com.tr")

LISTE_URL = f"{TABAN_URL}/kampanyalar"

URUN_LISTE_URL = (
    f"{TABAN_URL}/kendim-icin/finansmanlar"
)


# ============================================================
# URL DESENLERİ
# ============================================================

KAMPANYA_URL_DESENI = re.compile(
    r"^/kampanyalar/"
    r"[a-z0-9-]+/?$",
    re.IGNORECASE
)


KENDIM_ICIN_FINANSMAN_DESENI = re.compile(
    r"^/kendim-icin/finansmanlar/"
    r"[a-z0-9-]+"
    r"(?:/[a-z0-9-]+)?/?$",
    re.IGNORECASE
)


# ============================================================
# GEÇERSİZ ÜRÜN BAŞLIKLARI
# ============================================================

GECERSIZ_URUN_BASLIKLARI = {
    "finansmanlar",
    "kendim için",
    "kendim icin",
    "krediler",
    "finansman",
    "bireysel finansmanlar",
}


# ============================================================
# İÇERİK SEÇİCİLERİ
# ============================================================

KAMPANYA_ICERIK_SECICILERI = [
    ".page-left-content",
    ".campaign-detail-content",
    ".campaign-detail",
    "article",
    ".content",
    "main",
]


URUN_ICERIK_SECICILERI = [
    ".page-left-content",
    ".finance-detail",
    ".campaign-detail-content",
    ".campaign-detail",
    "article",
    ".content",
    "main",
]


# ============================================================
# SPIDER
# ============================================================

class DunyaKatilimSpider(TabanScraper):

    banka_kodu = "dunya_katilim"


    # ========================================================
    # METİN TEMİZLE
    # ========================================================

    def _metin_temizle(self, metin: str) -> str:

        if not metin:
            return ""

        bitis_desenleri = [
            r"Diğer Kampanyalar",
            r"İlginizi Çekebilecek",
            r"Bizi Takip Edin",
            r"Telif Hakları",
            r"©️",
        ]

        temiz = metin

        for desen in bitis_desenleri:

            eslesme = re.search(
                desen,
                temiz,
                re.IGNORECASE
            )

            if eslesme:

                temiz = temiz[
                    :eslesme.start()
                ]

                break

        return " ".join(
            temiz.split()
        ).strip()


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

                locator = page.locator(
                    secici
                ).first

                if locator.is_visible(
                    timeout=1000
                ):

                    locator.click(
                        timeout=2000
                    )

                    page.wait_for_timeout(
                        500
                    )

                    return

            except Exception:
                continue


    # ========================================================
    # SAYFAYA GİT
    # ========================================================

    def _sayfaya_git(
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

        page.wait_for_timeout(
            1500
        )

        self._cookie_kapat(
            page
        )


    # ========================================================
    # BAŞLIK AL
    # ========================================================

    def _baslik_al(
        self,
        page
    ):

        try:

            locator = page.locator(
                "h1"
            ).first

            if locator.is_visible(
                timeout=2000
            ):

                metin = locator.inner_text(
                    timeout=2000
                ).strip()

                return metin or None

        except Exception:
            pass

        return None


    # ========================================================
    # İÇERİK AL
    # ========================================================

    def _icerik_al(
        self,
        page,
        seciciler
    ) -> str:

        for secici in seciciler:

            try:

                locator = page.locator(
                    secici
                ).first

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


        # ----------------------------------------------------
        # PARAGRAF FALLBACK
        # ----------------------------------------------------

        try:

            paragraflar = page.locator(
                "p"
            ).all_inner_texts()

            paragraflar = [
                p.strip()
                for p in paragraflar
                if len(p.strip()) > 20
            ]

            return " ".join(
                paragraflar
            )

        except Exception:

            return ""


    # ========================================================
    # TARİH REGEX'LERİ
    # ========================================================

    def _sayisal_tarih_regex(self):

        return (
            r"(?:"
            r"(?:0?[1-9]|[12][0-9]|3[01])"
            r"[./-]"
            r"(?:0?[1-9]|1[0-2])"
            r"[./-]"
            r"\d{4}"
            r")"
        )


    def _uzun_tarih_regex(self):

        return (
            r"(?:"
            r"(?:0?[1-9]|[12][0-9]|3[01])"
            r"\s+"
            r"(?:"
            r"Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
            r"Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
            r")"
            r"\s+"
            r"\d{4}"
            r")"
        )


    # ========================================================
    # TARİHLERİ BUL
    # ========================================================

    def _tarihleri_bul(
        self,
        metin: str
    ) -> list[str]:

        if not metin:
            return []

        regex = re.compile(
            rf"""
            (
                {self._sayisal_tarih_regex()}
                |
                {self._uzun_tarih_regex()}
            )
            """,
            re.IGNORECASE | re.VERBOSE
        )

        bulunan = regex.findall(
            metin
        )

        sonuc = []

        for tarih in bulunan:

            if isinstance(
                tarih,
                tuple
            ):

                # Regex gruplarından gerçek tarihi bul
                tarih = next(
                    (
                        x
                        for x in tarih
                        if x
                    ),
                    ""
                )

            tarih = " ".join(
                tarih.split()
            ).strip()

            if (
                tarih
                and tarih not in sonuc
            ):

                sonuc.append(
                    tarih
                )

        return sonuc


    # ========================================================
    # TARİH METNİNİ TEMİZLE
    # ========================================================

    def _tarih_metnini_temizle(
        self,
        metin: str
    ) -> str:

        if not metin:
            return ""

        temiz = " ".join(
            metin.split()
        ).strip()

        # Gereksiz başlıkları kaldır
        temiz = re.sub(
            r"^\s*(?:Tarih|Tarihler)\s*[:\-]?\s*",
            "",
            temiz,
            flags=re.IGNORECASE
        )

        temiz = temiz.strip(
            " :-|"
        )

        return temiz


    # ========================================================
    # YAKIN ELEMENTTEN TARİH AL
    # ========================================================

    def _yakin_element_tarihi_al(
        self,
        locator
    ):

        expressions = [

            # Aynı element
            "el => el.innerText || ''",

            # Parent
            """
            el => el.parentElement
                ? el.parentElement.innerText
                : ''
            """,

            # Parent'ın parent'ı
            """
            el => el.parentElement?.parentElement
                ? el.parentElement.parentElement.innerText
                : ''
            """,

            # Bir üst container
            """
            el => el.closest('div')
                ? el.closest('div').innerText
                : ''
            """,
        ]

        for expression in expressions:

            try:

                metin = locator.evaluate(
                    expression
                )

                if not metin:
                    continue

                metin = " ".join(
                    metin.split()
                )

                tarihler = (
                    self._tarihleri_bul(
                        metin
                    )
                )

                if tarihler:

                    return (
                        " - ".join(
                            tarihler[:2]
                        )
                    )

            except Exception:
                continue

        return None


    # ========================================================
    # KAMPANYA TARİHİ
    # ========================================================

    def _kampanya_tarihi_al(
        self,
        page
    ):
        """
        Dünya Katılım kampanyalarında tarih farklı
        şekillerde bulunabildiği için aşağıdaki öncelik
        sırasıyla aranır:

        1. Bitiş Tarihi
        2. Başlangıç Tarihi
        3. Başlangıç ve Bitiş
        4. Kampanya süresi / geçerlilik metni
        """

        # ====================================================
        # 1. DOĞRUDAN TARİH ETİKETLERİ
        # ====================================================

        etiketler = [
            "Bitiş Tarihi",
            "Başlangıç Tarihi",
            "Başlangıç ve Bitiş Tarihi",
            "Başlangıç ve Bitiş Tarihleri",
            "Kampanya Tarihi",
            "Kampanya Dönemi",
            "Geçerlilik Tarihi",
            "Geçerlilik",
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

                sonuc = (
                    self._yakin_element_tarihi_al(
                        locator
                    )
                )

                if sonuc:
                    return sonuc

            except Exception:
                continue


        # ====================================================
        # 2. ETİKET AYNI ELEMENT İÇİNDE GEÇİYORSA
        # ====================================================

        try:

            body = page.locator(
                "body"
            ).inner_text(
                timeout=3000
            )

            body = " ".join(
                body.split()
            )


            # -----------------------------------------------
            # Bitiş Tarihi: 31 Ağustos 2026
            # -----------------------------------------------

            pattern = re.compile(
                rf"""
                Bitiş\s*Tarihi
                \s*[:\-]?\s*
                (
                    {self._sayisal_tarih_regex()}
                    |
                    {self._uzun_tarih_regex()}
                )
                """,
                re.IGNORECASE | re.VERBOSE
            )

            match = pattern.search(
                body
            )

            if match:

                return (
                    match.group(1)
                    .strip()
                )


            # -----------------------------------------------
            # Başlangıç Tarihi: ...
            # -----------------------------------------------

            pattern = re.compile(
                rf"""
                Başlangıç\s*Tarihi
                \s*[:\-]?\s*
                (
                    {self._sayisal_tarih_regex()}
                    |
                    {self._uzun_tarih_regex()}
                )
                """,
                re.IGNORECASE | re.VERBOSE
            )

            match = pattern.search(
                body
            )

            if match:

                return (
                    match.group(1)
                    .strip()
                )


        except Exception:
            pass


        # ====================================================
        # 3. KAMPANYA SÜRESİ / KAMPANYA KOŞULLARI
        # ====================================================

        try:

            body = page.locator(
                "body"
            ).inner_text(
                timeout=3000
            )

            body = " ".join(
                body.split()
            )


            # Örnek:
            # Kampanya, 10 Haziran 2026 –
            # 31 Ağustos 2026 tarihleri arasında geçerlidir.

            pattern = re.compile(
                rf"""
                (?:
                    Kampanya
                    |
                    kampanya\s+döneminde
                    |
                    kampanya\s+süresi
                )
                .{{0,100}}?
                (
                    {self._uzun_tarih_regex()}
                    |
                    {self._sayisal_tarih_regex()}
                )
                \s*
                (?:-|–|—|ile)
                \s*
                (
                    {self._uzun_tarih_regex()}
                    |
                    {self._sayisal_tarih_regex()}
                )
                """,
                re.IGNORECASE | re.VERBOSE
            )

            match = pattern.search(
                body
            )

            if match:

                baslangic = match.group(
                    1
                )

                bitis = match.group(
                    2
                )

                return (
                    f"{baslangic} - {bitis}"
                )


            # Daha genel tarih aralığı
            tarih_araligi = re.compile(
                rf"""
                (
                    {self._uzun_tarih_regex()}
                    |
                    {self._sayisal_tarih_regex()}
                )
                \s*
                (?:-|–|—)
                \s*
                (
                    {self._uzun_tarih_regex()}
                    |
                    {self._sayisal_tarih_regex()}
                )
                """,
                re.IGNORECASE | re.VERBOSE
            )

            match = tarih_araligi.search(
                body
            )

            if match:

                return (
                    f"{match.group(1)} - "
                    f"{match.group(2)}"
                )

        except Exception:
            pass


        return None


    # ========================================================
    # ÜRÜN TARİHİ
    # ========================================================

    def _urun_tarihi_al(
        self,
        page
    ):
        """
        Ürün sayfalarında rastgele body tarihi alınmaz.

        Sadece gerçekten bir tarih etiketi varsa
        tarih kaydedilir.
        """

        etiketler = [
            "Güncelleme Tarihi",
            "Güncellenme Tarihi",
            "Son Güncelleme",
            "Son Güncelleme Tarihi",
            "Geçerlilik Tarihi",
            "Başlangıç Tarihi",
            "Bitiş Tarihi",
            "Yayın Tarihi",
            "Yayımlanma Tarihi",
            "Başvuru Tarihi",
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

                sonuc = (
                    self._yakin_element_tarihi_al(
                        locator
                    )
                )

                if sonuc:
                    return sonuc

            except Exception:
                continue


        return None


    # ========================================================
    # KAMPANYA URL KONTROLÜ
    # ========================================================

    def _kampanya_url_gecerli_mi(
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

        if not url.startswith(
            TABAN_URL
        ):
            return False

        yol = url.replace(
            TABAN_URL,
            ""
        )

        # Sayfanın kendisi
        if yol == "/kampanyalar":
            return False

        # Geçersiz liste sayfaları
        haric = {
            "/kampanyalar",
            "/kampanyalar/",
            "/kampanyalar/biten-kampanyalar",
            "/kampanyalar/gecmis-kampanyalar",
            "/kampanyalar/tum-kampanyalar",
            "/kampanyalar/avantajli-kurlar",
        }

        if yol.lower() in haric:
            return False

        return bool(
            KAMPANYA_URL_DESENI.match(
                yol
            )
        )


    # ========================================================
    # KAMPANYA LINKLERİNİ TOPLA
    # ========================================================

    def _kampanya_linklerini_topla(
        self,
        page
    ) -> list[str]:

        hrefler = page.locator(
            "a[href*='/kampanyalar/']"
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

            if self._kampanya_url_gecerli_mi(
                href
            ):

                linkler.add(
                    href
                )

        return sorted(
            linkler
        )


    # ========================================================
    # DAHA FAZLA KAMPANYA
    # ========================================================

    def _kampanyalari_yukle(
        self,
        page
    ):

        tiklama = 0

        for _ in range(50):

            try:

                buton = page.locator(
                    "a:has-text('Daha Fazla'), "
                    "button:has-text('Daha Fazla')"
                ).first

                if not buton.is_visible(
                    timeout=1200
                ):
                    break

                onceki = len(
                    self._kampanya_linklerini_topla(
                        page
                    )
                )

                buton.scroll_into_view_if_needed()

                page.wait_for_timeout(
                    300
                )

                buton.click(
                    timeout=2000
                )

                tiklama += 1

                page.wait_for_timeout(
                    1200
                )

                sonraki = len(
                    self._kampanya_linklerini_topla(
                        page
                    )
                )

                print(
                    f"    -> Daha Fazla "
                    f"butonuna {tiklama}. "
                    f"kez tıklandı."
                )

                if sonraki <= onceki:
                    break

            except (
                PlaywrightTimeoutError,
                Exception
            ):
                break


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    def kampanyalari_topla(
        self
    ) -> list[dict]:

        kayitlar = []

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                slow_mo=300,
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

                self._sayfaya_git(
                    page,
                    LISTE_URL
                )

                print(
                    "  Kampanyaların tamamı "
                    "yükleniyor..."
                )

                self._kampanyalari_yukle(
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
                    f"linki bulundu."
                )


                # ==========================================
                # DETAY SAYFALARI
                # ==========================================

                for idx, k_url in enumerate(
                    kampanya_linkleri,
                    1
                ):

                    print(
                        f"  [{idx}/"
                        f"{len(kampanya_linkleri)}] "
                        f"Detay taranıyor: "
                        f"{k_url}"
                    )

                    try:

                        self._sayfaya_git(
                            page,
                            k_url,
                            timeout=25000
                        )


                        # --------------------------------------
                        # BAŞLIK
                        # --------------------------------------

                        baslik = (
                            self._baslik_al(
                                page
                            )
                        )

                        if not baslik:

                            print(
                                "    Başlık bulunamadı, "
                                "atlandı."
                            )

                            continue


                        if (
                            "süresi dolmuştur"
                            in baslik.lower()
                        ):

                            print(
                                "    Süresi dolmuş "
                                "kampanya, atlandı."
                            )

                            continue


                        # --------------------------------------
                        # İÇERİK
                        # --------------------------------------

                        aciklama = (
                            self._icerik_al(
                                page,
                                KAMPANYA_ICERIK_SECICILERI
                            )
                        )

                        ham_metin = (
                            self._metin_temizle(
                                aciklama
                            )
                        )


                        # --------------------------------------
                        # TARİH
                        # --------------------------------------

                        tarih_metni = (
                            self._kampanya_tarihi_al(
                                page
                            )
                        )


                        # --------------------------------------
                        # KAYIT
                        # --------------------------------------

                        kayitlar.append(
                            {
                                "banka": self.banka_kodu,
                                "url": k_url,
                                "baslik": baslik,
                                "ham_metin": ham_metin,
                                "kategori": None,
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
                            f"    Kampanya detay hatası: "
                            f"{k_url}"
                        )

                        print(
                            f"    HATA: {err}"
                        )


            finally:

                context.close()
                browser.close()


        return kayitlar


    # ========================================================
    # ÜRÜN LINKLERİNİ TOPLA
    # ========================================================

    def _urun_linklerini_topla(
        self,
        page
    ) -> list[str]:

        hrefler = page.locator(
            "a[href*='/kendim-icin/finansmanlar']"
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
                TABAN_URL
            ):
                continue

            yol = href.replace(
                TABAN_URL,
                ""
            )

            if not KENDIM_ICIN_FINANSMAN_DESENI.match(
                yol
            ):
                continue

            if yol == (
                "/kendim-icin/finansmanlar"
            ):
                continue

            linkler.add(
                href
            )

        return sorted(
            linkler
        )


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    def urunleri_topla(
        self
    ) -> list[dict]:

        kayitlar = []

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                slow_mo=300,
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
                    f"  Finansmanlar sayfasına "
                    f"gidiliyor: "
                    f"{URUN_LISTE_URL}"
                )

                self._sayfaya_git(
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
                    f"adet finansman ürünü bulundu."
                )


                # ==========================================
                # ÜRÜN DETAYLARI
                # ==========================================

                for idx, u_url in enumerate(
                    urun_linkleri,
                    1
                ):

                    print(
                        f"  [{idx}/"
                        f"{len(urun_linkleri)}] "
                        f"Finansman ürünü "
                        f"taranıyor: {u_url}"
                    )

                    try:

                        self._sayfaya_git(
                            page,
                            u_url,
                            timeout=25000
                        )


                        # --------------------------------------
                        # BAŞLIK
                        # --------------------------------------

                        baslik = (
                            self._baslik_al(
                                page
                            )
                        )

                        if not baslik:

                            print(
                                "    Başlık bulunamadı, "
                                "atlandı."
                            )

                            continue


                        if (
                            baslik.lower()
                            in GECERSIZ_URUN_BASLIKLARI
                        ):

                            print(
                                "    Ana kategori, "
                                "atlandı."
                            )

                            continue


                        # --------------------------------------
                        # İÇERİK
                        # --------------------------------------

                        aciklama = (
                            self._icerik_al(
                                page,
                                URUN_ICERIK_SECICILERI
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
                                "    İçerik yetersiz, "
                                "atlandı."
                            )

                            continue


                        # --------------------------------------
                        # KATEGORİ
                        # --------------------------------------

                        prefix = (
                            f"{TABAN_URL}"
                            "/kendim-icin/"
                            "finansmanlar/"
                        )

                        kalan = u_url.replace(
                            prefix,
                            ""
                        )

                        parcalar = (
                            kalan.split("/")
                        )

                        if len(
                            parcalar
                        ) > 1:

                            kategori = (
                                parcalar[0]
                            )

                        else:

                            kategori = (
                                "Kendim İçin Finansman"
                            )


                        # --------------------------------------
                        # ÜRÜN TARİHİ
                        # --------------------------------------

                        tarih_metni = (
                            self._urun_tarihi_al(
                                page
                            )
                        )


                        # --------------------------------------
                        # KAYIT
                        # --------------------------------------

                        kayitlar.append(
                            {
                                "banka": self.banka_kodu,
                                "url": u_url,
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
                            f"    Finansman ürünü "
                            f"hatası: {u_url}"
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

    spider = DunyaKatilimSpider()

    scraper = TabanScraper()


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    print(
        "Dünya Katılım Spider "
        "(Kampanyalar) çalıştırılıyor..."
    )

    kampanya_verileri = (
        spider.kampanyalari_topla()
    )

    scraper.kaydet_mongoDB(
        kampanya_verileri,
        koleksiyon_adi="dunya_katilim"
    )


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    print(
        "\nDünya Katılım Spider "
        "(Kendim İçin Finansman Ürünleri) "
        "çalıştırılıyor..."
    )

    urun_verileri = (
        spider.urunleri_topla()
    )

    scraper.kaydet_mongoDB(
        urun_verileri,
        koleksiyon_adi="dunya_katilim_ürün"
    )