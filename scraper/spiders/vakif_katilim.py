import os
import re
import sys
import json

from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from bs4 import BeautifulSoup

PROJE_KOK = Path(__file__).resolve().parent.parent.parent

if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))


from scraper.playwright_scraper import PlaywrightTabanScraper


# ============================================================
# SABİTLER
# ============================================================

TABAN_URL = os.getenv("URL_SPIDER_VAKIFKATILIM", "https://www.vakifkatilim.com.tr")


# ============================================================
# KAMPANYALAR
# ============================================================

LISTE_URL = (
    f"{TABAN_URL}/tr/kendim-icin/"
    f"kampanyalar/mevcut-kampanyalar"
)


DETAY_DESENI = re.compile(
    r"^/tr/kendim-icin/kampanyalar/"
    r"detay/[a-z0-9-]+/?$",
    re.IGNORECASE
)


KART_SECICI = "#pagination-page .col-lg-4"

SONRAKI_BUTON_SECICI = (
    "#pagination-button-next"
)

DAHA_FAZLA_METNI = (
    "Daha Fazla Kampanya Gör"
)


# ============================================================
# TARİH
# ============================================================

AYLAR = (
    "Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
    "Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
)


TARIH_YOK_VARSAYILAN = "Belirtilmemiş"


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
# 8 Mayıs - 30 Kasım 2026
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
# 31 Aralık 2026 tarihine kadar
# 31 Aralık 2026'ya kadar
# ------------------------------------------------------------

TARIH_TEK_KADAR_YAZI = re.compile(
    rf"""
    \b
    (?:0?[1-9]|[12][0-9]|3[01])
    \s+
    (?:{AYLAR})
    \s+
    \d{{4}}
    (?:['’][A-Za-zÇĞİÖŞÜçğıöşü]+)?
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


# ------------------------------------------------------------
# 31.12.2026 tarihine kadar
# ------------------------------------------------------------

TARIH_TEK_KADAR_SAYISAL = re.compile(
    r"""
    \b
    (?:0?[1-9]|[12][0-9]|3[01])
    [./-]
    (?:0?[1-9]|1[0-2])
    [./-]
    \d{4}
    (?:['’][A-Za-zÇĞİÖŞÜçğıöşü]+)?
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


# ------------------------------------------------------------
# 31 Aralık 2026
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
# 31.12.2026
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
# ÜRÜNLER / KENDİM İÇİN FİNANSMANLAR
# ============================================================

URUN_LISTE_URL = (
    f"{TABAN_URL}/tr/kendim-icin/finansmanlar"
)


# Bazı ürünler:
#
# /finansmanlar/konut-finansmani
#
# bazıları:
#
# /finansmanlar/konut-finansmanlari/"
# /urun
#
# şeklinde olabilir.
#
# Bu yüzden 1 veya 2 segment desteklenir.

URUN_DETAY_DESENI = re.compile(
    r"^/tr/kendim-icin/finansmanlar/"
    r"[a-z0-9-]+"
    r"(?:/[a-z0-9-]+)?/?$",
    re.IGNORECASE
)


GECERSIZ_URUN_BASLIKLARI = {
    "finansmanlar",
    "kendim için",
    "finansman",
    "finansman ürünleri",
    "finansman ürünleri ve hizmetler",
}


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
# TARİH DESENLERİNE TEK NOKTADAN BAK
# ============================================================

def _desenlerde_ara(
    metin: str
) -> str | None:

    if not metin:
        return None

    metin = normalize_metin(
        metin
    )


    # Öncelik tarih aralıklarında.
    for desen in [
        TARIH_ARALIGI_TAM,
        TARIH_ARALIGI_ILK_YILSIZ,
        TARIH_ARALIGI_SAYISAL,
    ]:

        eslesme = desen.search(
            metin
        )

        if eslesme:
            return eslesme.group(0).strip()


    # Sonra "tarihine kadar".
    for desen in [
        TARIH_TEK_KADAR_YAZI,
        TARIH_TEK_KADAR_SAYISAL,
    ]:

        eslesme = desen.search(
            metin
        )

        if eslesme:
            return eslesme.group(0).strip()


    # Son olarak tek tarih.
    for desen in [
        TARIH_TEK_YAZILI,
        TARIH_TEK_SAYISAL,
    ]:

        eslesme = desen.search(
            metin
        )

        if eslesme:
            return eslesme.group(0).strip()


    return None


# ============================================================
# TARİH METNİ BUL
# ============================================================

def tarih_metnini_bul(
    soup: BeautifulSoup,
    icerik
) -> str | None:
    """
    Kampanya veya ürün sayfasındaki gerçek tarih metnini
    bulur.

    Öncelik:
    1. hero alanı
    2. b / strong alanları
    3. tarih içerebilecek özel alanlar
    4. tüm içerik

    Tarih yoksa None döner.
    """

    if icerik is None:
        return None


    # ========================================================
    # 1. HERO
    # ========================================================

    hero = soup.select_one(
        ".hero-content"
    )


    if hero is not None:

        for etiket in hero.find_all(
            ["b", "strong"]
        ):

            sonuc = _desenlerde_ara(
                etiket.get_text(
                    " ",
                    strip=True
                )
            )

            if sonuc:
                return sonuc


        sonuc = _desenlerde_ara(
            hero.get_text(
                " ",
                strip=True
            )
        )

        if sonuc:
            return sonuc


    # ========================================================
    # 2. B / STRONG
    # ========================================================

    for etiket in icerik.find_all(
        ["b", "strong"]
    ):

        sonuc = _desenlerde_ara(
            etiket.get_text(
                " ",
                strip=True
            )
        )

        if sonuc:
            return sonuc


    # ========================================================
    # 3. OLASI TARİH ALANLARI
    # ========================================================

    tarih_secicileri = [
        ".campaign-date",
        ".campaign-detail-date",
        ".campaign-period",
        ".campaign-duration",
        ".date",
        ".date-text",
        "[class*='date']",
        "[class*='Date']",
    ]


    for secici in tarih_secicileri:

        try:

            alanlar = soup.select(
                secici
            )

            for alan in alanlar:

                metin = alan.get_text(
                    " ",
                    strip=True
                )

                sonuc = _desenlerde_ara(
                    metin
                )

                if sonuc:
                    return sonuc

        except Exception:
            continue


    # ========================================================
    # 4. İÇERİĞİN TAMAMI
    # ========================================================

    sonuc = _desenlerde_ara(
        icerik.get_text(
            " ",
            strip=True
        )
    )

    if sonuc:
        return sonuc


    return None


# ============================================================
# KAMPANYA LİNKLERİNİ TOPLAMA
# ============================================================

class VakifKatilimSpider(
    PlaywrightTabanScraper
):

    banka_kodu = "vakif_katilim"

    render_bekleme = "networkidle"


    # ========================================================
    # KAMPANYA LİNKLERİ
    # ========================================================

    def _liste_linklerini_topla(
        self
    ) -> set[str]:

        detaylar: set[str] = set()


        print(
            f"  Liste sayfası (render): "
            f"{LISTE_URL}"
        )


        soup = self.getir(
            LISTE_URL
        )


        if soup is None:

            print(
                f"  Liste sayfası açılamadı: "
                f"{LISTE_URL}"
            )

            return detaylar


        # ====================================================
        # DAHA FAZLA KAMPANYA
        # ====================================================

        tiklama_sayisi = 0


        while True:

            try:

                buton = (
                    self._sayfa
                    .get_by_text(
                        DAHA_FAZLA_METNI,
                        exact=False
                    )
                    .first
                )


                if (
                    buton.count() == 0
                    or
                    not buton.is_visible(
                        timeout=2000
                    )
                ):

                    break


                buton.scroll_into_view_if_needed(
                    timeout=5000
                )


                self._sayfa.wait_for_timeout(
                    300
                )


                buton.click(
                    timeout=5000
                )


                tiklama_sayisi += 1


                self._sayfa.wait_for_timeout(
                    1500
                )


                print(
                    f"  '{DAHA_FAZLA_METNI}' "
                    f"tıklandı "
                    f"({tiklama_sayisi})."
                )


            except Exception as e:

                print(
                    f"  '{DAHA_FAZLA_METNI}' "
                    f"butonu bulunamadı/"
                    f"tıklanamadı: {e}"
                )

                break


        if tiklama_sayisi == 0:

            print(
                "  'Daha Fazla Kampanya Gör' "
                "butonu bulunamadı; mevcut "
                "linkler taranacak."
            )


        # ====================================================
        # SAYFALAMA
        # ====================================================

        kart_alani_var = True


        try:

            self._sayfa.locator(
                KART_SECICI
            ).first.wait_for(
                state="visible",
                timeout=3000
            )


        except Exception:

            kart_alani_var = False


        sayfa_no = 1


        while True:

            html = self._sayfa.content()


            soup = BeautifulSoup(
                html,
                "html.parser"
            )


            yeni_sayisi = 0


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


                if DETAY_DESENI.match(
                    href
                ):

                    tam_link = (
                        TABAN_URL
                        + href
                    )


                    if tam_link not in detaylar:

                        detaylar.add(
                            tam_link
                        )

                        yeni_sayisi += 1


            print(
                f"  Sayfa {sayfa_no}: "
                f"{yeni_sayisi} yeni link. "
                f"(Toplam: {len(detaylar)})"
            )


            if not kart_alani_var:
                break


            try:

                sonraki_buton = (
                    self._sayfa
                    .locator(
                        SONRAKI_BUTON_SECICI
                    )
                    .first
                )


                if (
                    sonraki_buton.count() > 0
                    and
                    sonraki_buton.is_visible()
                    and
                    sonraki_buton.is_enabled()
                ):

                    sonraki_buton.click()

                    self._sayfa.wait_for_timeout(
                        2000
                    )

                    sayfa_no += 1

                else:

                    print(
                        "  Son sayfaya ulaşıldı, "
                        "link toplama tamamlandı."
                    )

                    break


            except Exception as e:

                print(
                    f"  Sayfalama sırasında "
                    f"sorun: {e}"
                )

                break


        return detaylar


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    def kampanyalari_topla(
        self
    ) -> list[dict]:

        kayitlar: list[dict] = []


        with self.oturum():

            print(
                "=== Bölüm: Kendim İçin "
                "(Kampanyalar) ==="
            )


            kampanyalar = (
                self._liste_linklerini_topla()
            )


            print(
                f"\nToplam "
                f"{len(kampanyalar)} "
                f"tekil kampanya linki bulundu"
            )


            for url in sorted(
                kampanyalar
            ):

                print(
                    f"  Kampanya taranıyor: "
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
                        "section.anchor-menu-section"
                    )
                    or
                    soup.select_one(
                        "section.section-block"
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
                # GÜRÜLTÜLERİ TEMİZLE
                # =================================================

                for gurultu in icerik.select(
                    ".related, "
                    ".similar, "
                    "[class*='ilgin']"
                ):

                    gurultu.decompose()


                # =================================================
                # TARİH
                # =================================================

                tarih_metni = (
                    tarih_metnini_bul(
                        soup,
                        icerik
                    )
                    or
                    TARIH_YOK_VARSAYILAN
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
                    "ham_metin": self.metin_temizle(
                        icerik
                    ),
                    "kategori": "kendim_icin",
                    "tarih_metni": tarih_metni,
                }


                kayitlar.append(
                    kayit
                )


                print(
                    f"    OK: "
                    f"{kayit['baslik'][:60]} "
                    f"| Tarih: "
                    f"{tarih_metni}"
                )


        return kayitlar


    # ========================================================
    # ÜRÜN LİNKLERİ
    # ========================================================

    def _urun_liste_linklerini_topla(
        self
    ) -> set[str]:

        detaylar: set[str] = set()


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

            return detaylar


        elenen_isim_icin: list[str] = []


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


            # ------------------------------------------------
            # İŞİM İÇİN KESİN DIŞARI
            # ------------------------------------------------

            if "isim-icin" in href.lower():

                elenen_isim_icin.append(
                    href
                )

                continue


            # ------------------------------------------------
            # LİSTE SAYFASINI ALMA
            # ------------------------------------------------

            if href == (
                "/tr/kendim-icin/finansmanlar"
            ):

                continue


            # ------------------------------------------------
            # GERÇEK ÜRÜN
            # ------------------------------------------------

            if URUN_DETAY_DESENI.match(
                href
            ):

                detaylar.add(
                    TABAN_URL + href
                )


        print(
            f"  {len(detaylar)} "
            f"adet aday ürün linki bulundu "
            f"(yalnızca kendim-icin)."
        )


        if elenen_isim_icin:

            print(
                f"  {len(set(elenen_isim_icin))} "
                f"adet 'işim için' linki elendi."
            )


        return detaylar


    # ========================================================
    # ÜRÜNLER / FİNANSMANLAR
    # ========================================================

    def urunleri_topla(
        self
    ) -> list[dict]:

        kayitlar: list[dict] = []


        with self.oturum():

            print(
                "=== Bölüm: Kendim İçin "
                "(Finansmanlar) ==="
            )


            urun_linkleri = (
                self._urun_liste_linklerini_topla()
            )


            print(
                f"\nToplam "
                f"{len(urun_linkleri)} "
                f"tekil ürün linki bulundu"
            )


            for url in sorted(
                urun_linkleri
            ):

                # ------------------------------------------------
                # İKİNCİ GÜVENLİK KONTROLÜ
                # ------------------------------------------------

                if "isim-icin" in url.lower():

                    print(
                        "    GÜVENLİK: "
                        "'işim için' linki "
                        f"atlandı: {url}"
                    )

                    continue


                # ------------------------------------------------
                # ÜRÜN DETAYI
                # ------------------------------------------------

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


                icerik = (
                    soup.select_one(
                        "section.anchor-menu-section"
                    )
                    or
                    soup.select_one(
                        "section.section-block"
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


                if (
                    not baslik
                    or
                    baslik.lower()
                    in GECERSIZ_URUN_BASLIKLARI
                ):

                    print(
                        "    Ürün detayı değil "
                        "(menü/liste sayfası olabilir), "
                        f"atlandı: {url}"
                    )

                    continue


                # =================================================
                # GÜRÜLTÜ TEMİZLE
                # =================================================

                for gurultu in icerik.select(
                    ".related, "
                    ".similar, "
                    "[class*='ilgin']"
                ):

                    gurultu.decompose()


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
                        "    İçerik çok kısa, "
                        "muhtemelen liste/menü "
                        f"sayfası, atlandı: {url}"
                    )

                    continue


                # =================================================
                # TARİH
                # =================================================

                tarih_metni = (
                    tarih_metnini_bul(
                        soup,
                        icerik
                    )
                    or
                    TARIH_YOK_VARSAYILAN
                )


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


                if len(
                    yol_parcalari
                ) > 1:

                    kategori = (
                        yol_parcalari[0]
                    )

                else:

                    kategori = None


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
                    f"    OK: "
                    f"{baslik[:60]} "
                    f"| Kategori: "
                    f"{kategori} "
                    f"| Tarih: "
                    f"{tarih_metni}"
                )


        return kayitlar


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # SPIDER
    # ========================================================

    spider = (
        VakifKatilimSpider()
    )


    # ========================================================
    # KAMPANYALAR
    # ========================================================

    print(
        "Vakıf Katılım Spider "
        "(Kendim İçin - Kampanyalar) "
        "çalıştırılıyor..."
    )


    kampanya_kayitlari = (
        spider.kampanyalari_topla()
    )


    spider.kaydet_mongoDB(
        kampanya_kayitlari,
        koleksiyon_adi="vakif_katilim"
    )


    # ========================================================
    # JSON KAMPANYA
    # ========================================================

    with open(
        "vakifkatilim_kampanyalar.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            kampanya_kayitlari,
            f,
            ensure_ascii=False,
            indent=4
        )


    print(
        f"\nToplam "
        f"{len(kampanya_kayitlari)} "
        f"kampanya "
        "'vakifkatilim_kampanyalar.json' "
        "dosyasına kaydedildi."
    )


    # ========================================================
    # TARİHİ BELİRTİLMEMİŞ KAMPANYALAR
    # ========================================================

    tarihi_belirtilmemis = [
        k
        for k in kampanya_kayitlari
        if k["tarih_metni"]
        ==
        TARIH_YOK_VARSAYILAN
    ]


    print(
        f"\n"
        f"{len(tarihi_belirtilmemis)} "
        f"kampanyada tarih belirtilmemiş."
    )


    with open(
        "tarih_bulunamayanlar.txt",
        "w",
        encoding="utf-8"
    ) as f:

        for k in tarihi_belirtilmemis:

            f.write(
                f"URL: {k['url']}\n"
            )

            f.write(
                f"BAŞLIK: "
                f"{k['baslik']}\n"
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
        "Detaylar "
        "'tarih_bulunamayanlar.txt' "
        "dosyasına yazıldı."
    )


    # ========================================================
    # ÜRÜNLER
    # ========================================================

    print(
        "\nVakıf Katılım Spider "
        "(Kendim İçin - Finansmanlar) "
        "çalıştırılıyor..."
    )


    urun_verileri = (
        spider.urunleri_topla()
    )


    spider.kaydet_mongoDB(
        urun_verileri,
        koleksiyon_adi="vakif_katilim_ürün"
    )


    # ========================================================
    # JSON ÜRÜNLER
    # ========================================================

    with open(
        "vakifkatilim_urunler.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            urun_verileri,
            f,
            ensure_ascii=False,
            indent=4
        )


    print(
        f"\nToplam "
        f"{len(urun_verileri)} "
        f"ürün "
        "'vakifkatilim_urunler.json' "
        "dosyasına kaydedildi."
    )


    # ========================================================
    # TARİHİ BELİRTİLMEMİŞ ÜRÜNLER
    # ========================================================

    urun_tarihi_yok = [
        u
        for u in urun_verileri
        if u["tarih_metni"]
        ==
        TARIH_YOK_VARSAYILAN
    ]


    print(
        f"\n"
        f"{len(urun_tarihi_yok)} "
        f"üründe tarih belirtilmemiş."
    )


    for urun in urun_tarihi_yok:

        print(
            f"  - "
            f"{urun['baslik']} "
            f"| {urun['url']}"
        )