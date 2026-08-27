import os
from contextlib import contextmanager

from bs4 import BeautifulSoup

# scraper/db_helper.py
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from scraper.base_scraper import TabanScraper, VARSAYILAN_USER_AGENT

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    user = os.getenv("MONGO_USER", "admin")
    password = os.getenv("MONGO_PASSWORD", "")
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    if password:
        return f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
    return f"mongodb://{host}:{port}/?authSource=admin"

mongo_uri: str = _get_mongo_uri()
db_name: str = os.getenv("MONGO_DB_NAME", os.getenv("CAMPAIGN_DB", "smartdata"))

# Gerçek Chrome'a daha yakın bir imza: TSPD gibi bot korumaları eski/tutarsız
# User-Agent'ları eler. Chromium sürümüyle uyumlu tutulur.
PW_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)

# navigator.webdriver vb. otomasyon izlerini maskeleyen açılış betiği.
# Bot korumaları bu bayrakları okur; gerçek tarayıcıda bulunmazlar.
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = {runtime: {}};
"""


class PlaywrightTabanScraper(TabanScraper):
    """JS ile yüklenen siteler için Chromium tabanlı temel spider.

    Statik TabanScraper ile AYNI arayüz — tek fark getir()'in tarayıcıyla
    render etmesi. Alt sınıf yine kampanyalari_topla() yazar ve içinde
    `with self.oturum():` açtıktan sonra self.getir(url) kullanır.
    """

    # TSPD gibi korumalarda challenge JS'inin çözülmesi için beklenecek
    # ek süre (ms). Basit JS-render siteler için 0'a çekilebilir.
    challenge_bekleme_ms: int = 0
    render_bekleme: str = "networkidle"   # goto sonrası hangi olayı bekle
    # Kimlik maskesi (UA + stealth betiği). 2026-07-16 Emlak Katılım keşfi:
    # oradaki TSPD, Chromium'un VARSAYILAN kimliğini geçiriyor; maske hem
    # gereksiz hem de tutarsızlık riski (UA "Chrome/149" derken motor farklı).
    # Vakıf Katılım maskeyle doğrulandı → varsayılan True kalıyor.
    kimlik_maskesi: bool = True

    def __init__(self) -> None:
        super().__init__()
        self._sayfa = None          # aktif Playwright sekmesi (oturum içinde)
        self._pw = None
        self._tarayici = None

    # ------------------------------------------------------------------ #
    # Tarayıcı oturumu (context manager)
    # ------------------------------------------------------------------ #
    @contextmanager
    def oturum(self):
        """Chromium'u başlatır, tek sekme açar, blok bitince kapatır.

        Kullanım (spider içinde):
            with self.oturum():
                soup = self.getir(liste_url)
                ...
        """
        # Import'u metoda aldık: Playwright kurulu değilse yalnızca dinamik
        # spider çalıştırıldığında hata versin, statik akışı etkilemesin.
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._tarayici = self._pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled",
                  "--no-sandbox"],
        )
        baglam_ayar = {
            "locale": "tr-TR",
            "timezone_id": "Europe/Istanbul",
            "viewport": {"width": 1366, "height": 768},
        }
        if self.kimlik_maskesi:
            baglam_ayar["user_agent"] = PW_USER_AGENT
        baglam = self._tarayici.new_context(**baglam_ayar)
        if self.kimlik_maskesi:
            baglam.add_init_script(STEALTH_JS)
        self._sayfa = baglam.new_page()
        try:
            yield
        finally:
            self._tarayici.close()
            self._pw.stop()
            self._sayfa = self._tarayici = self._pw = None




    # ------------------------------------------------------------------ #
    # HTTP katmanı — requests yerine Chromium render
    # ------------------------------------------------------------------ #
    def getir(self, url: str) -> BeautifulSoup | None:
        """URL'i tarayıcıyla açar, render olan DOM'u BeautifulSoup döndürür.

        Statik getir() ile aynı sözleşme (BeautifulSoup | None) — spider
        döngüleri değişmez. Rate limit ve retry mantığı korunur.
        """
        if self._sayfa is None:
            raise RuntimeError("getir() yalnızca 'with self.oturum():' içinde çağrılabilir")

        import time
        from playwright.sync_api import Error as PWError

        for deneme in range(1, self.deneme_sayisi + 1):
            gecen = time.time() - self._son_istek_zamani
            if gecen < self.bekleme_saniye:
                time.sleep(self.bekleme_saniye - gecen)
            self._son_istek_zamani = time.time()

            try:
                self._sayfa.goto(url, wait_until=self.render_bekleme, timeout=self.zaman_asimi * 1000)
                if self.challenge_bekleme_ms:
                    self._sayfa.wait_for_timeout(self.challenge_bekleme_ms)
                html = self._sayfa.content()
                # Bot koruması reddi: çok kısa "Request Rejected" kabuğu
                if len(html) < 1000 or "Request Rejected" in html:
                    print(f"    Render reddedildi ({len(html)} bayt), deneme {deneme}/{self.deneme_sayisi}")
                else:
                    return BeautifulSoup(html, "html.parser")
            except PWError as hata:
                mesaj = str(hata).splitlines()[0][:80]
                print(f"    Render hatası ({mesaj}), deneme {deneme}/{self.deneme_sayisi}")

            time.sleep(2 ** deneme)

        print(f"    VAZGEÇİLDİ (render): {url}")
        return None