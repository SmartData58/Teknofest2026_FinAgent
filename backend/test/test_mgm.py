import os
from pymongo import MongoClient

# Projenizdeki environment değişkenlerini veya varsayılan değerleri okur
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")  # Docker dışından çalıştırıyorsanız localhost olmalı
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

def _get_mongo_uri() -> str:
    # 1. Eğer tam MONGO_URI varsa kullan
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    # 2. Şifre tanımlıysa kimlik doğrulamalı URI döndür
    if MONGO_PASSWORD:
        return f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    # 3. Şifresiz bağlantı
    return f"mongodb://{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

MONGO_URI = _get_mongo_uri()

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db["kampanyalar"]

# 2. MGM Türündeki Kampanyaları Sorgula (İlk örnek verinizdeki 'kart_kampanyasi' / 'mgm' değerine göre ayarlayın)
query = {"genel_bilgi.kampanya_turu": {"$in": ["mgm", "mgm_kampanyasi"]}}

# 3. Hizalanmış Terminal Çıktısı
header_format = "{:<15} | {:<35} | {:<18} | {:<15}"
divider = "-" * 90

print(divider)
print(header_format.format("Banka", "Kampanya Adı", "Kişi Başı Kazanç", "Max Kişi Sayısı"))
print(divider)

count = 0
for doc in collection.find(query):
    genel = doc.get("genel_bilgi", {})
    mgm = doc.get("mgm_detay", {})
    
    banka = str(genel.get("banka_id") or "-")
    kampanya = str(genel.get("kampanya_adi") or "-")
    
    if len(kampanya) > 33:
        kampanya = kampanya[:30] + "..."
        
    kazanc = str(mgm.get("kisi_basi_kazanc") or "-")
    limit = str(mgm.get("mgm_limit_kisi") or "-")
    
    print(header_format.format(banka, kampanya, kazanc, limit))
    count += 1

print(divider)
print(f"Toplam {count} adet MGM kampanyası bulundu.")