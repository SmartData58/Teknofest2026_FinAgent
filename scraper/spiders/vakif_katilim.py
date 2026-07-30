import re
from bs4 import BeautifulSoup

from scraper.playwright_scraper import PlaywrightTabanScraper

TABAN_URL = "https://www.vakifkatilim.com.tr"

LISTE_URLLERI = {
    "kendim_icin": f"{TABAN_URL}/tr/kendim-icin/kampanyalar/mevcut-kampanyalar",
    "isim_icin": f"{TABAN_URL}/tr/isim-icin/kampanyalar/mevcut-kampanyalar",
}

DETAY_DESENI_SABLONU = r"^/tr/{onek}/kampanyalar/detay/[a-z0-9-]+$"

KART_SECICI = "#pagination-page .col-lg-4"
SONRAKI_BUTON_SECICI = "#pagination-button-next"

# Farklı tarih formatlarını sırayla dener. İlk eşleşen kabul edilir.
TARIH_DESENLERI = [
    # "01 Ocak 2026 - 31 Aralık 2026"  (yıl her iki tarafta da var)
    # "8 Mayıs - 30 Kasım 2026"        (yıl sadece ikinci tarihte var)
    re.compile(
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+(?:\s+\d{4})?\s*-\s*\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}"
    ),
    # "31 Temmuz 2026 tarihine kadar" / "31 Aralık 2026'ya kadar" (tek tarih + kadar)
    re.compile(
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}(?:['’]\w+)?\s*(?:tarihine\s+)?kadar"
    ),
]

TARIH_YOK_VARSAYILAN = "Belirtilmemiş"


def _desenlerde_ara(metin: str) -> str | None:
    """Verilen metin içinde tanımlı tüm tarih desenlerini sırayla dener."""
    for desen in TARIH_DESENLERI:
        eslesme = desen.search(metin)
        if eslesme:
            return eslesme.group(0)
    return None


def tarih_metnini_bul(soup: BeautifulSoup, icerik) -> str | None:
    """Kampanya tarih bilgisini bulur.

    Sitede tarih iki farklı yerde gösterilebiliyor:
      1. Sayfa üstündeki "hero" banner bölümünde (.hero-content) — genelde
         <b> ile vurgulanmış, kampanya detay metninin (icerik) DIŞINDA kalır.
         Bu yüzden ham_metin'de görünmez ama sitede görülür.
      2. Kampanya detay metninin (icerik) içinde, <b> ile vurgulanmış ya da
         düz paragraf metnine gömülü.

    Arama sırası (en güvenilirden en genele):
      1. .hero-content içindeki <b>/<strong> etiketleri
      2. icerik içindeki <b> etiketleri
      3. icerik'in tüm düz metni
      4. .hero-content'in tüm düz metni (fallback)
    """
    hero = soup.select_one(".hero-content")

    # 1. Hero banner'daki vurgulanmış etiketler (orijinal keşifteki yapı)
    if hero is not None:
        for etiket in hero.find_all(["b", "strong"]):
            sonuc = _desenlerde_ara(etiket.get_text(strip=True))
            if sonuc:
                return sonuc

    # 2. İçerik bloğundaki <b> etiketleri
    for b in icerik.find_all("b"):
        sonuc = _desenlerde_ara(b.get_text(strip=True))
        if sonuc:
            return sonuc

    # 3. İçerik bloğunun tüm düz metni
    sonuc = _desenlerde_ara(icerik.get_text(" ", strip=True))
    if sonuc:
        return sonuc

    # 4. Hero banner'ın tüm düz metni (son çare)
    if hero is not None:
        sonuc = _desenlerde_ara(hero.get_text(" ", strip=True))
        if sonuc:
            return sonuc

    return None


class VakifKatilimSpider(PlaywrightTabanScraper):
    banka_kodu = "vakif_katilim"
    render_bekleme = "networkidle"

    def _liste_linklerini_topla(self, liste_url: str, onek: str) -> set[str]:
        """Verilen liste sayfasında gezinip (sayfalama dahil) detay linklerini toplar."""
        detaylar: set[str] = set()

        print(f"  Liste sayfası (render): {liste_url}")
        soup = self.getir(liste_url)
        if soup is None:
            print(f"  Liste sayfası açılamadı, atlanıyor: {liste_url}")
            return detaylar

        detay_deseni = re.compile(DETAY_DESENI_SABLONU.format(onek=onek), re.IGNORECASE)
        sayfa_no = 1

        while True:
            try:
                self._sayfa.locator(KART_SECICI).first.wait_for(
                    state="visible", timeout=10000
                )
            except Exception as e:
                if sayfa_no == 1:
                    print(f"  Bu bölümde şu anda kampanya yok ya da sayfa mevcut değil (404 olabilir): {liste_url}")
                else:
                    print(f"  Sayfa {sayfa_no}: kartlar görünmedi ({e}), döngü sonlandırılıyor.")
                break

            html = self._sayfa.content()
            soup = BeautifulSoup(html, "html.parser")

            yeni_sayisi = 0
            for a in soup.select("a[href]"):
                href = a["href"].split("?")[0].split("#")[0].replace(TABAN_URL, "")
                if detay_deseni.match(href):
                    tam_link = TABAN_URL + href
                    if tam_link not in detaylar:
                        detaylar.add(tam_link)
                        yeni_sayisi += 1

            print(f"  Sayfa {sayfa_no}: {yeni_sayisi} yeni link. (Toplam: {len(detaylar)})")

            sonraki_buton = self._sayfa.locator(SONRAKI_BUTON_SECICI).first
            if (
                sonraki_buton.count() > 0
                and sonraki_buton.is_visible()
                and sonraki_buton.is_enabled()
            ):
                sonraki_buton.click()
                self._sayfa.wait_for_timeout(2000)
                sayfa_no += 1
            else:
                print("  Son sayfaya ulaşıldı, link toplama tamamlandı.")
                break

        return detaylar

    def kampanyalari_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        with self.oturum():
            url_kategori_haritasi: dict[str, str] = {}

            for kategori_adi, liste_url in LISTE_URLLERI.items():
                onek = "kendim-icin" if kategori_adi == "kendim_icin" else "isim-icin"
                print(f"\n=== Bölüm: {kategori_adi} ({liste_url}) ===")
                linkler = self._liste_linklerini_topla(liste_url, onek)
                for link in linkler:
                    url_kategori_haritasi.setdefault(link, kategori_adi)

            print(f"\nToplam {len(url_kategori_haritasi)} tekil kampanya linki bulundu "
                  f"(kendim_icin + isim_icin birleşik)")

            for url in sorted(url_kategori_haritasi):
                kategori = url_kategori_haritasi[url]
                soup = self.getir(url)
                if soup is None:
                    continue

                h1 = soup.select_one("h1")
                icerik = soup.select_one("section.anchor-menu-section") \
                    or soup.select_one("section.section-block")

                if h1 is None or icerik is None:
                    print(f"    YAPI UYUŞMADI, atlandı: {url}")
                    continue

                for gurultu in icerik.select(".related, .similar, [class*='ilgin']"):
                    gurultu.decompose()

                # Tarih araması artık hem hero banner'ı hem de içerik bloğunu
                # kapsıyor (bkz. tarih_metnini_bul fonksiyonunun docstring'i).
                tarih_metni = tarih_metnini_bul(soup, icerik) or TARIH_YOK_VARSAYILAN

                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": self.metin_temizle(h1),
                        "ham_metin": self.metin_temizle(icerik),
                        "kategori": kategori,
                        "tarih_metni": tarih_metni,
                    }
                )
                print(f"    OK [{kategori}]: {kayitlar[-1]['baslik'][:60]} | Tarih: {tarih_metni}")

        return kayitlar


if __name__ == "__main__":
    import json

    spider = VakifKatilimSpider()
    kayitlar = spider.kampanyalari_topla()

    with open("vakifkatilim_kampanyalar.json", "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=4)
    print(f"\nToplam {len(kayitlar)} kampanya 'vakifkatilim_kampanyalar.json' dosyasına kaydedildi.")

    tarihi_belirtilmemis = [k for k in kayitlar if k["tarih_metni"] == TARIH_YOK_VARSAYILAN]
    print(f"\n{len(tarihi_belirtilmemis)} kampanyada tarih belirtilmemiş (süresiz/tarihsiz).")

    with open("tarih_bulunamayanlar.txt", "w", encoding="utf-8") as f:
        for k in tarihi_belirtilmemis:
            f.write(f"URL: {k['url']}\n")
            f.write(f"BAŞLIK: {k['baslik']}\n")
            f.write(f"HAM METİN:\n{k['ham_metin']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
    print(f"Detaylar 'tarih_bulunamayanlar.txt' dosyasına yazıldı. ({len(tarihi_belirtilmemis)} kampanya)")