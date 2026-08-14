import os
from datetime import datetime, timezone
from typing import Any, List, Tuple
from pymongo import MongoClient
from pymongo.database import Database


# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "smartdata-mongodb")  # Docker içi servis adı
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)


def get_mongo_db() -> Tuple[MongoClient, Database]:
    """MongoDB istemcisini başlatır ve veritabanı nesnesini döndürür."""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    return client, db


def _kayit_dict_donustur(kayit: Any) -> dict:
    """Pydantic, Dataclass veya Dict nesnesini standart bir dict'e dönüştürür."""
    if hasattr(kayit, "dict"):
        return kayit.dict()
    elif hasattr(kayit, "model_dump"):
        return kayit.model_dump()
    elif isinstance(kayit, dict):
        return kayit.copy()
    return dict(kayit)


def ham_kampanyalari_kaydet(
    banka_conf: dict, 
    raw_kayitlar: List[Any], 
    baslangic_zamani: datetime, 
    db: Database
) -> None:
    """
    Scraper tarafından çekilen ham kampanya verilerini ve işlem logunu
    MongoDB 'kampanyalar' ve 'scrape_logs' koleksiyonlarına kaydeder.
    """
    # MongoDB bankalar dokümanındaki alan eşleşmeleri
    kod = banka_conf.get("_id")
    kisa_ad = banka_conf.get("kisa_ad", kod)

    raw_collection = db["ham_kampanyalar"]
    log_collection = db["scrape_logs"]

    tarih_str = baslangic_zamani.strftime("%Y%m%d_%H%M%S")

    # String temelli güvenli Log ID 
    log_kaydi = {
        "_id": f"scrape_{kod}_{tarih_str}",
        "banka_id": kod,
        "banka_adi": kisa_ad,
        "baslama_zamani": baslangic_zamani.isoformat(),
        "durum": "failed",
        "toplam_bulunan_k_sayisi": len(raw_kayitlar),
        "yeni_eklenen_k": 0,
        "guncellenen_k": 0,
        "errors": []
    }

    if not raw_kayitlar:
        print(" Çekilen kampanya verisi bulunamadı (0 kayıt).")
        log_kaydi["status"] = "kismi"
        log_collection.insert_one(log_kaydi)
        return

    yeni_sayisi = 0
    guncellenen_sayisi = 0

    for kayit in raw_kayitlar:
        kayit_dict = _kayit_dict_donustur(kayit)

        # Bankalar koleksiyonundan gelen Meta Bilgilerini ekliyoruz
        kayit_dict["banka_adi"] = kisa_ad

        kayit_dict["cekilis_tarihi"] = datetime.now(timezone.utc).isoformat()
        kayit_dict["is_processed"] = False

        # URL / Link alan kontrolü
        kampanya_url = kayit_dict.get("url")

        if kampanya_url:
            kayit_dict["url"] = kampanya_url

            # URL'e göre tekil kayıt güncelleme veya ekleme (upsert)
            sonuc = raw_collection.update_one(
                {"url": kampanya_url},
                {"$set": kayit_dict},
                upsert=True,
            )

            if sonuc.upserted_id is not None:
                yeni_sayisi += 1
            elif sonuc.modified_count > 0:
                guncellenen_sayisi += 1
        else:
            hata_msg = f"URL alanı eksik kayıt atlandı: {kayit_dict.get('baslik', 'Başlıksız')}"
            log_kaydi["errors"].append(hata_msg)
            print(f"  ⚠️ {hata_msg}")

    # Log sonucunu güncelle ve veritabanına yaz
    log_kaydi["yeni_eklenen_k"] = yeni_sayisi
    log_kaydi["guncellenen_k"] = guncellenen_sayisi
    log_kaydi["durum"] = "basarili" if len(log_kaydi["errors"]) == 0 else "kismi"

    log_collection.insert_one(log_kaydi)
    print(f"  🍃 MongoDB 'kampanyalar' koleksiyonuna {yeni_sayisi} yeni, {guncellenen_sayisi} güncellenen kayıt yazıldı.")