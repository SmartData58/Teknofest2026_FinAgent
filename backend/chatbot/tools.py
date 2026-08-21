import os
import json
import re
from pymongo import MongoClient
from loguru import logger

# 🚀 TOKAT: Localhost ve Şifresiz giriş iptal! Docker Compose'daki admin şifresi eklendi!
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")

# ... Kodun geri kalanı aynı kalacak
DB_NAME = "finagent"
COLLECTION_NAME = "kampanyalar"

def init_mongo_db():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Her başladığında koleksiyonu sıfırlar ki yeni veriler eklenebilsin (Test aşaması için)
        collection.drop()
        
        if collection.count_documents({}) == 0:
            # 🚀 TOKAT: Tam 32 Adetlik Dev Kampanya Havuzu (MongoDB JSON Formatında!)
            ornek_kampanyalar = [
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Sağlam Business Kart Erteleme", "kategori": "kart", "kar_payi": 3.49, "vade": 3, "odul_tl": 500.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Taksitlio'da Yeni Müşterilere", "kategori": "kart", "kar_payi": 2.99, "vade": 6, "odul_tl": 1000.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Müşterilere Özel Oran", "kategori": "kart", "kar_payi": 2.99, "vade": 12, "odul_tl": 0.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "İhracatınız Fazlaysa Bonus", "kategori": "kart", "kar_payi": 2.79, "vade": 12, "odul_tl": 2000.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Evlenecek Çiftlere", "kategori": "ihtiyaç", "kar_payi": 1.99, "vade": 24, "odul_tl": 0.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Seyahat Severlere Uçuş Kartı", "kategori": "kart", "kar_payi": 2.49, "vade": 6, "odul_tl": 1500.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Sağlam Kart Nakit Avans", "kategori": "kart", "kar_payi": 3.19, "vade": 9, "odul_tl": 300.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Market Alışverişlerine Özel", "kategori": "kart", "kar_payi": 2.89, "vade": 3, "odul_tl": 250.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Akaryakıt Kampanyası", "kategori": "kart", "kar_payi": 2.89, "vade": 5, "odul_tl": 400.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Giyim Sektörüne Özel", "kategori": "kart", "kar_payi": 2.99, "vade": 4, "odul_tl": 150.0},
                {"banka_adi": "Kuveyt Türk", "kampanya_adi": "Teknoloji Alışverişlerinde", "kategori": "kart", "kar_payi": 3.29, "vade": 12, "odul_tl": 750.0},
                {"banka_adi": "Albaraka Türk", "kampanya_adi": "Konut ve Taşıt Finansmanı", "kategori": "taşıt", "kar_payi": 2.87, "vade": 48, "odul_tl": 0.0},
                {"banka_adi": "Albaraka Türk", "kampanya_adi": "Faizsiz Pratik Kart", "kategori": "kart", "kar_payi": 0.0, "vade": 6, "odul_tl": 250.0},
                {"banka_adi": "Albaraka Türk", "kampanya_adi": "E-Ticaret Bonus Kart", "kategori": "kart", "kar_payi": 2.65, "vade": 3, "odul_tl": 450.0},
                {"banka_adi": "Albaraka Türk", "kampanya_adi": "Yurt Dışı Harcama Kartı", "kategori": "kart", "kar_payi": 3.10, "vade": 6, "odul_tl": 800.0},
                {"banka_adi": "Albaraka Türk", "kampanya_adi": "Worldcard Hoşgeldin Bonusu", "kategori": "kart", "kar_payi": 2.90, "vade": 6, "odul_tl": 550.0},
                {"banka_adi": "TOM Katılım", "kampanya_adi": "Hadi Hesaplı Kredi", "kategori": "ihtiyaç", "kar_payi": 4.99, "vade": 36, "odul_tl": 0.0},
                {"banka_adi": "TOM Katılım", "kampanya_adi": "Hadi Gold Kart", "kategori": "kart", "kar_payi": 4.50, "vade": 12, "odul_tl": 1200.0},
                {"banka_adi": "TOM Katılım", "kampanya_adi": "Gençlere Özel Hadi Kart", "kategori": "kart", "kar_payi": 4.20, "vade": 6, "odul_tl": 600.0},
                {"banka_adi": "Türkiye Finans", "kampanya_adi": "Masrafsız Finansman", "kategori": "ihtiyaç", "kar_payi": 0.0, "vade": 12, "odul_tl": 0.0},
                {"banka_adi": "Türkiye Finans", "kampanya_adi": "Happy Zero Kart", "kategori": "kart", "kar_payi": 0.0, "vade": 6, "odul_tl": 200.0},
                {"banka_adi": "Türkiye Finans", "kampanya_adi": "Happy Kart Bayram Kampanyası", "kategori": "kart", "kar_payi": 2.50, "vade": 9, "odul_tl": 850.0},
                {"banka_adi": "Türkiye Finans", "kampanya_adi": "Happy Kart Yılbaşı Çekilişi", "kategori": "kart", "kar_payi": 2.60, "vade": 12, "odul_tl": 1100.0},
                {"banka_adi": "Türkiye Finans", "kampanya_adi": "Happy Eğitim Kampanyası", "kategori": "kart", "kar_payi": 2.10, "vade": 9, "odul_tl": 650.0},
                {"banka_adi": "Vakıf Katılım", "kampanya_adi": "Sıfır Kar Paylı Taşıt", "kategori": "taşıt", "kar_payi": 0.0, "vade": 24, "odul_tl": 0.0},
                {"banka_adi": "Vakıf Katılım", "kampanya_adi": "VKart Nakit İade Kampanyası", "kategori": "kart", "kar_payi": 2.45, "vade": 6, "odul_tl": 350.0},
                {"banka_adi": "Vakıf Katılım", "kampanya_adi": "Eğitim Harcamalarına Özel", "kategori": "kart", "kar_payi": 2.10, "vade": 6, "odul_tl": 400.0},
                {"banka_adi": "Vakıf Katılım", "kampanya_adi": "Sağlık Harcamaları İadesi", "kategori": "kart", "kar_payi": 2.20, "vade": 3, "odul_tl": 300.0},
                {"banka_adi": "Ziraat Katılım", "kampanya_adi": "Tüketici Finansmanı", "kategori": "ihtiyaç", "kar_payi": 0.0, "vade": 18, "odul_tl": 0.0},
                {"banka_adi": "Ziraat Katılım", "kampanya_adi": "Ziraat Katılım Kredi Kartı", "kategori": "kart", "kar_payi": 2.75, "vade": 12, "odul_tl": 900.0},
                {"banka_adi": "Ziraat Katılım", "kampanya_adi": "Tatil ve Seyahat Fırsatı", "kategori": "kart", "kar_payi": 2.60, "vade": 6, "odul_tl": 750.0},
                {"banka_adi": "Ziraat Katılım", "kampanya_adi": "Ramazan Bayramı Harçlığı", "kategori": "kart", "kar_payi": 2.40, "vade": 3, "odul_tl": 500.0}
            ]
            collection.insert_many(ornek_kampanyalar)
            logger.info("✅ MongoDB Veritabanı 32 Kampanyalık Dev Havuzla Kuruldu!")
        client.close()
    except Exception as e:
        logger.error(f"MongoDB Bağlantı Hatası: {e}. Lütfen MongoDB'nin çalıştığından emin olun.")

init_mongo_db()

def safe_json_parse(text: str) -> dict:
    try:
        if not text or not text.strip(): return {}
        text = text.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return {}
    except Exception: return {}

def gercek_finansman_hesapla(tutar: float, vade: int, kar_payi: float) -> str:
    if kar_payi == 0: return ""
    r = kar_payi / 100
    aylik = tutar * (r * (1 + r)**vade) / (((1 + r)**vade) - 1)
    toplam = aylik * vade
    return f"| Parametre | Değer |\n| :--- | :--- |\n| **🏦 Finansman Tutarı** | {tutar:,.2f} TL |\n| **📅 Vade Süresi** | {vade} Ay |\n| **⚖️ Kâr Payı Oranı** | %{kar_payi} |\n| **💳 Aylık Taksit** | **{aylik:,.2f} TL** |\n| **💰 Toplam Geri Ödeme** | **{toplam:,.2f} TL** |"

# 🚀 NİHAİ TOKAT: OTONOM TEXT-TO-MONGO YÜRÜTÜCÜSÜ!
def grafigi_hazirla_mongo_dinamik(user_query: str, db_params: dict):
    query_lower = user_query.lower()
    chart_type = "bar" if any(w in query_lower for w in ["çubuk", "bar", "tablo", "liste"]) else "doughnut"
    
    # LLM'in Zekası Buradan Akar!
    hedef_sutun = db_params.get("hedef_sutun", "kar_payi")
    kategori = db_params.get("kategori", "hepsi")
    prefix = db_params.get("prefix", "")
    suffix = db_params.get("suffix", "")
    title = db_params.get("title", "Dinamik Pazar Analizi")
    
    # Güvenlik Zırhı
    if hedef_sutun not in ["kar_payi", "vade", "odul_tl"]:
        hedef_sutun = "kar_payi"
        prefix, suffix = "%", ""

    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]

    # 🚀 MONGODB (BSON) SORGUSUNU İNŞA EDİYORUZ
    # Temel Kural: İlgili hedef sütun boş (null) olmamalı
    mongo_query = {hedef_sutun: {"$ne": None}}

    # Ödül ve Vade aranıyorsa 0 olanları gizle ki grafik temiz kalsın
    if hedef_sutun in ["odul_tl", "vade"]:
        mongo_query[hedef_sutun] = {"$gt": 0}

    # Dinamik Kategori Filtresi (Mongo $or ile hem kategoride hem isimde arar)
    if kategori != "hepsi" and kategori in ["kart", "taşıt", "konut", "ihtiyaç"]:
        mongo_query["$or"] = [
            {"kategori": kategori},
            {"kampanya_adi": {"$regex": kategori, "$options": "i"}}
        ]

    # 🚀 Verileri büyükten küçüğe sıralıyoruz (-1)
    sonuclar = list(collection.find(mongo_query).sort(hedef_sutun, -1))
    client.close()

    labels, sub_labels, values, source_indices = [], [], [], []
    db_context = ""
    
    for idx, doc in enumerate(sonuclar):
        labels.append(doc["banka_adi"])
        sub_labels.append(doc["kampanya_adi"])
        values.append(doc[hedef_sutun])
        source_indices.append(idx + 1)
        db_context += f"- Banka: {doc['banka_adi']}, Kampanya: {doc['kampanya_adi']}, {hedef_sutun.upper()}: {doc[hedef_sutun]}\n"

    if len(labels) > 0:
        non_zero_values = [v for v in values if v > 0]
        avg_val = sum(non_zero_values) / len(non_zero_values) if len(non_zero_values) > 0 else 0
        
        chart_data = {
            "type": chart_type,
            "title": title,
            "subtitle": f"Otonom MongoDB Ajanı {len(labels)} sonucu başarıyla sıraladı.",
            "prefix": prefix, 
            "suffix": suffix, 
            "labels": labels,
            "sub_labels": sub_labels,
            "values": values,
            "source_indices": source_indices,
            "stats": {
                "avg": round(avg_val, 2),
                "min": min(values),
                "max": max(values)
            }
        }
        return f'\n\n[CHART]{json.dumps(chart_data)}[/CHART]\n\n', db_context
    return "", ""