from pymongo import MongoClient

# MongoDB Bağlantısı (Kendi URI ve veritabanı bilgilerinizi girin)
client = MongoClient("mongodb://localhost:27017/")
db = client["veritabani_adiniz"]
collection = db["kampanyalar"]

def kampanya_istatistiklerini_yazdir():
    # 1. Kampanya Türü Bazında Sayım
    turu_pipeline = [
        {"$group": {"_id": "$genel_bilgi.kampanya_turu", "toplam": {"$sum": 1}}},
        {"$sort": {"toplam": -1}}
    ]
    turu_sonuclari = collection.aggregate(turu_pipeline)

    print("--- KAMPANYA TÜRÜ BAZINDA SAYILAR ---")
    for doc in turu_sonuclari:
        tur_adi = doc["_id"] if doc["_id"] is not None else "Belirtilmemiş"
        print(f"Örn {tur_adi} : {doc['toplam']}")

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
        print(f"Örn {sektor_adi} : {doc['toplam']}")

if __name__ == "__main__":
    kampanya_istatistiklerini_yazdir()