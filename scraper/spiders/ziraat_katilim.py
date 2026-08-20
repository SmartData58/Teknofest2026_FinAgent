import re
from pathlib import Path
import sys

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.insert(0, str(PROJE_KOK))
    
from scraper.base_scraper import TabanScraper

TABAN_URL = "https://www.ziraatkatilim.com.tr"

# Kategori taksonomi sayfaları — her biri /kampanyalar/{slug} altında.
# Kategori etiketleri sitede DOĞRULANDI (kampanyalar/diger-kampanyalar
# sayfasındaki filtre linklerinden alındı).
KATEGORI_SAYFALARI = {
    "akaryakit": "Akaryakıt",
    "beyaz-esya-ve-ev-aletleri": "Beyaz Eşya ve Ev Aletleri",
    "diger-kampanyalar": "Diğer Kampanyalar",
    "e-ticaret": "E-Ticaret",
    "egitim-kitap-ve-kirtasiye": "Eğitim, Kitap ve Kırtasiye",
    "elektronik-ve-telekomunikasyon": "Elektronik ve Telekomünikasyon",
    "genel-kampanyalar": "Genel Kampanyalar",
    "giyim-ve-aksesuar": "Giyim ve Aksesuar",
    "hobi-ve-oyuncak": "Hobi ve Oyuncak",
    "kuyum-optik-ve-saat": "Kuyum, Optik ve Saat",
    "market-ve-gida": "Market ve Gıda",
    "mobilya-ve-dekorasyon": "Mobilya ve Dekorasyon",
    "turizm-ve-seyahat": "Turizm ve Seyahat",
    "yapi-sektoru-ve-iklimlendirme": "Yapı Sektörü ve İklimlendirme",
}

# Tüm detay sayfaları /kart-kampanyalari/{slug} altında toplanıyor
# (kategoriden bağımsız olarak — sitede DOĞRULANDI).
DETAY_DESENI = re.compile(r"^/kart-kampanyalari/[a-z0-9-]+/?$", re.IGNORECASE)

  
# --- ÜRÜN (Bireysel Finansman Ürünleri) sabitleri ---
URUN_LISTE_URL = f"{TABAN_URL}/bireysel/finansman-urunleri"

# Menüde 4 alt kategori var (ekran görüntüsünden DOĞRULANDI):
#   Konut-Gayrimenkul Finansmanı, Taşıt Finansmanı, İhtiyaç Finansmanı,
#   Sürdürülebilirlik Temalı Bireysel Ürünler
# Kategori slug'ları sitede tutarsız görülüyor (arama sonuçlarında hem
# "konut-finansmani" hem "konut-gayrimenkul-finansmani" görüldü), bu
# yüzden sabit bir slug seti tutmuyoruz — URL'den dinamik çıkarıyoruz.
URUN_LINK_DESENI = re.compile(
    r"^/bireysel/finansman-urunleri/[a-z0-9-]+(?:/[a-z0-9-]+)?/?$", re.IGNORECASE
)
GECERSIZ_URUN_BASLIKLARI = {"finansman ürünleri", "bireysel", "finansman"}

class ZiraatKatilimSpider(TabanScraper):
    banka_kodu = "ziraat_katilim"

    def kampanyalari_topla(self) -> list[dict]:
        kayitlar: list[dict] = []

        # url (temiz, ?IsArchived olmadan) -> kategori haritası
        url_kategori_haritasi: dict[str, str] = {}
        # Süresi geçmiş olarak İŞARETLENMİŞ url'leri ayrı tutuyoruz —
        # aynı kampanya bazen hem güncel hem arşiv linkiyle görünebiliyor,
        # arşiv işareti varsa kesin olarak dışarıda bırakılmalı.
        suresi_gecmis_urller: set[str] = set()

        for kategori_slug, kategori_adi in KATEGORI_SAYFALARI.items():
            liste_url = f"{TABAN_URL}/kampanyalar/{kategori_slug}"
            print(f"  Liste sayfası: {liste_url}")
            soup = self.getir(liste_url)
            if soup is None:
                continue

            for a in soup.select("a[href]"):
                href = a["href"].strip()
                if "IsArchived=true" in href:
                    temiz_href = href.split("?")[0]
                    temiz_href = temiz_href.replace(TABAN_URL, "")
                    if DETAY_DESENI.match(temiz_href):
                        suresi_gecmis_urller.add(TABAN_URL + temiz_href)
                    continue

                temiz_href = href.split("?")[0].split("#")[0]
                temiz_href = temiz_href.replace(TABAN_URL, "")
                if DETAY_DESENI.match(temiz_href):
                    tam_url = TABAN_URL + temiz_href
                    url_kategori_haritasi.setdefault(tam_url, kategori_adi)

        print(f"  {len(url_kategori_haritasi)} tekil (görünüşte güncel) kampanya linki bulundu")
        print(f"  {len(suresi_gecmis_urller)} tekil arşivlenmiş (süresi geçmiş) kampanya linki bulundu")

        for url in sorted(url_kategori_haritasi):
            # Aynı URL başka bir yerde ?IsArchived=true ile de görülmüşse,
            # güvenli tarafta kal ve bu kampanyayı atla.
            if url in suresi_gecmis_urller:
                print(f"    SÜRESİ GEÇMİŞ (arşiv işaretli), atlandı: {url}")
                continue

            kategori = url_kategori_haritasi[url]
            soup = self.getir(url)
            if soup is None:
                continue

            h1 = soup.select_one("h1")
            icerik = (
                soup.select_one(".field--name-body")
                or soup.select_one("article")
                or soup.select_one("main")
            )

            if h1 is None or icerik is None:
                print(f"    YAPI UYUŞMADI, atlandı: {url}")
                continue

            kayitlar.append(
                {
                    "banka": self.banka_kodu,
                    "url": url,
                    "baslik": self.metin_temizle(h1),
                    "ham_metin": self.metin_temizle(icerik),
                    "kategori": kategori,
                    "tarih_metni": None,  # "Son Gün DD.MM.YYYY" kart üzerinde var,
                                          # detay sayfası HTML'i doğrulanınca eklenebilir
                }
            )
            print(f"    OK [{kategori}]: {kayitlar[-1]['baslik'][:55]}")

        return kayitlar

    # FİNANSMAN URUNLERİ    

        # ------------------------------------------------------------------ #
    # ÜRÜNLER (Bireysel Finansman Ürünleri) — GÜNCELLENDİ (2 seviyeli tarama)
    # ------------------------------------------------------------------ #
    def urunleri_topla(self) -> list[dict]:
        kayitlar: list[dict] = []
        ziyaret_edilen: set[str] = set()
        kuyruk: list[str] = [URUN_LISTE_URL]
        urun_adaylari: set[str] = set()

        # 1. AŞAMA: Ana "Finansman Ürünleri" sayfasından başlayıp, 4 alt
        # kategori sayfasını (Konut-Gayrimenkul, Taşıt, İhtiyaç,
        # Sürdürülebilirlik) da tarayarak altlarındaki ürün linklerini
        # topluyoruz.
        while kuyruk:
            sayfa_url = kuyruk.pop(0)
            if sayfa_url in ziyaret_edilen:
                continue
            ziyaret_edilen.add(sayfa_url)

            print(f"  Taranıyor: {sayfa_url}")
            soup = self.getir(sayfa_url)
            if soup is None:
                continue

            for a in soup.select("a[href]"):
                href = a["href"].split("?")[0].split("#")[0].replace(TABAN_URL, "")
                if not URUN_LINK_DESENI.match(href):
                    continue
                if href.rstrip("/") == "/bireysel/finansman-urunleri":
                    continue

                tam_url = TABAN_URL + href
                urun_adaylari.add(tam_url)

                # Tek segmentli linkler (örn. .../finansman-urunleri/tasit-finansmani)
                # kategori sayfası olabilir; altındaki ürünleri bulmak için
                # kuyruğa ekleyip tekrar tarıyoruz.
                parcalar = href.strip("/").split("/")
                if len(parcalar) == 3 and tam_url not in ziyaret_edilen:
                    kuyruk.append(tam_url)

        print(f"\n  Toplam {len(urun_adaylari)} adet aday ürün/kategori linki bulundu.")

        # 2. AŞAMA: Her aday sayfayı tek tek ziyaret edip doğrula.
        for url in sorted(urun_adaylari):
            soup = self.getir(url)
            if soup is None:
                continue

            h1 = soup.select_one("h1")
            icerik = (
                soup.select_one(".field--name-body")
                or soup.select_one("article")
                or soup.select_one("main")
            )

            if h1 is None or icerik is None:
                print(f"    YAPI UYUŞMADI, atlandı: {url}")
                continue

            baslik = self.metin_temizle(h1)
            if not baslik or baslik.lower() in GECERSIZ_URUN_BASLIKLARI:
                print(f"    Geçersiz başlık, atlandı: {url}")
                continue

            ham_metin = self.metin_temizle(icerik)
            if len(ham_metin) < 30:
                print(f"    İçerik çok kısa, muhtemelen kategori/liste sayfası, atlandı: {url}")
                continue

            # Kategori: URL'nin "finansman-urunleri" sonrası ilk segmenti
            # (örn. ihtiyac-finansmani, konut-gayrimenkul-finansmani).
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
            print(f"    OK [{kategori}]: {baslik[:55]}")

        return kayitlar


if __name__ == "__main__":
    from collections import Counter

    spider = ZiraatKatilimSpider()

    print("Ziraat Katılım Spider (Kampanyalar) çalıştırılıyor...")
    kayitlar = spider.kampanyalari_topla()
    spider.kaydet(kayitlar)
    spider.kaydet_mongoDB(kayitlar, "ziraat_katilim")
    ozet = Counter(k["kategori"] for k in kayitlar)
    print("\nKategori bazında dağılım:")
    for kategori, sayi in sorted(ozet.items()):
        print(f"  {kategori}: {sayi}")

    print("\nZiraat Katılım Spider (Ürünler / Finansmanlar) çalıştırılıyor...")
    urun_verileri = spider.urunleri_topla()
    spider.kaydet_mongoDB(urun_verileri, koleksiyon_adi="ziraat_katilim_ürün")