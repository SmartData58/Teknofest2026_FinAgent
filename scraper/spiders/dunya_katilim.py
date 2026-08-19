import re
import sys
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from playwright.sync_api import sync_playwright

# Proje ana dizinini sys.path'e ekleyerek import hatasını engeller
PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))

from scraper.base_scraper import TabanScraper

TABAN_URL = "https://dunyakatilim.com.tr"
LISTE_URL = f"{TABAN_URL}/kampanyalar"

# --- Sadece "KENDİM İÇİN" Finansmanlar/Ürünler Sabitleri ---
# NOT: Gerçek URL doğrulandı — site "bireysel" değil "kendim-icin" segmentini
# kullanıyor (örn. https://dunyakatilim.com.tr/kendim-icin/finansmanlar).
URUN_LISTE_URL = f"{TABAN_URL}/kendim-icin/finansmanlar"
# Yalnızca /kendim-icin/finansmanlar/ altındaki detay linklerini yakalar.
# Görülen gerçek örnekler: .../finansmanlar/ihtiyac-finansmanlari/ihtiyac-finansmani
#                           .../finansmanlar/konut-finansmanlari/konut-finansmani
#                           .../finansmanlar/arac-finansmanlari/arac-finansmani
KENDIM_ICIN_FINANSMAN_DESENI = re.compile(
    r"^/kendim-icin/finansmanlar/[a-z0-9-]+(?:/[a-z0-9-]+)?/?$"
)
GECERSIZ_URUN_BASLIKLARI = {
    "finansmanlar",
    "kendim için",
    "kendim icin",
    "krediler",
    "finansman",
    "bireysel finansmanlar",
}


class DunyaKatilimSpider(TabanScraper):
    banka_kodu = "dunya_katilim"

    def _metin_temizle_paragraf(self, metin: str) -> str:
        """Sadece kampanya/ürün metnini temizler, gereksiz boşlukları düzeltir."""
        if not metin:
            return ""

        bitis_desenleri = [
            r"Diğer Kampanyalar",
            r"İlginizi Çekebilecek",
            r"Bizi Takip Edin",
            r"Telif Hakları",
            r"©️",
        ]
        for desen in bitis_desenleri:
            bitis_match = re.search(desen, metin, re.IGNORECASE)
            if bitis_match:
                metin = metin[: bitis_match.start()]
                break

        return " ".join(metin.split())

    # ------------------------------------------------------------------ #
    # KAMPANYALAR (Değiştirilmedi)
    # ------------------------------------------------------------------ #
    def kampanyalari_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                slow_mo=500,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()

                print(f"  Liste sayfasına gidiliyor: {LISTE_URL}")
                page.goto(LISTE_URL, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                for secici in [
                    "button:has-text('Kabul Et')",
                    "a:has-text('Kabul Et')",
                    "#onetrust-accept-btn-handler",
                ]:
                    try:
                        if page.locator(secici).first.is_visible(timeout=1500):
                            page.locator(secici).first.click()
                            break
                    except Exception:
                        pass

                daha_fazla_secici = (
                    "a:has-text('Daha Fazla'), button:has-text('Daha Fazla')"
                )
                while True:
                    try:
                        buton = page.locator(daha_fazla_secici).first
                        if buton.is_visible(timeout=2000):
                            onceki_sayi = len(
                                page.locator("a[href*='/kampanyalar/']").all()
                            )
                            buton.click()
                            page.wait_for_timeout(1500)
                            yeni_sayi = len(
                                page.locator("a[href*='/kampanyalar/']").all()
                            )
                            if yeni_sayi == onceki_sayi:
                                break
                        else:
                            break
                    except Exception:
                        break

                tum_hrefler = page.locator("a").evaluate_all(
                    "els => els.map(e => e.getAttribute('href'))"
                )
                benzersiz_linkler = set()

                haric_tutulanlar = {
                    "biten-kampanyalar",
                    "gecmis-kampanyalar",
                    "tum-kampanyalar",
                    "kampanyalar",
                    "avantajli-kurlar",
                }

                for href in tum_hrefler:
                    if href:
                        href_clean = href.split("?")[0].split("#")[0].rstrip("/")
                        tam_url = (
                            f"{TABAN_URL}{href_clean}"
                            if href_clean.startswith("/")
                            else href_clean
                        )

                        if (
                            "/kampanyalar/" in tam_url.lower()
                            and tam_url != LISTE_URL
                        ):
                            slug = tam_url.split("/")[-1].lower()
                            if slug not in haric_tutulanlar:
                                benzersiz_linkler.add(tam_url)

                kampanya_linkleri = sorted(benzersiz_linkler)
                print(
                    f"\n  Toplam {len(kampanya_linkleri)} adet kampanya linki bulundu!"
                )

                for idx, k_url in enumerate(kampanya_linkleri, 1):
                    print(
                        f"  [{idx}/{len(kampanya_linkleri)}] Detay taranıyor: {k_url}"
                    )
                    try:
                        page.goto(k_url, wait_until="networkidle", timeout=25000)
                        page.wait_for_timeout(1000)

                        baslik = None
                        h1_locator = page.locator("h1").first
                        if h1_locator.is_visible(timeout=2000):
                            baslik = h1_locator.inner_text().strip()

                        if not baslik or "süresi dolmuştur" in baslik.lower():
                            print(
                                f"    Süresi dolmuş veya geçersiz sayfa, atlandı: {k_url}"
                            )
                            continue

                        icerik_secicileri = [
                            ".page-left-content",
                            ".campaign-detail-content",
                            ".campaign-detail",
                            "article",
                            ".content",
                        ]

                        aciklama_metni = ""
                        for secici in icerik_secicileri:
                            loc = page.locator(secici).first
                            if loc.is_visible(timeout=1000):
                                aciklama_metni = loc.inner_text().strip()
                                if len(aciklama_metni) > 20:
                                    break

                        if not aciklama_metni:
                            paragraflar = page.locator("p").all_inner_texts()
                            uzun_p_ler = [
                                p.strip() for p in paragraflar if len(p.strip()) > 20
                            ]
                            aciklama_metni = " ".join(uzun_p_ler)

                        ham_metin_temiz = self._metin_temizle_paragraf(aciklama_metni)

                        kayitlar.append(
                            {
                                "banka": self.banka_kodu,
                                "url": k_url,
                                "baslik": baslik,
                                "ham_metin": ham_metin_temiz,
                                "kategori": None,
                                "tarih_metni": None,
                            }
                        )
                        print(f"    OK: {baslik[:50]}...")

                    except Exception as k_err:
                        print(f"    Kampanya detay hatası ({k_url}): {k_err}")

            finally:
                browser.close()

        return kayitlar

    # ------------------------------------------------------------------ #
    # ÜRÜNLER (Sadece "Kendim İçin" Finansmanlar)
    # ------------------------------------------------------------------ #
    def urunleri_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                slow_mo=300,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()

                print(f"  Kendim İçin Finansmanlar sayfasına gidiliyor: {URUN_LISTE_URL}")
                page.goto(URUN_LISTE_URL, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                for secici in [
                    "button:has-text('Kabul Et')",
                    "a:has-text('Kabul Et')",
                    "#onetrust-accept-btn-handler",
                ]:
                    try:
                        if page.locator(secici).first.is_visible(timeout=1500):
                            page.locator(secici).first.click()
                            break
                    except Exception:
                        pass

                # --- SADECE "KENDİM İÇİN" FİNANSMAN LİNKLERİNİ TOPLAMA ---
                tum_linkler = page.locator("a[href*='/kendim-icin/finansmanlar']").evaluate_all(
                    "els => els.map(e => e.getAttribute('href'))"
                )

                benzersiz_linkler = set()
                for href in tum_linkler:
                    if not href:
                        continue

                    href_clean = href.split("?")[0].split("#")[0].rstrip("/")

                    if href_clean.startswith("/"):
                        tam_url = f"{TABAN_URL}{href_clean}"
                        yol = href_clean
                    elif href_clean.startswith(TABAN_URL):
                        tam_url = href_clean
                        yol = href_clean.replace(TABAN_URL, "")
                    else:
                        continue

                    # Yalnızca /kendim-icin/finansmanlar/ altındaki spesifik ürün sayfalarını filtreler
                    if KENDIM_ICIN_FINANSMAN_DESENI.match(yol) and yol != "/kendim-icin/finansmanlar":
                        benzersiz_linkler.add(tam_url)

                kendim_icin_urun_linkleri = sorted(benzersiz_linkler)
                print(f"\n  Toplam {len(kendim_icin_urun_linkleri)} adet 'Kendim İçin' finansman ürünü bulundu.")

                for idx, u_url in enumerate(kendim_icin_urun_linkleri, 1):
                    print(f"  [{idx}/{len(kendim_icin_urun_linkleri)}] Finansman ürünü taranıyor: {u_url}")
                    try:
                        page.goto(u_url, wait_until="networkidle", timeout=25000)
                        page.wait_for_timeout(1000)

                        baslik = None
                        h1_locator = page.locator("h1").first
                        if h1_locator.is_visible(timeout=2000):
                            baslik = h1_locator.inner_text().strip()

                        if not baslik or baslik.lower() in GECERSIZ_URUN_BASLIKLARI:
                            print(f"    Ana kategori veya geçersiz sayfa, atlandı: {u_url}")
                            continue

                        icerik_secicileri = [
                            ".page-left-content",
                            ".campaign-detail-content",
                            ".finance-detail",
                            "article",
                            ".content",
                        ]

                        aciklama_metni = ""
                        for secici in icerik_secicileri:
                            loc = page.locator(secici).first
                            if loc.is_visible(timeout=1000):
                                aciklama_metni = loc.inner_text().strip()
                                if len(aciklama_metni) > 20:
                                    break

                        if not aciklama_metni:
                            paragraflar = page.locator("p").all_inner_texts()
                            uzun_p_ler = [p.strip() for p in paragraflar if len(p.strip()) > 20]
                            aciklama_metni = " ".join(uzun_p_ler)

                        ham_metin_temiz = self._metin_temizle_paragraf(aciklama_metni)

                        if len(ham_metin_temiz) < 30:
                            print(f"    İçerik yetersiz, atlandı: {u_url}")
                            continue

                        # URL üzerindeki alt kategori bilgisini yakalar
                        # (örn: ihtiyac-finansmanlari, konut-finansmanlari, arac-finansmanlari)
                        yol_parcalari = u_url.replace(f"{TABAN_URL}/kendim-icin/finansmanlar/", "").split("/")
                        kategori = yol_parcalari[0] if len(yol_parcalari) > 1 else "Kendim İçin Finansman"

                        kayitlar.append(
                            {
                                "banka": self.banka_kodu,
                                "url": u_url,
                                "baslik": baslik,
                                "ham_metin": ham_metin_temiz,
                                "kategori": kategori,
                                "tarih_metni": None,
                            }
                        )
                        print(f"    OK: {baslik[:50]}...")

                    except Exception as u_err:
                        print(f"    Finansman ürünü detay hatası ({u_url}): {u_err}")

            finally:
                browser.close()

        return kayitlar


if __name__ == "__main__":
    spider = DunyaKatilimSpider()

    print("Dünya Katılım Spider (Kampanyalar) çalıştırılıyor...")
    veriler = spider.kampanyalari_topla()
    scraper = TabanScraper()
    scraper.kaydet_mongoDB(veriler, koleksiyon_adi="dunya_katilim")

    print("\nDünya Katılım Spider (Kendim İçin Finansman Ürünleri) çalıştırılıyor...")
    urun_verileri = spider.urunleri_topla()
    scraper.kaydet_mongoDB(urun_verileri, koleksiyon_adi="dunya_katilim_ürün")