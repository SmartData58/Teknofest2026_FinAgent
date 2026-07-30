import re
from bs4 import BeautifulSoup

from scraper.base_scraper import TabanScraper

TABAN_URL = "https://hayatfinans.com.tr"
LISTE_URL = f"{TABAN_URL}/kampanyalar"

DETAY_DESENI = re.compile(r"^/kampanyalar/[a-z0-9-]+$", re.IGNORECASE)

SURESI_GECMIS_IFADESI = "kampanyamız sona ermiştir"

KATEGORI_ETIKETLERI = [
    "Arkadaşını Getir",
    "Biz Kart",
    "Katılma Hesabı",
    "Teknoloji",
    "Yatırım",
    "Genel",
]
VARSAYILAN_KATEGORI = "Genel"

# Farklı tarih formatlarını sırayla dener (Vakıf Katılım / Türkiye Finans /
# Emlak Katılım'da doğrulanan aile):
#   "01 Ocak 2026 - 31 Aralık 2026"   (her iki tarafta da tam tarih)
#   "16 Haziran - 31 Temmuz 2026"      (ilk tarafta yıl yok)
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


def kart_kategorisini_bul(a_etiketi) -> str:
    """Kampanya kartının (<a> elementi) alt ağacında kategori rozeti arar.

    Rozet, kartın içinde küçük bir <div> olarak (bir ikon + düz metin
    şeklinde) görünüyor. Class isimleri derleme zamanı üretildiği için
    (Emotion/Next.js) class'a değil, DOĞRUDAN METNE göre eşleştiriyoruz —
    bu, sitenin kendi build'i değişse bile çalışmaya devam eder.
    """
    for div in a_etiketi.find_all("div"):
        metin = div.get_text(strip=True)
        if metin in KATEGORI_ETIKETLERI:
            return metin
    return VARSAYILAN_KATEGORI


class HayatFinansSpider(TabanScraper):
    banka_kodu = "hayat_finans"

    def kampanyalari_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        print(f"  Liste sayfası: {LISTE_URL}")
        soup = self.getir(LISTE_URL)
        if soup is None:
            return kayitlar

        url_kategori_haritasi: dict[str, str] = {}
        for a in soup.select("a[href]"):
            href = a["href"].strip().split("?")[0].split("#")[0]
            href_temiz = href.replace(TABAN_URL, "").replace("https://www.hayatfinans.com.tr", "")
            if not DETAY_DESENI.match(href_temiz):
                continue

            tam_url = TABAN_URL + href_temiz
            kategori = kart_kategorisini_bul(a)
            url_kategori_haritasi.setdefault(tam_url, kategori)

        print(f"  {len(url_kategori_haritasi)} tekil kampanya linki bulundu")

        for url in sorted(url_kategori_haritasi):
            kategori = url_kategori_haritasi[url]
            soup = self.getir(url)
            if soup is None:
                continue

            h1 = soup.select_one("main h1") or soup.select_one("h1")
            icerik = soup.select_one("main")

            if h1 is None or icerik is None:
                print(f"    YAPI UYUŞMADI, atlandı: {url}")
                continue

            ham_metin = self.metin_temizle(icerik)

            if SURESI_GECMIS_IFADESI in ham_metin.lower():
                print(f"    SÜRESİ GEÇMİŞ, atlandı: {url}")
                continue

            tarih_metni = tarih_metnini_bul(icerik)

            kayitlar.append(
                {
                    "banka": self.banka_kodu,
                    "url": url,
                    "baslik": self.metin_temizle(h1),
                    "ham_metin": ham_metin,
                    "kategori": kategori,
                    "tarih_metni": tarih_metni,
                }
            )
            print(f"    OK [{kategori}]: {kayitlar[-1]['baslik'][:55]} | Tarih: {tarih_metni}")

        return kayitlar


if __name__ == "__main__":
    from collections import Counter

    spider = HayatFinansSpider()
    kayitlar = spider.kampanyalari_topla()
    spider.kaydet(kayitlar)

    ozet = Counter(k["kategori"] for k in kayitlar)
    print("\nKategori bazında dağılım:")
    for kategori, sayi in sorted(ozet.items()):
        print(f"  {kategori}: {sayi}")

    tarihi_olmayanlar = [k for k in kayitlar if k["tarih_metni"] is None]
    print(f"\n{len(tarihi_olmayanlar)} kampanyada tarih bulunamadı:")
    for k in tarihi_olmayanlar:
        print(f"  - {k['url']}")

    with open("hayatfinans_tarih_bulunamayanlar.txt", "w", encoding="utf-8") as f:
        for k in tarihi_olmayanlar:
            f.write(f"URL: {k['url']}\n")
            f.write(f"BAŞLIK: {k['baslik']}\n")
            f.write(f"HAM METİN:\n{k['ham_metin']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
    print(f"Detaylar 'hayatfinans_tarih_bulunamayanlar.txt' dosyasına yazıldı.")