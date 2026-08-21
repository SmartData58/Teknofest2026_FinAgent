import re
from bs4 import BeautifulSoup
from pathlib import Path
import sys

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))


from scraper.playwright_scraper import PlaywrightTabanScraper

TABAN_URL = "https://www.vakifkatilim.com.tr"

LISTE_URL = f"{TABAN_URL}/tr/kendim-icin/kampanyalar/mevcut-kampanyalar"
DETAY_DESENI = re.compile(r"^/tr/kendim-icin/kampanyalar/detay/[a-z0-9-]+$", re.IGNORECASE)

KART_SECICI = "#pagination-page .col-lg-4"
SONRAKI_BUTON_SECICI = "#pagination-button-next"
# Sitede doğrulanan gerçek "daha fazla yükle" butonu metni.
DAHA_FAZLA_METNI = "Daha Fazla Kampanya Gör"

TARIH_DESENLERI = [
    re.compile(
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+(?:\s+\d{4})?\s*-\s*\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}"
    ),
    re.compile(
        r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}(?:['’]\w+)?\s*(?:tarihine\s+)?kadar"
    ),
]

TARIH_YOK_VARSAYILAN = "Belirtilmemiş"

URUN_LISTE_URL = f"{TABAN_URL}/tr/kendim-icin/finansmanlar"
URUN_DETAY_DESENI = re.compile(r"^/tr/kendim-icin/finansmanlar/[a-z0-9-]+$", re.IGNORECASE)

GECERSIZ_URUN_BASLIKLARI = {
    "finansmanlar",
    "kendim için",
    "finansman",
}


def _desenlerde_ara(metin: str) -> str | None:
    for desen in TARIH_DESENLERI:
        eslesme = desen.search(metin)
        if eslesme:
            return eslesme.group(0)
    return None


def tarih_metnini_bul(soup: BeautifulSoup, icerik) -> str | None:
    hero = soup.select_one(".hero-content")

    if hero is not None:
        for etiket in hero.find_all(["b", "strong"]):
            sonuc = _desenlerde_ara(etiket.get_text(strip=True))
            if sonuc:
                return sonuc

    for b in icerik.find_all("b"):
        sonuc = _desenlerde_ara(b.get_text(strip=True))
        if sonuc:
            return sonuc

    sonuc = _desenlerde_ara(icerik.get_text(" ", strip=True))
    if sonuc:
        return sonuc

    if hero is not None:
        sonuc = _desenlerde_ara(hero.get_text(" ", strip=True))
        if sonuc:
            return sonuc

    return None


class VakifKatilimSpider(PlaywrightTabanScraper):
    banka_kodu = "vakif_katilim"
    render_bekleme = "networkidle"

    # ------------------------------------------------------------------ #
    # KAMPANYALAR (yalnızca "Kendim İçin")
    # ------------------------------------------------------------------ #
    def _liste_linklerini_topla(self) -> set[str]:
        """Kendim İçin kampanya sayfasında linkleri toplar.

        Linkler iki farklı yerde çıkabiliyor:
          1. Ana içerik alanındaki kartlar (#pagination-page .col-lg-4) —
             "Daha Fazla Kampanya Gör" butonuna tıklandıkça daha fazlası
             yükleniyor (sitede DOĞRULANAN gerçek buton metni).
          2. Sayfanın üstündeki "Bildirimler" açılır penceresi — kartlar
             boş görünse bile burada gerçek kampanya linkleri olabiliyor.

        Bu yüzden hem "Daha Fazla" butonuna olabildiğince tıklanır, hem de
        (buton hiç yoksa dahi) sayfanın tamamındaki linkler taranır.
        """
        detaylar: set[str] = set()

        print(f"  Liste sayfası (render): {LISTE_URL}")
        soup = self.getir(LISTE_URL)
        if soup is None:
            print(f"  Liste sayfası açılamadı: {LISTE_URL}")
            return detaylar

        # --- "Daha Fazla Kampanya Gör" butonuna tekrar tekrar tıkla ---
        tiklama_sayisi = 0
        while True:
            try:
                buton = self._sayfa.get_by_text(DAHA_FAZLA_METNI, exact=False).first
                if buton.count() == 0 or not buton.is_visible(timeout=2000):
                    break
                buton.scroll_into_view_if_needed(timeout=5000)
                self._sayfa.wait_for_timeout(300)
                buton.click(timeout=5000)
                tiklama_sayisi += 1
                self._sayfa.wait_for_timeout(1500)
                print(f"  '{DAHA_FAZLA_METNI}' tıklandı ({tiklama_sayisi}).")
            except Exception as e:
                print(f"  '{DAHA_FAZLA_METNI}' butonu bulunamadı/tıklanamadı: {e}")
                break

        if tiklama_sayisi == 0:
            print("  'Daha Fazla Kampanya Gör' butonu hiç bulunamadı "
                  "(kart alanı zaten boş olabilir), yine de tüm sayfa "
                  "linkleri (bildirimler dahil) taranacak.")

        # --- Kart alanının (varsa) sayfalanabilir olup olmadığını kontrol et ---
        kart_alani_var = True
        try:
            self._sayfa.locator(KART_SECICI).first.wait_for(state="visible", timeout=3000)
        except Exception:
            kart_alani_var = False

        sayfa_no = 1

        while True:
            html = self._sayfa.content()
            soup = BeautifulSoup(html, "html.parser")

            yeni_sayisi = 0
            for a in soup.select("a[href]"):
                href = a["href"].split("?")[0].split("#")[0].replace(TABAN_URL, "")
                if DETAY_DESENI.match(href):
                    tam_link = TABAN_URL + href
                    if tam_link not in detaylar:
                        detaylar.add(tam_link)
                        yeni_sayisi += 1

            print(f"  Sayfa {sayfa_no}: {yeni_sayisi} yeni link. (Toplam: {len(detaylar)})")

            if not kart_alani_var:
                break

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
            print("=== Bölüm: Kendim İçin (Kampanyalar) ===")
            urunler = self._liste_linklerini_topla()
            print(f"\nToplam {len(urunler)} tekil kampanya linki bulundu")

            for url in sorted(urunler):
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

                tarih_metni = tarih_metnini_bul(soup, icerik) or TARIH_YOK_VARSAYILAN

                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": self.metin_temizle(h1),
                        "ham_metin": self.metin_temizle(icerik),
                        "kategori": "kendim_icin",
                        "tarih_metni": tarih_metni,
                    }
                )
                print(f"    OK: {kayitlar[-1]['baslik'][:60]} | Tarih: {tarih_metni}")

        return kayitlar

    # ------------------------------------------------------------------ #
    # ÜRÜNLER (yalnızca "Kendim İçin" Finansmanlar)
    # ------------------------------------------------------------------ #
    def _urun_liste_linklerini_topla(self) -> set[str]:
        detaylar: set[str] = set()

        print(f"  Ürün liste sayfası (render): {URUN_LISTE_URL}")
        soup = self.getir(URUN_LISTE_URL)
        if soup is None:
            print(f"  Liste sayfası açılamadı: {URUN_LISTE_URL}")
            return detaylar

        elenen_isim_icin: list[str] = []

        for a in soup.select("a[href]"):
            href = a["href"].split("?")[0].split("#")[0].replace(TABAN_URL, "").rstrip("/")

            # Savunma filtresi: "isim-icin" geçen HİÇBİR link kabul
            # edilmez, regex zaten bunu engelliyor olmalı ama garantiye
            # alınıyor ve şeffaflık için elenenler ayrıca loglanıyor.
            if "isim-icin" in href.lower():
                elenen_isim_icin.append(href)
                continue

            if URUN_DETAY_DESENI.match(href):
                detaylar.add(TABAN_URL + href)

        print(f"  {len(detaylar)} adet aday ürün linki bulundu (yalnızca kendim-icin).")
        if elenen_isim_icin:
            print(f"  {len(elenen_isim_icin)} adet 'işim için' linki tespit edilip elendi:")
            for h in sorted(set(elenen_isim_icin)):
                print(f"    - elendi: {h}")

        return detaylar

    def urunleri_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        with self.oturum():
            print("=== Bölüm: Kendim İçin (Finansmanlar) ===")
            urun_linkleri = self._urun_liste_linklerini_topla()
            print(f"\nToplam {len(urun_linkleri)} tekil ürün linki bulundu")

            for url in sorted(urun_linkleri):
                # İkinci bir savunma katmanı: her ihtimale karşı, detay
                # sayfasına gitmeden önce URL'nin gerçekten kendim-icin
                # altında olduğunu bir kez daha doğrula.
                if "isim-icin" in url.lower():
                    print(f"    GÜVENLİK: 'işim için' linki tespit edildi, atlandı: {url}")
                    continue

                soup = self.getir(url)
                if soup is None:
                    continue

                h1 = soup.select_one("h1")
                icerik = soup.select_one("section.anchor-menu-section") \
                    or soup.select_one("section.section-block")

                if h1 is None or icerik is None:
                    print(f"    YAPI UYUŞMADI, atlandı: {url}")
                    continue

                baslik = self.metin_temizle(h1)
                if not baslik or baslik.lower() in GECERSIZ_URUN_BASLIKLARI:
                    print(f"    Ürün detayı değil (menü/liste sayfası olabilir), atlandı: {url}")
                    continue

                for gurultu in icerik.select(".related, .similar, [class*='ilgin']"):
                    gurultu.decompose()

                ham_metin = self.metin_temizle(icerik)
                if len(ham_metin) < 30:
                    print(f"    İçerik çok kısa, muhtemelen liste/menü sayfası, atlandı: {url}")
                    continue

                kayitlar.append(
                    {
                        "banka": self.banka_kodu,
                        "url": url,
                        "baslik": baslik,
                        "ham_metin": ham_metin,
                        "kategori": "kendim_icin",
                        "tarih_metni": None,
                    }
                )
                print(f"    OK: {kayitlar[-1]['baslik'][:60]}")

        return kayitlar


if __name__ == "__main__":
    import json

    spider = VakifKatilimSpider()

    print("Vakıf Katılım Spider (Kendim İçin - Kampanyalar) çalıştırılıyor...")
    kayitlar = spider.kampanyalari_topla()
    spider.kaydet_mongoDB(kayitlar, koleksiyon_adi="vakif_katilim")

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

    print("\nVakıf Katılım Spider (Kendim İçin - Finansmanlar) çalıştırılıyor...")
    urun_verileri = spider.urunleri_topla()
    spider.kaydet_mongoDB(urun_verileri, koleksiyon_adi="vakif_katilim_ürün")

    with open("vakifkatilim_urunler.json", "w", encoding="utf-8") as f:
        json.dump(urun_verileri, f, ensure_ascii=False, indent=4)
    print(f"Toplam {len(urun_verileri)} ürün 'vakifkatilim_urunler.json' dosyasına kaydedildi.")