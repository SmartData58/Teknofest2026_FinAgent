import re
import sys
from pathlib import Path
PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))
    
from scraper.base_scraper import TabanScraper


    
    
 
TABAN_URL = "https://www.turkiyefinans.com.tr"

KATEGORILER = {
    "finansman-kampanyalari": "finansman",
    "kart-kampanyalari": "kart",
    "odeme-kampanyalari": "odeme",
    "dijital-bankacilik-kampanyalari": "dijital",
    "birikim-fon-kampanyalari": "birikim-fon",
    "yatirim-kampanyalari": "yatirim",
    "sigorta-kampanyalari": "sigorta",
    "ticari-kampanyalar": "ticari",
    "diger-kampanyalar": "diger",
}

DETAY_DEGIL = set(KATEGORILER) | {"default", "Biten-Kampanyalar"}

ASPX_DESENI = re.compile(r"^/tr-tr/kampanyalar/Sayfalar/([A-Za-z0-9-]+)\.aspx$")

# Farklı tarih formatlarını sırayla dener (Vakıf Katılım'da doğrulanan aile):
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
    2. Bulunamazsa tüm içerik metninde arar (fallback) — bazı kampanyalarda
       tarih düz paragraf metnine gömülü olup vurgulanmıyor.
    3. Hiçbir yerde bulunamazsa None döner (kampanyanın gerçekten tarihi
       yoktur — örn. süresiz kampanyalar).
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


class TurkiyeFinansSpider(TabanScraper):
    banka_kodu = "turkiye_finans"

    def kampanyalari_topla(self) -> list[dict]:
        detaylar: dict[str, str] = {}
        for slug, kategori in KATEGORILER.items():
            liste_url = f"{TABAN_URL}/tr-tr/kampanyalar/Sayfalar/{slug}.aspx"
            print(f"  Liste sayfası: {liste_url}")
            soup = self.getir(liste_url)
            if soup is None:
                continue
            for a in soup.select("a[href]"):
                href = a["href"].split("?")[0].replace(TABAN_URL, "").replace(":443", "")
                esles = ASPX_DESENI.match(href)
                if esles and esles.group(1) not in DETAY_DEGIL:
                    detaylar.setdefault(TABAN_URL + href, kategori)

        print(f"  {len(detaylar)} tekil kampanya linki bulundu")

        kayitlar: list[dict] = []
        for url in sorted(detaylar):
            soup = self.getir(url)
            if soup is None:
                continue
            h1 = soup.select_one("h1")
            icerik = soup.select_one(".subpage-content")
            if h1 is None or icerik is None:
                print(f"    YAPI UYUŞMADI, atlandı: {url}")
                continue

            for gurultu in icerik.select(".breadcrumbs, .tool, .noindex"):
                gurultu.decompose()

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

    spider = TurkiyeFinansSpider()
    kayitlar = spider.kampanyalari_topla()
    spider.kaydet(kayitlar)
    spider.kaydet_mongoDB(kayitlar,"turkiye_finans")

    ozet = Counter(k["kategori"] for k in kayitlar)
    print("\nKategori bazında dağılım:")
    for kategori, sayi in sorted(ozet.items()):
        print(f"  {kategori}: {sayi}")

    tarihi_olmayanlar = [k for k in kayitlar if k["tarih_metni"] is None]
    print(f"\n{len(tarihi_olmayanlar)} kampanyada tarih bulunamadı:")
    for k in tarihi_olmayanlar:
        print(f"  - {k['url']}")