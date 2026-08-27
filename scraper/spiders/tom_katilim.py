import os
import re
from datetime import datetime
from pathlib import Path
import sys

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

TABAN_URL = os.getenv("URL_SPIDER_TOMKATILIM", "https://hadiyanindakibanka.com")

LISTE_URL = (
    f"{TABAN_URL}/hadi-kazan/kampanyalar"
)

DETAY_DESENI = re.compile(
    r"^/kampanyalar/[a-z0-9-]+/?$",
    re.IGNORECASE
)

DAHA_FAZLA_METNI = "Daha fazla göster"


# ============================================================
# TÜRKÇE AY İSİMLERİ
# ============================================================

AYLAR = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}


# ============================================================
# TARİH DESENLERİ
# ============================================================

# ------------------------------------------------------------
# 6 Mart - 31 Ağustos 2026
# 6 Mart–31 Ağustos 2026
# 6 Mart — 31 Ağustos 2026
#
# İlk tarafta yıl bulunmayabilir.
# ------------------------------------------------------------

TARIH_ARALIGI_YAZI = re.compile(
    r"""
    \b
    (?P<gun1>\d{1,2})
    \s+
    (?P<ay1>[A-Za-zÇĞİÖŞÜçğıöşü]+)
    (?:\s+(?P<yil1>\d{4}))?
    \s*
    [-–—]
    \s*
    (?P<gun2>\d{1,2})
    \s+
    (?P<ay2>[A-Za-zÇĞİÖŞÜçğıöşü]+)
    \s+
    (?P<yil2>\d{4})
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# 19.01.2026 - 30.09.2026
# 19/01/2026 - 30/09/2026
# 19-01-2026 - 30-09-2026
# ------------------------------------------------------------

TARIH_ARALIGI_SAYISAL = re.compile(
    r"""
    \b
    (?P<gun1>\d{1,2})
    [./-]
    (?P<ay1>\d{1,2})
    [./-]
    (?P<yil1>\d{4})
    \s*
    [-–—]
    \s*
    (?P<gun2>\d{1,2})
    [./-]
    (?P<ay2>\d{1,2})
    [./-]
    (?P<yil2>\d{4})
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# 31 Aralık 2026'ya kadar
# 31 Aralık 2026'ye kadar
# 31 Aralık 2026 tarihine kadar
# 31 Aralık 2026 tarihine dek
# ------------------------------------------------------------

TARIH_TEK_KADAR_YAZI = re.compile(
    r"""
    \b
    (?P<gun>\d{1,2})
    \s+
    (?P<ay>[A-Za-zÇĞİÖŞÜçğıöşü]+)
    \s+
    (?P<yil>\d{4})
    (?:['’][A-Za-zÇĞİÖŞÜçğıöşü]+)?
    \s*
    (?:
        tarihine
        \s+
    )?
    (?:
        kadar
        |
        dek
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# 31.12.2026'ya kadar
# 31.12.2026 tarihine kadar
# ------------------------------------------------------------

TARIH_TEK_KADAR_SAYISAL = re.compile(
    r"""
    \b
    (?P<gun>\d{1,2})
    [./-]
    (?P<ay>\d{1,2})
    [./-]
    (?P<yil>\d{4})
    (?:['’][A-Za-zÇĞİÖŞÜçğıöşü]+)?
    \s*
    (?:
        tarihine
        \s+
    )?
    (?:
        kadar
        |
        dek
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# Tek yazılı tarih
# 31 Ağustos 2026
# ------------------------------------------------------------

TARIH_TEK_YAZI = re.compile(
    r"""
    \b
    (?P<gun>\d{1,2})
    \s+
    (?P<ay>[A-Za-zÇĞİÖŞÜçğıöşü]+)
    \s+
    (?P<yil>\d{4})
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ------------------------------------------------------------
# Tek sayısal tarih
# 31.08.2026
# ------------------------------------------------------------

TARIH_TEK_SAYISAL = re.compile(
    r"""
    \b
    (?P<gun>\d{1,2})
    [./-]
    (?P<ay>\d{1,2})
    [./-]
    (?P<yil>\d{4})
    \b
    """,
    re.IGNORECASE | re.VERBOSE
)


# ============================================================
# METİN TEMİZLEME
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
# TARİH SINIRLARINI PARSE ET
# ============================================================

def _tarih_olustur_yazi(
    gun: str,
    ay_adi: str,
    yil: str
):
    """
    Türkçe ay adından datetime üretir.
    """

    if not gun or not ay_adi or not yil:
        return None

    ay_numarasi = AYLAR.get(
        ay_adi.strip().lower()
    )

    if not ay_numarasi:
        return None

    try:

        return datetime(
            int(yil),
            ay_numarasi,
            int(gun)
        )

    except ValueError:

        return None


def _tarih_olustur_sayisal(
    gun: str,
    ay: str,
    yil: str
):
    """
    Sayısal tarihten datetime üretir.
    """

    try:

        return datetime(
            int(yil),
            int(ay),
            int(gun)
        )

    except (
        TypeError,
        ValueError
    ):

        return None


# ============================================================
# KAMPANYA TARİH BİLGİSİ
# ============================================================

def kampanya_tarih_bilgisi(
    metin: str
):
    """
    Metinden:

        - başlangıç tarihi
        - bitiş tarihi
        - gösterilecek tarih metni

    çıkarır.

    Dönen:

        (baslangic_tarihi, bitis_tarihi, tarih_metni)

    """

    if not metin:
        return None, None, None


    metin = normalize_metin(
        metin
    )


    # ========================================================
    # 1. SAYISAL TARİH ARALIĞI
    # ========================================================

    eslesme = TARIH_ARALIGI_SAYISAL.search(
        metin
    )


    if eslesme:

        baslangic = _tarih_olustur_sayisal(
            eslesme.group("gun1"),
            eslesme.group("ay1"),
            eslesme.group("yil1")
        )


        bitis = _tarih_olustur_sayisal(
            eslesme.group("gun2"),
            eslesme.group("ay2"),
            eslesme.group("yil2")
        )


        if baslangic and bitis:

            tarih_metni = eslesme.group(
                0
            ).strip()

            return (
                baslangic,
                bitis,
                tarih_metni
            )


    # ========================================================
    # 2. YAZILI TARİH ARALIĞI
    # ========================================================

    eslesme = TARIH_ARALIGI_YAZI.search(
        metin
    )


    if eslesme:

        yil1 = (
            eslesme.group("yil1")
            or
            eslesme.group("yil2")
        )


        yil2 = eslesme.group(
            "yil2"
        )


        baslangic = _tarih_olustur_yazi(
            eslesme.group("gun1"),
            eslesme.group("ay1"),
            yil1
        )


        bitis = _tarih_olustur_yazi(
            eslesme.group("gun2"),
            eslesme.group("ay2"),
            yil2
        )


        if baslangic and bitis:

            tarih_metni = eslesme.group(
                0
            ).strip()

            return (
                baslangic,
                bitis,
                tarih_metni
            )


    # ========================================================
    # 3. TEK TARİH + KADAR / DEK
    # ========================================================

    eslesme = TARIH_TEK_KADAR_SAYISAL.search(
        metin
    )


    if eslesme:

        bitis = _tarih_olustur_sayisal(
            eslesme.group("gun"),
            eslesme.group("ay"),
            eslesme.group("yil")
        )


        if bitis:

            tarih_metni = eslesme.group(
                0
            ).strip()

            return (
                None,
                bitis,
                tarih_metni
            )


    # ========================================================
    # 4. TEK TARİH + KADAR / DEK - YAZILI
    # ========================================================

    eslesme = TARIH_TEK_KADAR_YAZI.search(
        metin
    )


    if eslesme:

        bitis = _tarih_olustur_yazi(
            eslesme.group("gun"),
            eslesme.group("ay"),
            eslesme.group("yil")
        )


        if bitis:

            tarih_metni = eslesme.group(
                0
            ).strip()

            return (
                None,
                bitis,
                tarih_metni
            )


    # ========================================================
    # 5. TEK TARİH
    # ========================================================

    eslesme = TARIH_TEK_SAYISAL.search(
        metin
    )


    if eslesme:

        bitis = _tarih_olustur_sayisal(
            eslesme.group("gun"),
            eslesme.group("ay"),
            eslesme.group("yil")
        )


        if bitis:

            tarih_metni = eslesme.group(
                0
            ).strip()

            return (
                None,
                bitis,
                tarih_metni
            )


    eslesme = TARIH_TEK_YAZI.search(
        metin
    )


    if eslesme:

        bitis = _tarih_olustur_yazi(
            eslesme.group("gun"),
            eslesme.group("ay"),
            eslesme.group("yil")
        )


        if bitis:

            tarih_metni = eslesme.group(
                0
            ).strip()

            return (
                None,
                bitis,
                tarih_metni
            )


    # ========================================================
    # TARİH BULUNAMADI
    # ========================================================

    return (
        None,
        None,
        None
    )


# ============================================================
# GERÇEK BİTİŞ TARİHİNİ BUL
# ============================================================

def bitis_tarihini_bul(
    metin: str
) -> datetime | None:

    """
    Sadece kampanyanın bitiş tarihini döndürür.

    Tarih bulunamazsa None.
    """

    _, bitis, _ = (
        kampanya_tarih_bilgisi(
            metin
        )
    )

    return bitis


# ============================================================
# TOM KATILIM SPIDER
# ============================================================

class TomKatilimSpider(
    PlaywrightTabanScraper
):

    banka_kodu = "tom_katilim"

    render_bekleme = "networkidle"


    # ========================================================
    # LINK SAYISI
    # ========================================================

    def _link_sayisini_al(
        self
    ) -> int:

        return len(
            self._sayfa.locator(
                "a[href*='/kampanyalar/']"
            ).all()
        )


    # ========================================================
    # KAMPANYA LINKLERİNİ TOPLA
    # ========================================================

    def _liste_linklerini_topla(
        self
    ) -> set[str]:

        print(
            f"  Liste sayfası (render): "
            f"{LISTE_URL}"
        )


        soup = self.getir(
            LISTE_URL
        )


        if soup is None:

            print(
                "  Liste sayfası açılamadı."
            )

            return set()


        # ====================================================
        # İLK KAMPANYA KARTINI BEKLE
        # ====================================================

        try:

            self._sayfa.locator(
                "a[href*='/kampanyalar/']"
            ).first.wait_for(
                state="attached",
                timeout=10000
            )

        except Exception as e:

            print(
                f"  İlk kampanya kartı "
                f"beklenirken sorun: {e}"
            )


        # ====================================================
        # DAHA FAZLA GÖSTER
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

                buton = (
                    self._sayfa
                    .get_by_text(
                        DAHA_FAZLA_METNI,
                        exact=False
                    )
                    .first
                )


                if buton.count() == 0:

                    print(
                        "  'Daha fazla göster' "
                        "butonu artık DOM'da yok, "
                        "döngü bitti."
                    )

                    break


                onceki_sayisi = (
                    self._link_sayisini_al()
                )


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


                yeni_sayisi = (
                    self._link_sayisini_al()
                )


                print(
                    f"  '{DAHA_FAZLA_METNI}' "
                    f"tıklandı "
                    f"({tiklama_sayisi}). "
                    f"Kampanya linki: "
                    f"{onceki_sayisi} -> "
                    f"{yeni_sayisi}"
                )


                if (
                    yeni_sayisi
                    == onceki_sayisi
                ):

                    print(
                        "  Link sayısı artmadı, "
                        "tüm kampanyalar "
                        "yüklenmiş olmalı."
                    )

                    break


            except Exception as e:

                print(
                    f"  Buton tıklanırken "
                    f"sorun oluştu: {e}"
                )

                break


        # ====================================================
        # HTML
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
                .strip()
                .split("?")[0]
                .split("#")[0]
            )


            href = (
                href
                .replace(
                    TABAN_URL,
                    ""
                )
                .replace(
                    "https://tombankhadi.com",
                    ""
                )
            )


            if DETAY_DESENI.match(
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


        bugun = datetime.now()


        with self.oturum():

            detaylar = (
                self._liste_linklerini_topla()
            )


            print(
                f"  {len(detaylar)} "
                f"tekil kampanya "
                f"linki bulundu"
            )


            # ==================================================
            # DETAY SAYFALARI
            # ==================================================

            for url in sorted(
                detaylar
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


                # =================================================
                # BAŞLIK
                # =================================================

                h1 = (
                    soup.select_one(
                        "main h1"
                    )
                    or
                    soup.select_one(
                        "h1"
                    )
                )


                # =================================================
                # İÇERİK
                # =================================================

                icerik = soup.select_one(
                    "main"
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
                # KAMPANYA İÇERİĞİNDE GÜRÜLTÜ TEMİZLE
                # =================================================

                for gurultu in icerik.select(
                    "section.campaigns"
                ):

                    gurultu.decompose()


                # =================================================
                # HAM METİN
                # =================================================

                ham_metin = (
                    self.metin_temizle(
                        icerik
                    )
                )


                # =================================================
                # KAMPANYA TARİHİ
                # =================================================

                (
                    baslangic_tarihi,
                    bitis_tarihi,
                    tarih_metni
                ) = kampanya_tarih_bilgisi(
                    ham_metin
                )


                # =================================================
                # SÜRESİ GEÇMİŞ Mİ?
                # =================================================

                if (
                    bitis_tarihi is not None
                    and
                    bitis_tarihi < bugun
                ):

                    print(
                        "    SÜRESİ GEÇMİŞ "
                        f"({bitis_tarihi.strftime('%d.%m.%Y')}), "
                        f"atlandı: {url}"
                    )

                    continue


                # =================================================
                # KAYIT
                # =================================================

                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": self.metin_temizle(
                            h1
                        ),
                        "ham_metin": ham_metin,
                        "kategori": None,

                        # Artık yalnızca Bitiş tarihi değil,
                        # kampanyanın süre ifadesi tutuluyor.
                        "tarih_metni": tarih_metni,
                    }
                )


                # =================================================
                # TERMINAL
                # =================================================

                if tarih_metni:

                    if baslangic_tarihi and bitis_tarihi:

                        etiket = (
                            f"Süre: "
                            f"{tarih_metni}"
                        )

                    elif bitis_tarihi:

                        etiket = (
                            f"Bitiş: "
                            f"{bitis_tarihi.strftime('%d.%m.%Y')}"
                        )

                    else:

                        etiket = (
                            f"Tarih: "
                            f"{tarih_metni}"
                        )

                else:

                    etiket = (
                        "Tarih: bulunamadı"
                    )


                print(
                    f"    OK: "
                    f"{kayitlar[-1]['baslik'][:60]} "
                    f"| {etiket}"
                )


        return kayitlar


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    spider = TomKatilimSpider()


    print(
        "TOM Katılım Spider "
        "(Kampanyalar) çalıştırılıyor..."
    )


    kayitlar = (
        spider.kampanyalari_topla()
    )


    # ========================================================
    # DOSYAYA KAYDET
    # ========================================================

    spider.kaydet(
        kayitlar
    )


    # ========================================================
    # MONGODB
    # ========================================================

    spider.kaydet_mongoDB(
        kayitlar,
        "tom_katilim"
    )


    # ========================================================
    # TARİHİ OLMAYANLAR
    # ========================================================

    tarihi_olmayanlar = [
        k
        for k in kayitlar
        if k["tarih_metni"] is None
    ]


    print(
        f"\n{len(tarihi_olmayanlar)} "
        f"kampanyada tarih bulunamadı:"
    )


    if tarihi_olmayanlar:

        with open(
            "tom_tarih_bulunamayanlar.txt",
            "w",
            encoding="utf-8"
        ) as f:

            for k in tarihi_olmayanlar:

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
            "'tom_tarih_bulunamayanlar.txt' "
            "dosyasına yazıldı."
        )