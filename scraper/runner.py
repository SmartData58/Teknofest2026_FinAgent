import argparse
import importlib
import inspect
import os
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from scraper.base_scraper import TabanScraper

PROJE_KOK = Path(__file__).resolve().parent.parent

# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")  # Docker içi servis adı
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)


def get_mongo_db():
    """MongoDB istemcisini başlatır ve veritabanı nesnesini döndürür."""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    return client, db


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


def bankayi_calistir(banka_conf: dict, db) -> None:
    """Tek bankanın spider'ını çalıştırır; verileri MongoDB 'kampanyalar' koleksiyonuna kaydeder."""
    kod = banka_conf["id"]
    kisa_ad = banka_conf.get("kisa_ad", kod)
    spider_adi = banka_conf.get("spider", kod)

    # MongoDB bankalar koleksiyonundan okunan Meta Bilgiler
    mulkiyet_turu = banka_conf.get("mulkiyet_turu", "özel")
    buyukluk_kategorisi = banka_conf.get("buyukluk_kategorisi", "belirtilmedi")

    print(f"\n==========================================")
    print(f"🚀 [{kod.upper()}] {kisa_ad} Tarama Başlatılıyor...")
    print(f"📊 Mülkiyet: {mulkiyet_turu.upper()} | Ölçek: {buyukluk_kategorisi.upper()}")
    print(f"==========================================")

    raw_collection = db["kampanyalar"]
    log_collection = db["scrape_logs"]

    simdi = datetime.now(timezone.utc)
    log_kaydi = {
        "banka_kodu": kod,
        "tarih": simdi,
        "durum": "hata",
        "kampanya_sayisi": 0,
        "hata_mesaji": None
    }

    try:
        spider_class = spider_sinifini_bul(spider_adi)
        spider = spider_class()

        # Spider'dan gelen ham verileri alıyoruz
        raw_kayitlar = list(spider.kampanyalari_topla())

        if not raw_kayitlar:
            print("  ℹ️ Çekilen kampanya verisi bulunamadı (0 kayıt).")
            log_kaydi["durum"] = "kismi"
            log_collection.insert_one(log_kaydi)
            return

        # --- DOĞRUDAN MONGODB'YE KAYDETME ---
        eklenen_guncellenen = 0
        
        for kayit in raw_kayitlar:
            # Pydantic / Dataclass / Dict dönüştürme güvenliği
            if hasattr(kayit, "dict"):
                kayit_dict = kayit.dict()
            elif hasattr(kayit, "model_dump"):
                kayit_dict = kayit.model_dump()
            elif isinstance(kayit, dict):
                kayit_dict = kayit.copy()
            else:
                kayit_dict = dict(kayit)

            # Metadata ekleme
            kayit_dict["banka_kodu"] = kod
            kayit_dict["mulkiyet_turu"] = mulkiyet_turu
            kayit_dict["buyukluk_kategorisi"] = buyukluk_kategorisi
            kayit_dict["cekilis_tarihi"] = simdi
            kayit_dict["is_processed"] = False

            # URL / Link alanı kontrolü
            kampanya_url = kayit_dict.get("url") or kayit_dict.get("link")

            if kampanya_url:
                kayit_dict["url"] = kampanya_url
                
                raw_collection.update_one(
                    {"url": kampanya_url},
                    {"$set": kayit_dict},
                    upsert=True,
                )
                eklenen_guncellenen += 1
            else:
                print(f"  ⚠️ URL alanı eksik olan kayıt MongoDB'ye yazılmadı: {kayit_dict.get('baslik', 'Başlıksız')}")

        print(f"  🍃 MongoDB 'kampanyalar' koleksiyonuna {eklenen_guncellenen} kayıt başarıyla kaydedildi/güncellendi.")

        log_kaydi["durum"] = "basarili"
        log_kaydi["kampanya_sayisi"] = len(raw_kayitlar)

    except NotImplementedError:
        log_kaydi["hata_mesaji"] = "spider henüz yazılmadı"
        print("  ⏭️ Spider henüz yazılmadı, atlanıyor.")
    except Exception as hata:
        log_kaydi["hata_mesaji"] = f"{hata.__class__.__name__}: {hata}"
        print(f"  ❌ HATA: {log_kaydi['hata_mesaji']}")

    # İşlem logunu MongoDB 'scrape_logs' koleksiyonuna kaydet
    log_collection.insert_one(log_kaydi)


def main() -> None:
    parser = argparse.ArgumentParser(description="FinAgent / SmartData Veri Toplama Çalıştırıcısı")
    parser.add_argument("banka", nargs="?", help="MongoDB 'bankalar' koleksiyonundaki banka id'si (ör. albaraka)")
    parser.add_argument("--hepsi", action="store_true", help="Aktif tüm bankaları sırayla çek")
    args = parser.parse_args()

    mongo_client = None
    try:
        mongo_client, db = get_mongo_db()
        bankalar_col = db["bankalar"]

        # Hedef bankaları doğrudan MongoDB 'bankalar' koleksiyonundan çekiyoruz
        if args.hepsi:
            hedefler = list(bankalar_col.find({"aktif": True}))
            if not hedefler:
                print("⚠️ MongoDB 'bankalar' koleksiyonunda aktif banka bulunamadı!")
                return
        elif args.banka:
            hedefler = list(bankalar_col.find({"id": args.banka}))
            if not hedefler:
                # Kullanıcıya geçerli ID'leri göstermek için sorgula
                tum_bankalar = [b["id"] for b in bankalar_col.find({}, {"id": 1})]
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