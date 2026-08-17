import os
import yaml
from pymongo import MongoClient

def seed_bankalar():
    # MongoDB Bağlantısı (Not: Docker içinde hata alırsan 'localhost' kısmını mongo container adıyla değiştir kanka)
    client = MongoClient("mongodb://admin:admin123@smartdata-mongodb:27017/?authSource=admin")
    db = client["smartdata"]
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