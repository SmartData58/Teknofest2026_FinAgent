import re
import sys
from pathlib import Path

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))

from scraper.playwright_scraper import PlaywrightTabanScraper
from scraper.base_scraper import TabanScraper

TABAN_URL = "https://www.emlakkatilim.com.tr"

LISTELER = {
    f"{TABAN_URL}/tr/bireysel/kampanyalar": "bireysel",
    f"{TABAN_URL}/tr/kurumsal/kampanyalar": "kurumsal",
}

DETAY_DESENLERI = [
    re.compile(r"^/tr/bireysel/kampanyalar/kampanya/[a-z0-9-]+$", re.IGNORECASE),
    re.compile(r"^/tr/kurumsal/kampanyalar/[a-z0-9-]+$", re.IGNORECASE),
]

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))


# Farklı tarih formatlarını sırayla dener (Vakıf Katılım / Türkiye Finans'ta
# doğrulanan aile):
#   "01 Ocak 2026 - 31 Aralık 2026"   (her iki tarafta da tam tarih)
#   "8 Mayıs - 30 Kasım 2026"          (ilk tarafta yıl yok)
#   "01.01.2026 - 31.12.2026"          (sayısal, nokta ayraçlı)
#   "31 Aralık 2026 tarihine kadar"    (tek tarih + kadar)
TARIH_DESENLERI = [
    re.compile(
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+(?:\s+\d{4})?\s*[-–]\s*"
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}"
    ),
    re.compile(
        r"\d{1,2}\.\d{1,2}\.\d{4}\s*[-–]\s*\d{1,2}\.\d{1,2}\.\d{4}"
    ),
    re.compile(
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}(?:['’]\w+)?\s*"
        r"(?:tarihine\s+)?kadar"
    ),
]


def tarih_metnini_bul(icerik) -> str | None:
    """Kampanya tarih aralığını bulur.

    1. Önce <b>/<strong> etiketlerinde arar (genelde vurgulanmış tarih
       burada olur).
    2. Bulunamazsa tüm içerik metninde arar (fallback).
    3. Hiçbir yerde bulunamazsa None döner.
    """
    for etiket in icerik.find_all(["b", "strong"]):
        metin = etiket.get_text(strip=True)
        for desen in TARIH_DESENLERI:
            eslesme = desen.search(metin)
            if eslesme:
                return eslesme.group(0)

    tam_metin = icerik.get_text(" ", strip=True)
    for desen in TARIH_DESENLERI:
        eslesme = desen.search(tam_metin)
        if eslesme:
            return eslesme.group(0)

    return None


class EmlakKatilimSpider(PlaywrightTabanScraper):
    banka_kodu = "emlak_katilim"
    render_bekleme = "domcontentloaded"   # networkidle bu sitede hiç gelmiyor
    challenge_bekleme_ms = 5000           # TSPD challenge + içerik render payı
    kimlik_maskesi = False                # TSPD varsayılan Chromium'u geçiriyor

    def kampanyalari_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        with self.oturum():
            # url → kategori (bireysel/kurumsal, URL'den türetiliyor)
            detaylar: dict[str, str] = {}
            for liste_url, kategori in LISTELER.items():
                print(f"  Liste sayfası (render): {liste_url}")
                soup = self.getir(liste_url)
                if soup is None:
                    continue
                for a in soup.select("a[href]"):
                    href = a["href"].strip().split("?")[0].split("#")[0]
                    href = href.replace(TABAN_URL, "")
                    if any(d.match(href) for d in DETAY_DESENLERI):
                        detaylar.setdefault(TABAN_URL + href, kategori)

            print(f"  {len(detaylar)} tekil kampanya linki bulundu")

            for url in sorted(detaylar):
                soup = self.getir(url)
                if soup is None:
                    continue

                h1 = soup.select_one("h1")
                icerik = soup.select_one("article.o-page__content") \
                    or soup.select_one(".o-page__content")

                if h1 is None or icerik is None:
                    print(f"    YAPI UYUŞMADI, atlandı: {url}")
                    continue

                tarih_metni = tarih_metnini_bul(icerik)

                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": self.metin_temizle(h1),
                        "ham_metin": self.metin_temizle(icerik),
                        "kategori": detaylar[url],
                        "tarih_metni": tarih_metni,
                    }
                )
                print(f"    OK: [{detaylar[url]}] {kayitlar[-1]['baslik'][:55]} | Tarih: {tarih_metni}")

        return kayitlar


if __name__ == "__main__":
    from collections import Counter

    spider = EmlakKatilimSpider()
    kayitlar = spider.kampanyalari_topla()
    spider.kaydet_mongoDB(kayitlar, koleksiyon_adi="emlak_katilim")

    ozet = Counter(k["kategori"] for k in kayitlar)
    print("\nKategori bazında dağılım:")
    for kategori, sayi in sorted(ozet.items()):
        print(f"  {kategori}: {sayi}")

    tarihi_olmayanlar = [k for k in kayitlar if k["tarih_metni"] is None]
    print(f"\n{len(tarihi_olmayanlar)} kampanyada tarih bulunamadı:")
    for k in tarihi_olmayanlar:
        print(f"  - {k['url']}")


  
    

    # Tam metinleri ayrı bir dosyaya yaz (terminale sığmayabilir) —
    # gerçek tarih formatını görüp regex'i kesinleştirmek için.
    with open("emlak_tarih_bulunamayanlar.txt", "w", encoding="utf-8") as f:
        for k in tarihi_olmayanlar:
            f.write(f"URL: {k['url']}\n")
            f.write(f"BAŞLIK: {k['baslik']}\n")
            f.write(f"HAM METİN:\n{k['ham_metin']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
    print(f"Detaylar 'emlak_tarih_bulunamayanlar.txt' dosyasına yazıldı.")