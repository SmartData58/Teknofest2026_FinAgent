import json
import time
from datetime import datetime, timezone
from pathlib import Path

 # scraper/db_helper.py
from pymongo import MongoClient
from pymongo.errors import PyMongoError

import requests
from bs4 import BeautifulSoup

PROJE_KOK = Path(__file__).resolve().parent.parent

# Gerçekçi bir tarayıcı kimliği: bazı siteler "python-requests" imzalı
# istekleri botsanıp 403 döndürür. Yaygın bir Chrome imzası kullanıyoruz.
VARSAYILAN_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)



class TabanScraper:
    """Tüm banka spider'larının miras aldığı temel sınıf.

    Alt sınıfın (spider) doldurması gerekenler:
      banka_kodu   : banks.yaml'daki id (ör. "kuveytturk")
      kampanyalari_topla() : kampanya kayıtları listesi döndürür

    Temel sınıfın sağladıkları:
      getir(url)   : beklemeli + yeniden denemeli HTTP GET → BeautifulSoup
      kaydet(...)  : kayıtları data/raw/<banka>/<tarih>.json dosyasına yazar
    """

    banka_kodu: str = ""          # alt sınıf dolduracak
    bekleme_saniye: float = 1.5   # istekler arası nezaket beklemesi
    deneme_sayisi: int = 3        # hata hâlinde toplam deneme
    zaman_asimi: int = 30         # tek isteğin saniye limiti
    mongo_uri: str = "mongodb://localhost:27017"
    db_name: str = "kampanyalar"

    def __init__(self) -> None:
        # Session: aynı siteye art arda isteklerde TCP bağlantısını yeniden
        # kullanır (daha hızlı, siteye daha az yük) ve ortak header taşır.
        self.session = requests.Session()
        self.session.headers["User-Agent"] = VARSAYILAN_USER_AGENT
        self._son_istek_zamani = 0.0

    # ------------------------------------------------------------------ #
    # HTTP katmanı
    # ------------------------------------------------------------------ #
    def getir(self, url: str) -> BeautifulSoup | None:
        """URL'i indirir, BeautifulSoup ağacı döndürür; başarısızsa None.

        - Rate limit: son istekten bu yana bekleme_saniye geçmediyse bekler
        - Retry: ağ hatası/5xx durumunda üstel geri çekilme (exponential
          backoff) ile yeniden dener: 2sn, 4sn, 8sn... Site geçici sorunda
          hemen pes etmeyiz ama ısrarla da yormayız.
        """
        for deneme in range(1, self.deneme_sayisi + 1):
            # --- nezaket beklemesi ---------------------------------------
            gecen = time.time() - self._son_istek_zamani
            if gecen < self.bekleme_saniye:
                time.sleep(self.bekleme_saniye - gecen)

            try:
                self._son_istek_zamani = time.time()
                cevap = self.session.get(url, timeout=self.zaman_asimi)

                if cevap.status_code == 200:
                    # html.parser: Python'un yerleşik ayrıştırıcısı —
                    # ek kurulum gerektirmez (jüri kurulumu basit kalsın)
                    return BeautifulSoup(cevap.text, "html.parser")

                # 404 gibi kalıcı hatalarda yeniden denemek anlamsız
                if 400 <= cevap.status_code < 500:
                    print(f"    UYARI {cevap.status_code}: {url}")
                    return None

                print(f"    {cevap.status_code} aldı, deneme {deneme}/{self.deneme_sayisi}")
            except requests.RequestException as hata:
                # RequestException: zaman aşımı, DNS, bağlantı kopması...
                # requests'in TÜM ağ hatalarının ortak atası.
                print(f"    Ağ hatası ({hata.__class__.__name__}), deneme {deneme}/{self.deneme_sayisi}")

            time.sleep(2 ** deneme)  # üstel geri çekilme: 2, 4, 8 sn

        print(f"    VAZGEÇİLDİ: {url}")
        return None

    # ------------------------------------------------------------------ #
    # Alt sınıfın uygulayacağı sözleşme
    # ------------------------------------------------------------------ #
    def kampanyalari_topla(self) -> list[dict]:
        """Her spider kendi site yapısına göre bunu yazar.

        Dönen her kayıt ŞU ŞEMAYA uymalı (docs/veri_seti.md'de de tanımlı):
          {
            "banka": str,        # banka_kodu
            "url": str,          # kampanya detay sayfası
            "baslik": str,
            "ham_metin": str,    # temizlenmiş düz metin (HTML'siz)
            "kategori": str|None,# sitedeki kategori (ör. "kart-kampanyalari")
            "tarih_metni": str|None,  # sitede yazan tarih ifadesi (ham)
          }
        """
        raise NotImplementedError("Spider kampanyalari_topla() metodunu yazmalı")

    # ------------------------------------------------------------------ #
    # Kayıt katmanı
    # ------------------------------------------------------------------ #
    def kaydet(self, kayitlar: list[dict]) -> Path:
        """Kayıtları data/raw/<banka>/<tarih_saat>.json dosyasına yazar.

        Dosya adında zaman damgası var → her çalıştırma AYRI dosya üretir,
        eski çekimlerin üzerine yazılmaz (veri geçmişi korunur; hangi gün
        hangi kampanyalar vardı sorusuna cevap verebiliriz).
        """
        klasor = PROJE_KOK / "backend" / "data" / "raw" / self.banka_kodu
        klasor.mkdir(parents=True, exist_ok=True)

        zaman = datetime.now(timezone.utc)
        dosya = klasor / f"{zaman.strftime('%Y%m%d_%H%M%S')}.json"

        icerik = {
            "banka": self.banka_kodu,
            "cekilme_zamani": zaman.isoformat(),  # ISO 8601: 2026-07-14T20:00:00+00:00
            "kampanya_sayisi": len(kayitlar),
            "kampanyalar": kayitlar,
        }
        # ensure_ascii=False: Türkçe karakterler ç yerine ç olarak yazılsın
        # indent=2: insan gözüyle okunabilir olsun (debug kolaylığı)
        dosya.write_text(
            json.dumps(icerik, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  Kaydedildi: {dosya} ({len(kayitlar)} kampanya)")
        return dosya


    def kaydet_mongoDB(self, veriler: list[dict], koleksiyon_adi: str) -> None:
        """Çekilen verileri MongoDB koleksiyonuna yazar (Upsert kullanarak mükerrer kaydı önler).

        mongo_uri ve db_name class varsayılanlarından gelir; çağıran taraf
        yalnızca hedef koleksiyon adını verir.
        """
        if not veriler:
            print("MongoDB'ye eklenecek veri bulunamadı.")
            return

        try:
            client = MongoClient(self.mongo_uri)
            db = client[self.db_name]
            koleksiyon = db[koleksiyon_adi]

            islem_sayisi = 0
            for veri in veriler:
                koleksiyon.update_one(
                    {"url": veri["url"]}, {"$set": veri}, upsert=True
                )
                islem_sayisi += 1

            print(
                f"\n[MongoDB] Toplam {islem_sayisi} adet kampanya "
                f"'{koleksiyon_adi}' koleksiyonuna başarıyla kaydedildi/güncellendi."
            )
            client.close()

        except PyMongoError as err:
            print(f"\n[MongoDB Hatası] Veritabanı bağlantı/yazma hatası: {err}")


  

    # ------------------------------------------------------------------ #
    # Yardımcılar
    # ------------------------------------------------------------------ #
    @staticmethod
    def metin_temizle(soup_parcasi) -> str:
        """HTML parçasından düz metin çıkarır.

        get_text(separator=" "): etiketleri atar, aradaki metinleri boşlukla
        birleştirir. split/join zinciri ardışık boşluk/satır sonlarını teke
        indirir — NLP katmanına temiz, tek satırlık paragraflar gider.
        """
        return " ".join(soup_parcasi.get_text(separator=" ").split())