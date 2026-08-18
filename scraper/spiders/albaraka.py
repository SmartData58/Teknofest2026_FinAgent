import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright



# Proje ana dizinini sys.path'e ekleyerek 'ModuleNotFoundError: No module named scraper' hatasını engeller
PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))

from scraper.base_scraper import TabanScraper


TABAN_URL = "https://www.albaraka.com.tr"
LISTE_URL = f"{TABAN_URL}/tr/kampanyalar"

# --- ÜRÜN (Bireysel Finansmanlar) sabitleri ---
URUN_LISTE_URL = f"{TABAN_URL}/tr/bireysel/finansmanlar"
# Ürün detay linkleri /tr/bireysel/finansmanlar/... altında, ama derinlik
# tutarsız: bazıları /finansmanlar/{kategori}/{slug}, bazıları doğrudan
# /finansmanlar/{slug}. Bu yüzden regex ile derinlik zorlamak yerine tüm
# alt linkleri toplayıp içerik/başlık doğrulamasıyla eleme yapıyoruz.
URUN_LINK_DESENI = re.compile(r"^/tr/bireysel/finansmanlar/[a-z0-9-]+(?:/[a-z0-9-]+)?/?$")
GECERSIZ_URUN_BASLIKLARI = {"finansmanlar", "bireysel", "krediler", "finansman"}


class AlbarakaSpider(TabanScraper):
    banka_kodu = "albaraka"

    def _metin_temizle_paragraf(self, metin: str) -> str:
        """Sadece kampanya metnini temizler, gereksiz boşlukları düzeltir."""
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
    # KAMPANYALAR (değişmedi)
    # ------------------------------------------------------------------ #
    def kampanyalari_topla(self) -> list[dict]:
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

                print(f"  Liste sayfasına gidiliyor: {LISTE_URL}")
                page.goto(LISTE_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)

                # Çerez Kapatma
                for secici in [
                    "button:has-text('Kabul Et')",
                    "a:has-text('Kabul Et')",
                    "#onetrust-accept-btn-handler",
                    ".cookie-accept",
                ]:
                    try:
                        if page.locator(secici).first.is_visible(timeout=1500):
                            page.locator(secici).first.click()
                            break
                    except Exception:
                        pass

                # --- "DAHA FAZLA KAMPANYA GÖSTER" BUTONUNA SÜREKLİ TIKLAMA DÖNGÜSÜ ---
                buton_secici = "text='Daha Fazla Kampanya Göster'"

                print("  Tüm kampanyaları yüklemek için butona tıklanıyor...")
                tiklama_sayisi = 0

                while True:
                    try:
                        page.mouse.wheel(0, 1000)
                        page.wait_for_timeout(1000)

                        buton = page.locator(buton_secici).first

                        if buton.is_visible(timeout=2000):
                            buton.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)
                            buton.click()
                            tiklama_sayisi += 1
                            print(f"    -> 'Daha Fazla Kampanya Göster' butonuna {tiklama_sayisi}. kez tıklandı.")
                            page.wait_for_timeout(2000)
                        else:
                            print("  Tüm kampanyalar yüklendi (Buton artık görünmüyor).")
                            break
                    except Exception:
                        break

                # --- LINKLERI TOPLAMA ---
                kart_linkleri = page.locator("a[href*='/kampanyalar/detay/']").evaluate_all(
                    "els => els.map(e => e.getAttribute('href'))"
                )

                benzersiz_linkler = set()
                for href in kart_linkleri:
                    if href:
                        href_clean = href.split("?")[0].split("#")[0].rstrip("/")
                        tam_url = (
                            f"{TABAN_URL}{href_clean}" if href_clean.startswith("/") else href_clean
                        )

                        slug = tam_url.split("/detay/")[-1].strip()
                        if slug and slug != "detay":
                            benzersiz_linkler.add(tam_url)

                kampanya_linkleri = sorted(benzersiz_linkler)
                print(
                    f"\n  Toplam {len(kampanya_linkleri)} adet kampanya adresi bulundu."
                )

                # --- DETAY SAYFALARINI GEZME ---
                for idx, k_url in enumerate(kampanya_linkleri, 1):
                    print(
                        f"  [{idx}/{len(kampanya_linkleri)}] Detay taranıyor: {k_url}"
                    )
                    try:
                        page.goto(k_url, wait_until="domcontentloaded", timeout=25000)
                        page.wait_for_timeout(1000)

                        # 1. Başlık Kontrolü
                        baslik = None
                        h1_locator = page.locator("h1").first
                        if h1_locator.is_visible(timeout=2000):
                            baslik = h1_locator.inner_text().strip()

                        if not baslik or baslik.lower() in ["kampanyalar", "kampanya"]:
                            print(f"    Geçersiz sayfa/başlık, atlandı: {k_url}")
                            continue

                        # 2. İçerik Alımı
                        icerik_secicileri = [
                            ".campaign-detail-content",
                            ".campaign-detail",
                            ".page-left-content",
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

                        kayitlar.append(
                            {
                                "banka": self.banka_kodu,
                                "url": k_url,
                                "baslik": baslik,
                                "ham_metin": ham_metin_temiz,
                                "kategori": None,
                                "tarih_metni": "Kampanya Başlangıç ve Bitiş" if "Başlangıç" in ham_metin_temiz else None,
                            }
                        )
                        print(f"    OK: {baslik[:50]}...")

                    except Exception as k_err:
                        print(f"    Kampanya detay hatası ({k_url}): {k_err}")

            finally:
                browser.close()

        return kayitlar

    # ------------------------------------------------------------------ #
    # ÜRÜNLER (Bireysel Finansmanlar) — YENİ EKLENDİ
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

                print(f"  Liste sayfasına gidiliyor: {URUN_LISTE_URL}")
                page.goto(URUN_LISTE_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)

                # Çerez Kapatma
                for secici in [
                    "button:has-text('Kabul Et')",
                    "a:has-text('Kabul Et')",
                    "#onetrust-accept-btn-handler",
                    ".cookie-accept",
                ]:
                    try:
                        if page.locator(secici).first.is_visible(timeout=1500):
                            page.locator(secici).first.click()
                            break
                    except Exception:
                        pass

                # Bazı liste sayfalarında "Daha Fazla" tarzı buton olabilir;
                # yoksa zararsızca atlanır.
                for buton_metni in ["Daha Fazla Göster", "Tümünü Gör", "Devamını Gör"]:
                    try:
                        buton = page.locator(f"text='{buton_metni}'").first
                        while buton.is_visible(timeout=1500):
                            buton.scroll_into_view_if_needed()
                            page.wait_for_timeout(400)
                            buton.click()
                            page.wait_for_timeout(1500)
                    except Exception:
                        pass

                # --- LINKLERI TOPLAMA ---
                tum_linkler = page.locator("a[href*='/bireysel/finansmanlar/']").evaluate_all(
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

                    if URUN_LINK_DESENI.match(yol) and yol != "/tr/bireysel/finansmanlar":
                        benzersiz_linkler.add(tam_url)

                urun_linkleri = sorted(benzersiz_linkler)
                print(f"\n  Toplam {len(urun_linkleri)} adet aday ürün adresi bulundu.")

                # --- DETAY SAYFALARINI GEZME ---
                for idx, u_url in enumerate(urun_linkleri, 1):
                    print(f"  [{idx}/{len(urun_linkleri)}] Detay taranıyor: {u_url}")
                    try:
                        page.goto(u_url, wait_until="domcontentloaded", timeout=25000)
                        page.wait_for_timeout(1000)

                        baslik = None
                        h1_locator = page.locator("h1").first
                        if h1_locator.is_visible(timeout=2000):
                            baslik = h1_locator.inner_text().strip()

                        if not baslik or baslik.lower() in GECERSIZ_URUN_BASLIKLARI:
                            print(f"    Ürün detayı değil (kategori/liste sayfası olabilir), atlandı: {u_url}")
                            continue

                        icerik_secicileri = [
                            ".campaign-detail-content",
                            ".campaign-detail",
                            ".page-left-content",
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
                            print(f"    İçerik çok kısa, muhtemelen liste sayfası, atlandı: {u_url}")
                            continue

                        # Kategori bilgisini URL yapısından çıkarmayı dener:
                        # /finansmanlar/{kategori}/{slug} varsa kategori dolar,
                        # /finansmanlar/{slug} (tek segment) varsa None kalır.
                        yol_parcalari = u_url.replace(f"{TABAN_URL}/tr/bireysel/finansmanlar/", "").split("/")
                        kategori = yol_parcalari[0] if len(yol_parcalari) > 1 else None

                        kayitlar.append(
                            {
                                "banka": self.banka_kodu,
                                "url": u_url,
                                "baslik": baslik,
                                "ham_metin": ham_metin_temiz,
                                "kategori": kategori,
                                "tarih_metni": None,  # ürün sayfaları genelde tarihsiz
                            }
                        )
                        print(f"    OK: {baslik[:50]}...")

                    except Exception as u_err:
                        print(f"    Ürün detay hatası ({u_url}): {u_err}")

            finally:
                browser.close()

        return kayitlar


if __name__ == "__main__":
    spider = AlbarakaSpider()

    print("Albaraka Spider (Kampanyalar) çalıştırılıyor...")
    kampanya_verileri = spider.kampanyalari_topla()
    scraper = TabanScraper()
    scraper.kaydet_mongoDB(kampanya_verileri, koleksiyon_adi="albaraka")

    print("\nAlbaraka Spider (Ürünler / Finansmanlar) çalıştırılıyor...")
    urun_verileri = spider.urunleri_topla()
    scraper.kaydet_mongoDB(urun_verileri, koleksiyon_adi="albaraka_ürün")
    
    