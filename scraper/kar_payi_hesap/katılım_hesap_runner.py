"""
vakif_katilim.py ve ziraat_katilim.py dosyalarındaki hesaplamaları çalıştırır,
dönen sonuçları MongoDB'de 'katilim_hesap' koleksiyonuna kaydeder.

Kullanım:
    python kaydet_mongo.py

Ortam değişkenleri (opsiyonel, varsayılanlar aşağıda):
    MONGO_URI  -> mongodb://localhost:27017
    MONGO_DB   -> katilim_db
"""

import os
import sys
from datetime import datetime, timezone  # Bu satırı geri ekledik
from pymongo import MongoClient

# Bulunduğu klasörü Python'un modül arama yollarına ekler
mevcut_dizin = os.path.dirname(os.path.abspath(__file__))
if mevcut_dizin not in sys.path:
    sys.path.append(mevcut_dizin)

import vakif_katılım_hesap
import ziraat_katılım_hesap


MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")
 
DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)
 
COLLECTION_NAME = "katilim_hesap"


def topla_sonuclar():
    """Her iki bankanın hesaplamalarını çalıştırıp tek bir liste halinde döndürür."""
    tum_sonuclar = []

    print("Vakıf Katılım hesaplanıyor...")
    try:
        tum_sonuclar.extend(vakif_katılım_hesap.run())
    except Exception as e:
        print(f"Vakıf Katılım hesaplanırken hata oluştu: {e}")

    print("Ziraat Katılım hesaplanıyor...")
    try:
        tum_sonuclar.extend(ziraat_katılım_hesap.run())
    except Exception as e:
        print(f"Ziraat Katılım hesaplanırken hata oluştu: {e}")

    return tum_sonuclar


def mongoya_kaydet(sonuclar):
    """Sonuç listesini MongoDB'deki katilim_hesap koleksiyonuna kaydeder."""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    koleksiyon = db[COLLECTION_NAME]

    kayit_zamani = datetime.now(timezone.utc)
    for sonuc in sonuclar:
        sonuc["kayit_tarihi"] = kayit_zamani

    if sonuclar:
        sonuc_ekle = koleksiyon.insert_many(sonuclar)
        print(f"{len(sonuc_ekle.inserted_ids)} kayıt '{COLLECTION_NAME}' koleksiyonuna eklendi.")
    else:
        print("Kaydedilecek sonuç bulunamadı.")

    client.close()


def main():
    sonuclar = topla_sonuclar()

    print("=" * 50)
    for s in sonuclar:
        for k, v in s.items():
            print(f"{k}: {v}")
        print("-" * 50)

    mongoya_kaydet(sonuclar)


if __name__ == "__main__":
    main()