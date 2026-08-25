import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
#MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)


def genel_kampanya_analizi():
    client = None
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        db = client[MONGO_DB_NAME]
        structured_col = db["islenmis_kampanyalar"]

        toplam_kampanya = structured_col.count_documents({})
        if toplam_kampanya == 0:
            print("❌ Koleksiyonda analiz edilecek kampanya bulunamadı.")
            return

        print("=" * 60)
        print(f"📊 KAMPANYA VERİ ALANLARI DETAYLI ANALİZ RAPORU (Toplam: {toplam_kampanya})")
        print("=" * 60)

        print("\n📌 Alanların Doluluk Durumları:")
        
        # Taksit Sayısı
        taksitli_sayisi = structured_col.count_documents({"finansman_detay.taksit": {"$exists": True, "$ne": None}})
        print(f"  • Toplam taksit sayısı bulunan kampanya sayısı: {taksitli_sayisi}")

        # Tekil Alanlar (Kâr Payı eklendi)
        alanlar = [
            ("Kâr Payı / Faiz Oranı", "finansman_detay.kar_payi_orani"),
            ("Finansman Tutarı", "finansman_detay.finansman_tutari"),
            ("Tahsis Ücreti", "finansman_detay.tahsis_ucreti"),
            ("Başlangıç Tarihi", "genel_bilgi.baslangic_tarihi"),
            ("Bitiş Tarihi", "genel_bilgi.bitis_tarihi"),
            ("Süre (Gün)", "genel_bilgi.sure_gun"),
            ("Kişi Başı Kazanç (MGM)", "mgm_detay.kisi_basi_kazanc"),
            ("MGM Limit (TL)", "mgm_detay.mgm_limit_tl")
        ]

        for etiket, alan_yolu in alanlar:
            dolu_sayi = structured_col.count_documents({alan_yolu: {"$exists": True, "$ne": None}})
            print(f"  • {etiket} Dolu Kampanya Sayısı: {dolu_sayi}")

        # %0 Kâr Paylı Kampanyalar
        sifir_kar_sayisi = structured_col.count_documents({
            "$or": [
                {"finansman_detay.kar_payi_orani": 0},
                {"finansman_detay.kar_payi_orani": 0.0},
                {"finansman_detay.kar_payi_orani": "0"},
                {"finansman_detay.kar_payi_orani": "%0"}
            ]
        })
        print(f"  • %0 Kâr Paylı / Faizsiz Kampanya Sayısı: {sifir_kar_sayisi}")

        # Özel Masraf Bilgisi
        masraf_dolu = structured_col.count_documents({
            "finansman_detay.masraf_bilgi": {
                "$exists": True, 
                "$ne": None, 
                "$nin": ["Tahsis ücreti belirtilmemiştir.", ""]
            }
        })
        print(f"  • Masraf Bilgisi Özel/Dolu Kampanya Sayısı: {masraf_dolu}")

        # MGM Aktiflik
        mgm_true_sayi = structured_col.count_documents({"mgm_detay.is_mgm": True})
        print(f"  • MGM Kampanyası (is_mgm = True) Sayısı: {mgm_true_sayi}")

        # Kâr Payı Oranı Dağılımı
        kar_payi_dagilim = list(structured_col.aggregate([
            {"$match": {"finansman_detay.kar_payi_orani": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$finansman_detay.kar_payi_orani", "adet": {"$sum": 1}}},
            {"$sort": {"adet": -1}}
        ]))
        print("\n📌 Kâr Payı / Faiz Oranlarına Göre Dağılım:")
        for item in kar_payi_dagilim:
            print(f"  • Oran: %{item['_id']} -> {item['adet']} kampanya")

        # Kampanya Türü Dağılımı
        tur_dagilim = list(structured_col.aggregate([
            {"$match": {"genel_bilgi.kampanya_turu": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$genel_bilgi.kampanya_turu", "adet": {"$sum": 1}}},
            {"$sort": {"adet": -1}}
        ]))
        print("\n📌 Kampanya Türlerine Göre Dağılım:")
        for item in tur_dagilim:
            print(f"  • {item['_id']}: {item['adet']} kampanya")

        # Hedef Kitle Dağılımı
        kitle_dagilim = list(structured_col.aggregate([
            {"$unwind": "$genel_bilgi.hedef_kitle"},
            {"$group": {"_id": "$genel_bilgi.hedef_kitle", "adet": {"$sum": 1}}},
            {"$sort": {"adet": -1}}
        ]))
        print("\n📌 Hedef Kitlesine Göre Dağılım:")
        for item in kitle_dagilim:
            print(f"  • {item['_id']}: {item['adet']} kampanya")

    except PyMongoError as err:
        print(f"❌ MongoDB Bağlantı/Sorgu Hatası: {err}")
    except Exception as err:
        print(f"❌ Hata: {err}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    genel_kampanya_analizi()