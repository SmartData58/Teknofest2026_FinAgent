import argparse
import importlib
import inspect
from datetime import date, datetime, timezone
from pathlib import Path

from pymongo.errors import PyMongoError
from backend.nlp.preprocessing.cleaner import ATLATICAK_ANAHTARLAR

# DB modülünden fonksiyonları ve bağlantıyı alıyoruz
from backend.db.ham_kampanya_kaydet import get_mongo_db, ham_kampanyalari_kaydet
from scraper.base_scraper import TabanScraper

# Backend NLP temizleme modülünden gerekli bağımlılıkları yüklüyoruz
from backend.nlp.preprocessing.cleaner import temizle
from backend.nlp.extraction.rule_based import kategori_cikar

# --- 1. ADIM: TARİH ÇIKARMA FONKSİYONUNUZU IMPORT EDİN ---
from backend.nlp.extraction.rule_based import tarihleri_cikar

PROJE_KOK = Path(__file__).resolve().parent.parent



def bson_uyumlu_hale_getir(veri):
    """
    Dictionary veya liste içindeki datetime.date objelerini MongoDB/BSON ile 
    uyumlu datetime.datetime tipine dönüştürür.
    """
    if isinstance(veri, dict):
        return {k: bson_uyumlu_hale_getir(v) for k, v in veri.items()}
    elif isinstance(veri, list):
        return [bson_uyumlu_hale_getir(item) for item in veri]
    elif isinstance(veri, date) and not isinstance(veri, datetime):
        return datetime.combine(veri, datetime.min.time())
    return veri


def spider_sinifini_bul(spider_adi: str) -> type[TabanScraper]:
    """scraper/spiders/<ad>.py veya spiders/<ad>.py içindeki TabanScraper alt sınıfını döndürür."""
    modul_yollari = [
        f"scraper.spiders.{spider_adi}",
        f"spiders.{spider_adi}",
    ]

    modul = None
    for yol in modul_yollari:
        try:
            modul = importlib.import_module(yol)
            break
        except ModuleNotFoundError:
            continue

    if not modul:
        raise RuntimeError(
            f"'{spider_adi}' modülü 'scraper.spiders' veya 'spiders' paketleri altında bulunamadı."
        )

    for _, nesne in inspect.getmembers(modul, inspect.isclass):
        if (
            issubclass(nesne, TabanScraper)
            and nesne is not TabanScraper
            and nesne.__module__ == modul.__name__
        ):
            return nesne

    raise RuntimeError(f"'{spider_adi}' modülünde TabanScraper alt sınıfı bulunamadı.")


def ham_verileri_temizle_in_memory(raw_kayitlar: list[dict]) -> list[dict]:
    """
    Spider'dan toplanan ham sözlük verilerini hafızada temizler.
    Metin alanlarını temizler, önce 'tarih_metni' sonra 'ham_metin' üzerinden tarihleri çıkarır.
    """
    if not raw_kayitlar:
        return []

    temiz_kayitlar = []
    print(f"🧹 Toplam {len(raw_kayitlar)} adet ham kampanya verisi temizleniyor...")

    for doc in raw_kayitlar:
        clean_doc = doc.copy()
        clean_doc.pop("is_processed", None)

        # 1. Doküman içindeki tüm metin alanlarını otomatik temizle
        for anahtar, deger in clean_doc.items():
            if anahtar not in ATLATICAK_ANAHTARLAR and isinstance(deger, str):
                clean_doc[anahtar] = temizle(deger)

        # 2. Öncelikli Tarih Çıkarma Mantığı (Fallback Mechanics)
        tarih_metni = clean_doc.get("tarih_metni", "")
        ham_metin = clean_doc.get("ham_metin", "")
        baslik = clean_doc.get("baslik", "")

        tarih_bulgulari = {}

        # 1. ÖNCELİK: Spider'ın karttan/özetten topladığı kısa tarih_metni
        if tarih_metni and str(tarih_metni).strip().lower() != "none":
            tarih_bulgulari = tarihleri_cikar(tarih_metni)

        # 2. ÖNCELİK: Kısa metin yoksa veya tarih çıkarılamadıysa uzun detay metnini tara
        if not tarih_bulgulari.get("baslangic_tarihi") and not tarih_bulgulari.get("bitis_tarihi"):
            tarih_bulgulari = tarihleri_cikar(ham_metin)

        # Çıkarılan bulguları MongoDB dokümanına ekle
        if "baslangic_tarihi" in tarih_bulgulari:
            clean_doc["baslangic_tarihi"] = tarih_bulgulari["baslangic_tarihi"].deger

        if "bitis_tarihi" in tarih_bulgulari:
            clean_doc["bitis_tarihi"] = tarih_bulgulari["bitis_tarihi"].deger

        if "sure_gun" in tarih_bulgulari:
            clean_doc["sure_gun"] = tarih_bulgulari["sure_gun"].deger
            
        # Spider'ın web sitesinden çektiği kategori alanını öncelikli olarak al
        siteden_gelen_kategori = clean_doc.get("kategori")

# Değerin gerçekten var ve anlamlı bir string olup olmadığını kontrol et
        if siteden_gelen_kategori and str(siteden_gelen_kategori).strip().lower() not in ["none", "null", ""]:
            clean_doc["kampanya_turu"] = siteden_gelen_kategori
        else:
    # Siteden geçerli bir kategori gelmediyse başlık ve metinden tespit et
            #aranacak_metin = f"{clean_doc.get('baslik', '')} {ham_metin}"
            tur_bulgusu = kategori_cikar(
                        baslik or "",
                        ham_metin or "",
                    )
    
    # kategori_cikar'dan dönen veri yapısına uygun atama yapın:
            if isinstance(tur_bulgusu, dict):
                clean_doc["kampanya_turu"] = tur_bulgusu.get("tur", "genel")
            else:
                clean_doc["kampanya_turu"] = getattr(tur_bulgusu, "deger", "genel") 

        # 3. İşleme zamanı ve LLM aşaması için bayrak ekleme
        clean_doc["temizlenme_tarihi"] = datetime.now(timezone.utc)
        clean_doc["is_extracted"] = False  # LLM aşaması için hazır işareti

        temiz_kayitlar.append(clean_doc)

    print(f"✅ {len(temiz_kayitlar)} adet kampanya başarıyla temizlendi ve tarihleri işlendi.")
    return temiz_kayitlar


def bankayi_calistir(banka_conf: dict, db) -> None:
    """Tek bankanın spider'ını çalıştırır, verileri temizler ve DB kaydı için ilgili fonksiyona iletir."""
    banka_id = banka_conf["_id"]
    kisa_ad = banka_conf.get("kisa_ad", banka_id)
    spider_adi = banka_conf.get("spider", banka_id)

    print(f"\n==========================================")
    print(f"🚀 [{banka_id.upper()}] {kisa_ad} Tarama Başlatılıyor...")
    print(f"==========================================")

    baslangic_zamani = datetime.now(timezone.utc)

    try:
        spider_class = spider_sinifini_bul(spider_adi)
        spider = spider_class()

        # 1. Spider'dan gelen ham verileri topla
        raw_kayitlar = list(spider.kampanyalari_topla())

        # 2. Verileri DB'ye yazmadan önce hafızada (in-memory) temizle ve tarihleri ayrıştır
        temizlenmis_kayitlar = ham_verileri_temizle_in_memory(raw_kayitlar)

        # 3. MongoDB BSON uyumsuzluğu oluşmaması için date objelerini datetime'a dönüştür
        bson_uyumlu_kayitlar = bson_uyumlu_hale_getir(temizlenmis_kayitlar)

        # 4. Temizlenmiş ve BSON uyumlu kayıtları DB kaydı için ilet
        ham_kampanyalari_kaydet(
            banka_conf=banka_conf,
            raw_kayitlar=bson_uyumlu_kayitlar,
            baslangic_zamani=baslangic_zamani,
            db=db,
        )

    except NotImplementedError:
        print("  ⏭️ Spider henüz yazılmadı (NotImplementedError), atlanıyor.")
    except Exception as hata:
        hata_str = f"{hata.__class__.__name__}: {hata}"
        print(f"   HATA: {hata_str}")


def main() -> None:
    parser = argparse.ArgumentParser(description="FinAgent / SmartData Veri Toplama Çalıştırıcısı")
    parser.add_argument("banka", nargs="?", help="MongoDB 'bankalar' koleksiyonundaki banka id'si (ör. albaraka)")
    parser.add_argument("--hepsi", action="store_true", help="Aktif tüm bankaları sırayla çek")
    args = parser.parse_args()

    mongo_client = None
    try:
        mongo_client, db = get_mongo_db()
        bankalar_col = db["bankalar"]

        if args.hepsi:
            hedefler = list(bankalar_col.find({"aktif": True}))
            if not hedefler:
                print("⚠️ MongoDB 'bankalar' koleksiyonunda aktif banka bulunamadı!")
                return
        elif args.banka:
            hedefler = list(bankalar_col.find({"_id": args.banka}))
            if not hedefler:
                tum_bankalar = [b["_id"] for b in bankalar_col.find({}, {"_id": 1})]
                gecerli_idler = ", ".join(tum_bankalar) if tum_bankalar else "Hiç banka kayıtlı değil"
                parser.error(
                    f"'{args.banka}' MongoDB 'bankalar' koleksiyonunda bulunamadı. Geçerli id'ler: {gecerli_idler}"
                )
        else:
            parser.error("Lütfen bir banka id'si belirtin (ör. python runner.py albaraka) ya da --hepsi kullanın.")

        for banka_conf in hedefler:
            bankayi_calistir(banka_conf, db)

    except PyMongoError as err:
        print(f"\n❌ MongoDB Bağlantı/Yazma Hatası: {err}")
    finally:
        if mongo_client:
            mongo_client.close()


if __name__ == "__main__":
    main()