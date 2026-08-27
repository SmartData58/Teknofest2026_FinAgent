"""
banka_istatistikleri.py

islenmis_kampanyalar koleksiyonundaki verilere bakarak her banka için:
  - baskın kampanya türü (+ yüzdesi)
  - baskın kategori (+ yüzdesi)
  - aktif kampanya sayısı
hesaplar ve 'bankalar' koleksiyonuna yazar.

Bağımsız çalıştırılabilir:
    python banka_istatistikleri.py

Ya da başka bir yerden import edilip çağrılabilir:
    from banka_istatistikleri import banka_istatistiklerini_guncelle
    banka_istatistiklerini_guncelle(db)
"""

import os
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError


# --- MONGODB BAĞLANTI AYARLARI ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    if MONGO_PASSWORD:
        return f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    return f"mongodb://{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

MONGO_URI = _get_mongo_uri()


def _banka_baskin_alanlarini_hesapla(db, alan_yolu: str, haric_degerler: set | None = None) -> dict:
    """
    islenmis_kampanyalar koleksiyonunda verilen alan_yolu (ör: 'genel_bilgi.kampanya_turu')
    için her banka_id bazında en sık görülen değeri ve yüzdesini hesaplar.

    Dönüş: { banka_id: {"deger": str, "adet": int, "toplam": int, "yuzde": float} }
    """
    structured_col = db["islenmis_kampanyalar"]
    haric_degerler = haric_degerler or set()

    match_filtre = {
        "genel_bilgi.is_active": "aktif",
        alan_yolu: {"$nin": [None, "", *haric_degerler]},
    }

    pipeline = [
        {"$match": match_filtre},
        {"$group": {
            "_id": {"banka_id": "$genel_bilgi.banka_id", "deger": f"${alan_yolu}"},
            "adet": {"$sum": 1}
        }},
        {"$sort": {"adet": -1}},
        {"$group": {
            "_id": "$_id.banka_id",
            "baskin_deger": {"$first": "$_id.deger"},
            "baskin_adet": {"$first": "$adet"},
            "toplam": {"$sum": "$adet"}
        }}
    ]

    sonuc = {}
    for kayit in structured_col.aggregate(pipeline):
        banka_id = kayit["_id"]
        toplam = kayit["toplam"]
        yuzde = round((kayit["baskin_adet"] / toplam) * 100, 1) if toplam else 0.0
        sonuc[banka_id] = {
            "deger": kayit["baskin_deger"],
            "adet": kayit["baskin_adet"],
            "toplam": toplam,
            "yuzde": yuzde,
        }
    return sonuc


def banka_istatistiklerini_guncelle(db) -> int:
    """
    Her banka için:
      - baskın kampanya türü (+ yüzdesi)
      - baskın kategori (+ yüzdesi)
      - aktif kampanya sayısı
    hesaplayıp 'bankalar' koleksiyonuna kaydeder.

    kampanya_turu ve kategori ayrı ayrı hesaplanıp ayrı alanlara yazılır
    (frontend'de 'baskın kampanya türü' ve 'baskın kategori' ayrı gösterilebilsin diye).

    Dönüş: güncellenen banka sayısı.
    """
    bankalar_col = db["bankalar"]
    structured_col = db["islenmis_kampanyalar"]

    # "kategori" alanında extractor tarafında varsayılan değer "Genel" atanıyor.
    # Bunu gerçek bir istatistikmiş gibi göstermemek için hesaptan hariç tutuyoruz.
    baskin_turler = _banka_baskin_alanlarini_hesapla(db, "genel_bilgi.kampanya_turu")
    baskin_kategoriler = _banka_baskin_alanlarini_hesapla(
        db, "genel_bilgi.kategori", haric_degerler={"Genel"}
    )

    # Aktif kampanya sayıları
    aktif_sayilar = {
        kayit["_id"]: kayit["adet"]
        for kayit in structured_col.aggregate([
            {"$match": {"genel_bilgi.is_active": "aktif"}},
            {"$group": {"_id": "$genel_bilgi.banka_id", "adet": {"$sum": 1}}}
        ])
    }

    tum_banka_idler = set(baskin_turler) | set(baskin_kategoriler) | set(aktif_sayilar)

    if not tum_banka_idler:
        print(" ℹ️  Banka istatistiği hesaplanacak veri bulunamadı.")
        return 0

    simdi = datetime.now(timezone.utc).isoformat()
    islemler = []

    for banka_id in tum_banka_idler:
        tur_bilgi = baskin_turler.get(banka_id)
        kategori_bilgi = baskin_kategoriler.get(banka_id)

        guncelleme = {
            "aktif_kampanya_sayisi": aktif_sayilar.get(banka_id, 0),
            "baskin_kampanya_turu": tur_bilgi["deger"] if tur_bilgi else None,
            "baskin_kampanya_turu_yuzde": tur_bilgi["yuzde"] if tur_bilgi else None,
            "baskin_kategori": kategori_bilgi["deger"] if kategori_bilgi else None,
            "baskin_kategori_yuzde": kategori_bilgi["yuzde"] if kategori_bilgi else None,
            "istatistik_guncelleme_tarihi": simdi,
        }

        islemler.append(
            # upsert=False: bankalar koleksiyonu zaten önceden dolu (banka tanım
            # kayıtları), burada sadece mevcut banka dokümanlarını güncelliyoruz.
            # Tanımsız bir banka_id için yeni doküman açılmasını istemiyorsan
            # upsert=False kalsın; istersen True yap.
            UpdateOne({"_id": banka_id}, {"$set": guncelleme}, upsert=False)
        )

    if not islemler:
        return 0

    sonuc = bankalar_col.bulk_write(islemler)
    guncellenen = sonuc.modified_count
    print(f"    📊 {guncellenen} banka için istatistik güncellendi (baskın tür / kategori).")
    return guncellenen


def calistir() -> None:
    print(" 🚀 Banka istatistikleri hesaplanıyor...\n")

    client = None
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]

        guncellenen = banka_istatistiklerini_guncelle(db)

        print(f"\n🎉 İşlem Tamamlandı! {guncellenen} banka güncellendi.")

    except PyMongoError as err:
        print(f"❌ MongoDB Hata: {err}")
    except Exception as err:
        print(f"❌ İstatistik Hesaplama Hatası: {err}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    calistir()