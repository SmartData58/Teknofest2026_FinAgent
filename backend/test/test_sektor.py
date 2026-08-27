import os
from urllib.parse import quote_plus
from pymongo import MongoClient

# --- ENVIRONMENT AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
# Docker dışından (Windows terminalinden) erişiliyorsa localhost kullanılır
MONGO_HOST = os.getenv("MONGO_HOST", "localhost") 
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

escaped_user = quote_plus(MONGO_USER)
escaped_password = quote_plus(MONGO_PASSWORD)

# Bağlantı Dizesi
DEFAULT_URI = f"mongodb://{escaped_user}:{escaped_password}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db["islenmis_kampanyalar"]

def kampanya_istatistiklerini_yazdir():
    # 1. Kampanya Türü Bazında Sayım
    turu_pipeline = [
        {"$group": {"_id": "$genel_bilgi.kampanya_turu", "toplam": {"$sum": 1}}},
        {"$sort": {"toplam": -1}}
    ]
    turu_sonuclari = collection.aggregate(turu_pipeline)

    print("\n--- KAMPANYA TÜRÜ BAZINDA SAYILAR ---")
    for doc in turu_sonuclari:
        tur_adi = doc["_id"] if doc["_id"] is not None else "Belirtilmemiş"
        print(f" {tur_adi} : {doc['toplam']}")

    print("\n" + "="*40 + "\n")

    # 2. Sektör Bazında Sayım
    sektor_pipeline = [
        {"$group": {"_id": "$genel_bilgi.sektor", "toplam": {"$sum": 1}}},
        {"$sort": {"toplam": -1}}
    ]
    sektor_sonuclari = collection.aggregate(sektor_pipeline)

    print("--- SEKTÖR BAZINDA SAYILAR ---")
    for doc in sektor_sonuclari:
        sektor_adi = doc["_id"] if doc["_id"] is not None else "Belirtilmemiş"
        print(f" {sektor_adi} : {doc['toplam']}")

if __name__ == "__main__":
    kampanya_istatistiklerini_yazdir()