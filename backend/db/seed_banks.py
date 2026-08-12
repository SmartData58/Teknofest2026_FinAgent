import yaml
from pymongo import MongoClient

def seed_bankalar():
    # MongoDB Bağlantısı
    client = MongoClient("mongodb://admin:admin123@localhost:27017/?authSource=admin")
    db = client["smartdata"]
    bankalar_col = db["bankalar"]

    # YAML dosyasını okuma
    with open("backend/configs/banks.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    banka_listesi = config.get("bankalar", [])

    for banka in banka_listesi:
        # id'yi MongoDB'nin ana anahtarı (_id) yapıyoruz
        banka["_id"] = banka["id"]
        
        # Upsert: Varsa güncelle, yoksa yeni ekle
        bankalar_col.update_one(
            {"_id": banka["_id"]},
            {"$set": banka},
            upsert=True
        )

    print(f"✅ {len(banka_listesi)} banka MongoDB 'bankalar' koleksiyonuna başarıyla aktarıldı.")

if __name__ == "__main__":
    seed_bankalar()