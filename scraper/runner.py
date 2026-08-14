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
    """Tek bankanın spider'ını çalıştırır; verileri MongoDB 'kampanyalar' koleksiyonuna kaydeder ve detaylı log tutar."""
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

    baslangic_zamanı = datetime.now(timezone.utc)
    tarih_str = baslangic_zamanı.strftime("%Y%m%d_%H%M%S")

    # --- İSTEDİĞİNİZ LOG ŞEMASI YAPISI ---
    log_kaydi = {
        "_id": f"scrape_{kod}_{tarih_str}",
        "bank_id": kod,
        "started_at": baslangic_zamanı.isoformat(),
        "finished_at": None,
        "status": "failed",  # ['completed', 'failed', 'partial']
        "total_campaigns_found": 0,
        "errors": []
    }

    try:
        spider_class = spider_sinifini_bul(spider_adi)
        spider = spider_class()

        # Spider'dan gelen ham verileri alıyoruz
        raw_kayitlar = list(spider.kampanyalari_topla())
        log_kaydi["total_campaigns_found"] = len(raw_kayitlar)

        if not raw_kayitlar:
            print("  ℹ️ Çekilen kampanya verisi bulunamadı (0 kayıt).")
            log_kaydi["status"] = "partial"
            log_kaydi["finished_at"] = datetime.now(timezone.utc).isoformat()
            log_collection.insert_one(log_kaydi)
            return

        # --- DOĞRUDAN MONGODB'YE KAYDETME VE SAYAÇLAR ---
        yeni_sayisi = 0
        guncellenen_sayisi = 0

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
            kayit_dict["cekilis_tarihi"] = datetime.now(timezone.utc).isoformat()
            kayit_dict["is_processed"] = False

            # URL / Link alanı kontrolü
            kampanya_url = kayit_dict.get("url") or kayit_dict.get("link")

            if kampanya_url:
                kayit_dict["url"] = kampanya_url

                sonuc = raw_collection.update_one(
                    {"url": kampanya_url},
                    {"$set": kayit_dict},
                    upsert=True,
                )

                # Yeni mi eklendi yoksa güncellendi mi tespiti
                if sonuc.upserted_id is not None:
                    yeni_sayisi += 1
                elif sonuc.modified_count > 0:
                    guncellenen_sayisi += 1
            else:
                hata_msg = f"URL alanı eksik kayıt Atlandı: {kayit_dict.get('baslik', 'Başlıksız')}"
                log_kaydi["errors"].append(hata_msg)
                print(f"  ⚠️ {hata_msg}")

        log_kaydi["new_campaigns"] = yeni_sayisi
        log_kaydi["updated_campaigns"] = guncellenen_sayisi
        log_kaydi["status"] = "completed"

        print(f"  🍃 MongoDB 'kampanyalar' koleksiyonuna {yeni_sayisi} yeni, {guncellenen_sayisi} güncellenen kayıt yazıldı.")

    except NotImplementedError:
        log_kaydi["errors"].append("Spider henüz yazılmadı (NotImplementedError)")
        log_kaydi["status"] = "partial"
        print("  ⏭️ Spider henüz yazılmadı, atlanıyor.")
    except Exception as hata:
        hata_str = f"{hata.__class__.__name__}: {hata}"
        log_kaydi["errors"].append(hata_str)
        log_kaydi["status"] = "failed"
        print(f"  ❌ HATA: {hata_str}")

    finally:
        # Bitiş zamanını kaydet ve logu yaz
        log_kaydi["finished_at"] = datetime.now(timezone.utc).isoformat()
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