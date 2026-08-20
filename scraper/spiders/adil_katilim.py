from scraper.base_scraper import TabanScraper


class AdilKatilimSpider(TabanScraper):
    banka_kodu = "adil_katilim"

    def kampanyalari_topla(self) -> list[dict]:
        # Adil Katılım Bankası (BDDK onayı almış, faaliyete geçmiş bir
        # katılım bankası) henüz mobil uygulamasını / dijital bankacılık
        # ürünlerini yayına almadı (doğrulama tarihi: 20.07.2026,
        # adilkatilim.com.tr üzerinde "Mobil uygulamamız çok yakında
        # uygulama mağazalarında hizmetinizde olacak" ibaresi mevcut).
        #
        # Bu nedenle sitede aktif bir kampanya listeleme sayfası yok.
        # Banka uygulamasını/kampanya sayfasını yayına aldığında bu
        # spider'ı diğer katılım bankası spider'ları (örn. Vakıf Katılım,
        # Dünya Katılım) gibi doldurmak gerekecek.
        print("  Adil Katılım Bankası henüz aktif kampanya yayınlamıyor "
              )
        return []


if __name__ == "__main__":
    spider = AdilKatilimSpider()
    kayitlar = spider.kampanyalari_topla()
    spider.kaydet(kayitlar)