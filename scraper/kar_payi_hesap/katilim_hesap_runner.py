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
from pymongo import MongoClient, UpdateOne

# Bulunduğu klasörü Python'un modül arama yollarına ekler
mevcut_dizin = os.path.dirname(os.path.abspath(__file__))
if mevcut_dizin not in sys.path:
    sys.path.append(mevcut_dizin)

import vakif_katilim_hesap  
import ziraat_katilim_hesap
import albaraka_katilim_hesap


try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")
 
def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    if MONGO_PASSWORD:
        return f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    return f"mongodb://{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

MONGO_URI = _get_mongo_uri()
 
COLLECTION_NAME = "katilim_hesap"


def topla_sonuclar():
    """Her iki bankanın hesaplamalarını çalıştırıp tek bir liste halinde döndürür."""
    tum_sonuclar = []

    print("Vakıf Katılım hesaplanıyor...")
    try:
        tum_sonuclar.extend(vakif_katilim_hesap.run())
    except Exception as e:
        print(f"Vakıf Katılım hesaplanırken hata oluştu: {e}")

    print("Ziraat Katılım hesaplanıyor...")
    try:
        tum_sonuclar.extend(ziraat_katilim_hesap.run())
    except Exception as e:
        print(f"Ziraat Katılım hesaplanırken hata oluştu: {e}")
        
    print("Albaraka Katılım hesaplanıyor...")
    try:
        tum_sonuclar.extend(albaraka_katilim_hesap.run())
    except Exception as e:
        print(f"Albaraka Katılım hesaplanırken hata oluştu: {e}")
    return tum_sonuclar


def mongoya_kaydet(sonuclar):
    """Sonuç listesini MongoDB'deki katilim_hesap koleksiyonuna YAZAR (upsert).

    🛠️ Eskiden `insert_many` kullanılıyordu: boru hattı her çalıştığında aynı
    kayıtların bir kopyası daha ekleniyordu. Ölçüldü — 12 kaydın yalnızca 4'ü
    benzersizdi (3 koşu = 3 kopya); chatbot tablosunda aynı banka üst üste üç
    kez görünüyordu. Kardeş kazıyıcı (finans_hesap/finansman_runner.py) bu işi
    baştan doğru yapıyor: ayırt edici anahtar üzerinde unique index + upsert.
    Aynı kalıp buraya da uygulandı.
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    koleksiyon = db[COLLECTION_NAME]

    # Ayırt edici anahtar: aynı banka + tutar + vade tek bir kayıttır.
    try:
        koleksiyon.create_index(
            [("banka", 1), ("yatirilan_tutar", 1), ("vade", 1)],
            unique=True,
            name="banka_tutar_vade_unique",
        )
    except Exception as e:
        print(f"Index olusturulurken uyari (muhtemelen zaten mevcut): {e}")

    kayit_zamani = datetime.now(timezone.utc)
    for sonuc in sonuclar:
        sonuc["kayit_tarihi"] = kayit_zamani

    if not sonuclar:
        print("Kaydedilecek sonuç bulunamadı.")
        client.close()
        return

    islemler = [
        UpdateOne(
            {"banka": s.get("banka"),
             "yatirilan_tutar": s.get("yatirilan_tutar"),
             "vade": s.get("vade")},
            {"$set": s},
            upsert=True,
        )
        for s in sonuclar
    ]
    sonuc_yaz = koleksiyon.bulk_write(islemler, ordered=False)
    print(f"{sonuc_yaz.upserted_count} yeni, {sonuc_yaz.modified_count} güncellenen "
          f"kayıt '{COLLECTION_NAME}' koleksiyonuna yazıldı.")

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