import re
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path
import sys
PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))
    
    

from scraper.playwright_scraper import PlaywrightTabanScraper

TABAN_URL = "https://hadiyanindakibanka.com"
LISTE_URL = f"{TABAN_URL}/hadi-kazan/kampanyalar"

DETAY_DESENI = re.compile(r"^/kampanyalar/[a-z0-9-]+$", re.IGNORECASE)

DAHA_FAZLA_METNI = "Daha fazla göster"

AYLAR = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}

# İki tarihli aralık, yazılı ay, yıl bazen sadece ikinci tarafta:
#   "6 Mart-31 Ağustos 2026"
TARIH_ARALIGI_YAZI = re.compile(
    r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)(?:\s+(\d{4}))?\s*[-–]\s*"
    r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})"
)
# İki tarihli aralık, sayısal (nokta ayraçlı):
#   "19.01.2026 – 30.09.2026"
TARIH_ARALIGI_SAYISAL = re.compile(
    r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s*[-–]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})"
)
# YENİ — Tek bitiş tarihi + "kadar", yazılı ay:
#   "31 Aralık 2026'ya kadar", "31 Aralık 2026 tarihine kadar"
TARIH_TEK_KADAR = re.compile(
    r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})(?:['’]\w+)?\s*"
    r"(?:tarihine\s+)?kadar"
)
# YENİ — Tek bitiş tarihi + "kadar", sayısal:
#   "31.12.2026'ya kadar", "31.12.2026 tarihine kadar"
TARIH_TEK_SAYISAL_KADAR = re.compile(
    r"(\d{1,2})\.(\d{1,2})\.(\d{4})(?:['’]\w+)?\s*(?:tarihine\s+)?kadar"
)


def bitis_tarihini_bul(metin: str) -> datetime | None:
    """Metindeki tarih ifadesinden BİTİŞ tarihini çıkarır.

    Sırasıyla dener: iki-tarihli sayısal aralık, iki-tarihli yazılı aralık,
    tek tarih + "kadar" (sayısal), tek tarih + "kadar" (yazılı). Hiçbiri
    eşleşmezse None döner (kampanyanın süresi belirsizdir, güvenli tarafta
    kalıp aktif kabul edilir).
    """
    eslesme = TARIH_ARALIGI_SAYISAL.search(metin)
    if eslesme:
        gun, ay, yil = int(eslesme.group(4)), int(eslesme.group(5)), int(eslesme.group(6))
        try:
            return datetime(yil, ay, gun)
        except ValueError:
            pass

    eslesme = TARIH_ARALIGI_YAZI.search(metin)
    if eslesme:
        gun = int(eslesme.group(4))
        ay_adi = eslesme.group(5).lower()
        yil = int(eslesme.group(6))
        ay = AYLAR.get(ay_adi)
        if ay:
            try:
                return datetime(yil, ay, gun)
            except ValueError:
                pass

    eslesme = TARIH_TEK_SAYISAL_KADAR.search(metin)
    if eslesme:
        gun, ay, yil = int(eslesme.group(1)), int(eslesme.group(2)), int(eslesme.group(3))
        try:
            return datetime(yil, ay, gun)
        except ValueError:
            pass

    eslesme = TARIH_TEK_KADAR.search(metin)
    if eslesme:
        gun = int(eslesme.group(1))
        ay_adi = eslesme.group(2).lower()
        yil = int(eslesme.group(3))
        ay = AYLAR.get(ay_adi)
        if ay:
            try:
                return datetime(yil, ay, gun)
            except ValueError:
                pass

    return None


class TomKatilimSpider(PlaywrightTabanScraper):
    banka_kodu = "tom_katilim"
    render_bekleme = "networkidle"

    def _link_sayisini_al(self) -> int:
        return len(self._sayfa.locator("a[href*='/kampanyalar/']").all())

    def _liste_linklerini_topla(self) -> set[str]:
        print(f"  Liste sayfası (render): {LISTE_URL}")
        soup = self.getir(LISTE_URL)
        if soup is None:
            return set()

        try:
            self._sayfa.locator("a[href*='/kampanyalar/']").first.wait_for(
                state="attached", timeout=10000
            )
        except Exception as e:
            print(f"  İlk kampanya kartı beklenirken sorun: {e}")

        tiklama_sayisi = 0
        while True:
            if self._sayfa.is_closed():
                print("  [UYARI] Sayfa kapanmış, döngüden çıkılıyor.")
                break

            buton = self._sayfa.get_by_text(DAHA_FAZLA_METNI, exact=False).first
            if buton.count() == 0:
                print("  'Daha fazla göster' butonu artık DOM'da yok, döngü bitti.")
                break

            try:
                onceki_sayisi = self._link_sayisini_al()
                buton.scroll_into_view_if_needed(timeout=5000)
                self._sayfa.wait_for_timeout(300)
                buton.click(timeout=5000)
                tiklama_sayisi += 1
                self._sayfa.wait_for_timeout(1500)
                yeni_sayisi = self._link_sayisini_al()
                print(f"  '{DAHA_FAZLA_METNI}' tıklandı ({tiklama_sayisi}). "
                      f"Kampanya linki: {onceki_sayisi} -> {yeni_sayisi}")
                if yeni_sayisi == onceki_sayisi:
                    print("  Link sayısı artmadı, tüm kampanyalar yüklenmiş olmalı.")
                    break
            except Exception as e:
                print(f"  Buton tıklanırken sorun oluştu: {e}")
                break

        html = self._sayfa.content()
        soup = BeautifulSoup(html, "html.parser")

        detaylar: set[str] = set()
        for a in soup.select("a[href]"):
            href = a["href"].strip().split("?")[0].split("#")[0]
            href = href.replace(TABAN_URL, "").replace("https://tombankhadi.com", "")
            if DETAY_DESENI.match(href):
                detaylar.add(TABAN_URL + href)

        return detaylar

    def kampanyalari_topla(self) -> list[dict]:
        kayitlar: list[dict] = []
        bugun = datetime.now()

        with self.oturum():
            detaylar = self._liste_linklerini_topla()
            print(f"  {len(detaylar)} tekil kampanya linki bulundu")

            for url in sorted(detaylar):
                soup = self.getir(url)
                if soup is None:
                    continue

                h1 = soup.select_one("main h1") or soup.select_one("h1")
                icerik = soup.select_one("main")

                if h1 is None or icerik is None:
                    print(f"    YAPI UYUŞMADI, atlandı: {url}")
                    continue

                for gurultu in icerik.select("section.campaigns"):
                    gurultu.decompose()

                ham_metin = self.metin_temizle(icerik)

                bitis_tarihi = bitis_tarihini_bul(ham_metin)
                if bitis_tarihi is not None and bitis_tarihi < bugun:
                    print(f"    SÜRESİ GEÇMİŞ ({bitis_tarihi.strftime('%d.%m.%Y')}), atlandı: {url}")
                    continue

                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": self.metin_temizle(h1),
                        "ham_metin": ham_metin,
                        "kategori": None,
                        "tarih_metni": bitis_tarihi.strftime("%d.%m.%Y") if bitis_tarihi else None,
                    }
                )
                etiket = f"Bitiş: {bitis_tarihi.strftime('%d.%m.%Y')}" if bitis_tarihi else "Tarih: bulunamadı"
                print(f"    OK: {kayitlar[-1]['baslik'][:60]} | {etiket}")

        return kayitlar


if __name__ == "__main__":
    spider = TomKatilimSpider()
    kayitlar = spider.kampanyalari_topla()
    spider.kaydet(kayitlar)
    spider.kaydet_mongoDB(kayitlar,"tom_katilim")

    tarihi_olmayanlar = [k for k in kayitlar if k["tarih_metni"] is None]
    print(f"\n{len(tarihi_olmayanlar)} kampanyada tarih bulunamadı:")
    if tarihi_olmayanlar:
        with open("tom_tarih_bulunamayanlar.txt", "w", encoding="utf-8") as f:
            for k in tarihi_olmayanlar:
                print(f"  - {k['url']}")
                f.write(f"URL: {k['url']}\n")
                f.write(f"BAŞLIK: {k['baslik']}\n")
                f.write(f"HAM METİN:\n{k['ham_metin']}\n")
                f.write("\n" + "=" * 80 + "\n\n")
        print("Detaylar 'tom_tarih_bulunamayanlar.txt' dosyasına yazıldı.")