import os
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError

# Desteklenen Bilgi Çıkarım Yöntemleri
GEÇERLİ_YÖNTEMLER = {"regex", "ner", "berturk_classifier", "llm"}

# MongoDB Bağlantı Ayarları
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)


def kanit_dokumani_olustur(doc: dict, alan_adi: str, bulgu_obj) -> dict | None:
    """
    Tek bir AlanBulgusu nesnesini Jüri Kanıt Şemasına (extracted_fields) dönüştürür.
    """
    if bulgu_obj is None:
        return None

    # Bulgu verilerini güvenli şekilde oku (AlanBulgusu nesnesi veya Dict)
    if hasattr(bulgu_obj, "deger"):
        raw_val = getattr(bulgu_obj, "ham_metin", None) or str(bulgu_obj.deger)
        norm_val = bulgu_obj.deger
        unit_val = getattr(bulgu_obj, "birim", "metin")
        method_val = getattr(bulgu_obj, "yontem", "regex")
        conf_val = getattr(bulgu_obj, "guven", 1.0)
        evidence_val = getattr(bulgu_obj, "kanit_metni", "") or doc.get("baslik", "")
        start_pos = getattr(bulgu_obj, "baslangic_konum", None)
        end_pos = getattr(bulgu_obj, "bitis_konum", None)
    elif isinstance(bulgu_obj, dict):
        norm_val = bulgu_obj.get("deger")
        raw_val = bulgu_obj.get("ham_metin", str(norm_val))
        unit_val = bulgu_obj.get("birim", "metin")
        method_val = bulgu_obj.get("yontem", "llm")
        conf_val = bulgu_obj.get("guven", 0.85)
        evidence_val = bulgu_obj.get("kanit_metni", "")
        start_pos = bulgu_obj.get("baslangic_konum")
        end_pos = bulgu_obj.get("bitis_konum")
    else:
        return None

    # Değer yoksa kanıt oluşturma
    if norm_val is None:
        return None

    # Yöntem kontrolü (Geçersiz yöntem girilirse varsayılan atar)
    if method_val not in GEÇERLİ_YÖNTEMLER:
        method_val = "regex"

    simdi = datetime.now(timezone.utc).isoformat()
    raw_campaign_id = str(doc.get("ham_kampanya_id", doc.get("_id")))
    bank_id = doc.get("banka_kodu", "genel")
    campaign_id = f"camp_{bank_id}_{doc['_id']}"

    return {
        # Benzersiz Kanıt Kimliği (Örn: field_camp_kuveytturk_001_profit_rate_percent)
        "_id": f"field_{doc['_id']}_{alan_adi}",
        
        # Kampanya Referansları
        "campaign_id": campaign_id,
        "raw_campaign_id": raw_campaign_id,
        "bank_id": bank_id,
        
        # Alan ve Değer Bilgileri
        "field_name": alan_adi,
        "raw_value": raw_val,
        "normalized_value": norm_val,
        "unit": unit_val,
        
        # Yapay Zeka / Kural İzlenebilirlik Metrikleri
        "method": method_val,                 # ["regex", "ner", "berturk_classifier", "llm"]
        "confidence_score": float(conf_val),
        "evidence_text": evidence_val,        # Jürinin okuyacağı kanıt cümlesi
        "start_char": start_pos,              # Metindeki başlangıç karakter indeksi
        "end_char": end_pos,                  # Metindeki bitiş karakter indeksi
        
        # Zaman Damgası
        "created_at": simdi
    }


def kanitlari_mongodb_kaydet(doc: dict, bulgular: dict) -> int:
    """
    Kampanyaya ait çıkarılan tüm alan kanıtlarını 'extracted_fields' koleksiyonuna toplu olarak kaydeder.
    """
    kanit_dokumanlari = []

    for alan_adi, bulgu in bulgular.items():
        kanit_doc = kanit_dokumani_olustur(doc, alan_adi, bulgu)
        if kanit_doc:
            kanit_dokumanlari.append(kanit_doc)

    if not kanit_dokumanlari:
        return 0

    client = None
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        fields_col = db["extracted_fields"]

        # Bulk (Toplu) Güncelleme/Ekleme İşlemi
        islemler = [
            UpdateOne({"_id": k["_id"]}, {"$set": k}, upsert=True)
            for k in kanit_dokumanlari
        ]
        
        sonuc = fields_col.bulk_write(islemler)
        return sonuc.upserted_count + sonuc.modified_count

    except PyMongoError as err:
        print(f"❌ Extracted Fields MongoDB Kayıt Hatası: {err}")
        return 0
    finally:
        if client:
            client.close()