import os
import yaml
from pymongo import MongoClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def seed_bankalar():
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        user = os.getenv("MONGO_USER", "admin")
        pwd = os.getenv("MONGO_PASSWORD", "")
        host = os.getenv("MONGO_HOST", "smartdata-mongodb")
        port = os.getenv("MONGO_PORT", "27017")
        if pwd:
            mongo_uri = f"mongodb://{user}:{pwd}@{host}:{port}/?authSource=admin"
        else:
            mongo_uri = f"mongodb://{host}:{port}/?authSource=admin"
    
    db_name = os.getenv("MONGO_DB_NAME", "smartdata")
    client = MongoClient(mongo_uri)
    db = client[db_name]
    bankalar_col = db["bankalar"]

    # 🚀 TOKAT: Dinamik dosya yolu! Kod nerede çalışırsa çalışsın config dosyasını şak diye bulur.
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yaml_path = os.path.join(BASE_DIR, "configs", "banks.yaml")

    # YAML dosyasını okuma
    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    banka_listesi = config.get("bankalar", [])

    for banka in banka_listesi:
        # id'yi MongoDB'nin ana anahtarı (_id) yapıyoruz
        banka["_id"] = banka["id"]
        
        # Upsert: Varsa güncelle, yoksa yeni ekle
        bankalar_col.update_one(
            {"_id": banka["id"]},
            {"$set": banka},
            upsert=True
        )

    print(f"✅ {len(banka_listesi)} banka MongoDB 'bankalar' koleksiyonuna başarıyla aktarıldı.")

if __name__ == "__main__":
    seed_bankalar()