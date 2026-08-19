import re
from bs4 import BeautifulSoup
from pathlib import Path
import sys
PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))
from scraper.playwright_scraper import PlaywrightTabanScraper

TABAN_URL = "https://www.kuveytturk.com.tr"

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

DAHA_FAZLA_SECICI = (
    "a:has-text('Daha Fazla'), button:has-text('Daha Fazla'), "
    "a:has-text('Daha Fazla Göster'), button:has-text('Daha Fazla Göster')"
)

# CleverTap web pop-up'ı (görsel/promosyon katmanı) tıklamaları engelliyor.
# Bu selectorleri DOM'dan tamamen kaldırıyoruz — sayfanın kendi işleyişini
# etkilemez, sadece otomasyonun önündeki görünmez engeli temizler.
POPUP_TEMIZLEME_JS = """
document.querySelectorAll(
  'ct-web-popup-imageonly, #wzrkImageOnlyDiv, [id^="wzrk"]'
).forEach(el => el.remove());
"""

# --- ÜRÜN (Bireysel Finansmanlar) sabitleri ---
URUN_LISTE_URL = f"{TABAN_URL}/kendim-icin/finansmanlar"
# Ürün detay linkleri /kendim-icin/finansmanlar altında, derinlik
# tutarsız olabilir (bazıları {kategori}/{slug}, bazıları doğrudan
# {slug}) — Albaraka'daki gibi esnek eşleştirip başlık/içerik ile
# doğruluyoruz.
URUN_DETAY_DESENI = re.compile(
    r"^/kendim-icin/finansmanlar/[a-z0-9-]+(?:/[a-z0-9-]+)?/?$", re.IGNORECASE
)
GECERSIZ_URUN_BASLIKLARI = {"finansmanlar", "finansman", "kendim için"}


class KuveytTurkSpider(PlaywrightTabanScraper):
    banka_kodu = "kuveytturk"
    render_bekleme = "networkidle"

    def _popup_temizle(self):
        """Sayfayı engelleyen CleverTap pop-up'larını (varsa) kaldırır."""
        try:
            self._sayfa.evaluate(POPUP_TEMIZLEME_JS)
        except Exception:
            pass  # sayfa henüz hazır değilse ya da pop-up hiç yoksa sorun değil

    def _kategori_linklerini_topla(self, bolum: str, kategori_slug: str) -> set[str]:
        liste_url = f"{TABAN_URL}/kampanyalar/{bolum}/{kategori_slug}"
        print(f"  Liste sayfası (render): {liste_url}")

        soup = self.getir(liste_url)
        if soup is None:
            print(f"  Liste sayfası açılamadı: {liste_url}")
            return set()

        detay_deseni = re.compile(
            rf"^/kampanyalar/{re.escape(bolum)}/{re.escape(kategori_slug)}/[a-z0-9-]+$"
        )

        # Sayfa yüklendikten hemen sonra olası pop-up'ı temizle.
        self._popup_temizle()

        tiklama_sayisi = 0
        while True:
            if self._sayfa.is_closed():
                print("  [UYARI] Sayfa kapanmış, döngüden çıkılıyor.")
                break
            try:
                buton = self._sayfa.locator(DAHA_FAZLA_SECICI).first
                if buton.is_visible(timeout=2000):
                    onceki_sayisi = len(self._sayfa.locator("a[href]").all())

                    # Her tıklamadan hemen önce pop-up'ı tekrar temizle —
                    # sayfa gezinirken/geç yüklenen içerikte tekrar
                    # belirebilir.
                    self._popup_temizle()

                    try:
                        buton.click(timeout=5000)
                    except Exception as tiklama_hatasi:
                        # Yine de engellendiyse, pop-up'ı bir kez daha
                        # temizleyip son bir deneme yap.
                        print(f"  İlk tıklama denemesi engellendi ({tiklama_hatasi.__class__.__name__}), "
                              f"pop-up temizlenip tekrar deneniyor...")
                        self._popup_temizle()
                        self._sayfa.wait_for_timeout(500)
                        buton.click(timeout=5000)

                    tiklama_sayisi += 1
                    self._sayfa.wait_for_timeout(1500)
                    yeni_sayisi = len(self._sayfa.locator("a[href]").all())
                    print(f"  'Daha Fazla' tıklandı ({tiklama_sayisi}). Link elementi: {onceki_sayisi} -> {yeni_sayisi}")
                    if yeni_sayisi == onceki_sayisi:
                        break
                else:
                    break
            except Exception as e:
                print(f"  'Daha Fazla' aranırken/tıklanırken durdu: {e}")
                break

        html = self._sayfa.content()
        soup = BeautifulSoup(html, "html.parser")

        detaylar: set[str] = set()
        for a in soup.select("a[href]"):
            href = a["href"].split("?")[0]
            if detay_deseni.match(href):
                detaylar.add(TABAN_URL + href)

        return detaylar

    def kampanyalari_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        with self.oturum():
            url_bilgi_haritasi: dict[str, tuple[str, str]] = {}

            for bolum, kategoriler in BOLUM_KATEGORILERI.items():
                for kategori_adi, kategori_slug in kategoriler.items():
                    print(f"\n=== Bölüm: {bolum} | Kategori: {kategori_adi} ({kategori_slug}) ===")
                    linkler = self._kategori_linklerini_topla(bolum, kategori_slug)
                    print(f"  {bolum}/{kategori_adi}: {len(linkler)} tekil kampanya linki bulundu")
                    for link in linkler:
                        url_bilgi_haritasi.setdefault(link, (bolum, kategori_adi))

            print(f"\nToplam {len(url_bilgi_haritasi)} tekil kampanya linki bulundu "
                  f"(2 bölüm x 4 kategori birleşik)")

            for url in sorted(url_bilgi_haritasi):
                bolum, kategori = url_bilgi_haritasi[url]
                soup = self.getir(url)
                if soup is None:
                    continue

                h1 = soup.select_one("h1")
                icerik = soup.select_one(".subpage-content")
                tarih = soup.select_one(".campaign-date")

                if h1 is None or icerik is None:
                    print(f"    YAPI UYUŞMADI, atlandı: {url}")
                    continue

                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": self.metin_temizle(h1),
                        "ham_metin": self.metin_temizle(icerik),
                        "bolum": bolum,
                        "kategori": kategori,
                        "tarih_metni": self.metin_temizle(tarih) if tarih else None,
                    }
                )
                print(f"    OK [{bolum}/{kategori}]: {kayitlar[-1]['baslik'][:60]}")

        return kayitlar

        # ------------------------------------------------------------------ #
    # ÜRÜNLER (Bireysel Finansmanlar) — YENİ EKLENDİ
    # ------------------------------------------------------------------ #
    def _urun_linklerini_topla(self) -> set[str]:
        print(f"  Ürün liste sayfası (render): {URUN_LISTE_URL}")
        soup = self.getir(URUN_LISTE_URL)
        if soup is None:
            print(f"  Liste sayfası açılamadı: {URUN_LISTE_URL}")
            return set()

        # Diğer sayfalarda olduğu gibi CleverTap pop-up'ı temizle.
        self._popup_temizle()

        # Kampanyalardaki "Daha Fazla" butonu burada da olabilir; yoksa
        # zararsızca atlanır. Bu sayfanın kartlı/sayfalamalı olduğu
        # DOĞRULANMADI — menü tipi tek sayfa da olabilir.
        try:
            buton = self._sayfa.locator(DAHA_FAZLA_SECICI).first
            while buton.is_visible(timeout=2000):
                self._popup_temizle()
                buton.click(timeout=5000)
                self._sayfa.wait_for_timeout(1500)
        except Exception:
            pass

        html = self._sayfa.content()
        soup = BeautifulSoup(html, "html.parser")

        detaylar: set[str] = set()
        for a in soup.select("a[href]"):
            href = a["href"].split("?")[0].split("#")[0].replace(TABAN_URL, "").rstrip("/")
            if href == "/kendim-icin/finansmanlar":
                continue
            if URUN_DETAY_DESENI.match(href):
                detaylar.add(TABAN_URL + href)

        print(f"  {len(detaylar)} adet aday ürün linki bulundu.")
        return detaylar

    def urunleri_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        with self.oturum():
            urun_linkleri = sorted(self._urun_linklerini_topla())
            print(f"\nToplam {len(urun_linkleri)} tekil ürün linki bulundu.")

            for url in urun_linkleri:
                soup = self.getir(url)
                if soup is None:
                    continue

                h1 = soup.select_one("h1")
                icerik = soup.select_one(".subpage-content")

                if h1 is None or icerik is None:
                    print(f"    YAPI UYUŞMADI, atlandı: {url}")
                    continue

                baslik = self.metin_temizle(h1)
                if not baslik or baslik.lower() in GECERSIZ_URUN_BASLIKLARI:
                    print(f"    Ürün detayı değil (kategori/menü sayfası olabilir), atlandı: {url}")
                    continue

                ham_metin = self.metin_temizle(icerik)
                if len(ham_metin) < 30:
                    print(f"    İçerik çok kısa, muhtemelen liste/menü sayfası, atlandı: {url}")
                    continue

                # Kategori bilgisini URL yapısından çıkar:
                # /kendim-icin/finansmanlar/{kategori}/{slug} varsa dolar,
                # tek segmentse (/finansmanlar/{slug}) None kalır.
                yol_parcalari = url.replace(f"{URUN_LISTE_URL}/", "").split("/")
                kategori = yol_parcalari[0] if len(yol_parcalari) > 1 else None

                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": baslik,
                        "ham_metin": ham_metin,
                        "kategori": kategori,
                        "tarih_metni": None,  # ürün sayfaları genelde tarihsiz
                    }
                )
                print(f"    OK [{kategori}]: {kayitlar[-1]['baslik'][:60]}")

        return kayitlar

if __name__ == "__main__":
    from collections import Counter

    spider = KuveytTurkSpider()

    print("Kuveyt Türk Spider (Kampanyalar) çalıştırılıyor...")
    kayitlar = spider.kampanyalari_topla()
    spider.kaydet(kayitlar)
    spider.kaydet_mongoDB(kayitlar, "kuveyt_katilim")

    ozet = Counter(f"{k['bolum']}/{k['kategori']}" for k in kayitlar)
    print("\nBölüm/Kategori bazında dağılım:")
    for anahtar, sayi in sorted(ozet.items()):
        print(f"  {anahtar}: {sayi}")

    print("\nKuveyt Türk Spider (Ürünler / Bireysel Finansmanlar) çalıştırılıyor...")
    urun_verileri = spider.urunleri_topla()
    spider.kaydet_mongoDB(urun_verileri, koleksiyon_adi="kuveyt_katilim_ürün")

    urun_ozet = Counter(k["kategori"] for k in urun_verileri)
    print("\nÜrün kategori bazında dağılım:")
    for kategori, sayi in sorted(urun_ozet.items(), key=lambda x: (x[0] is None, x[0])):
        print(f"  {kategori}: {sayi}")