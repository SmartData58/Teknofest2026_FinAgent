from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
client = MongoClient(MONGO_URI)
db = client["smartdata"]
kampanyalar = db["islenmis_kampanyalar"]

print("Sample Campaigns:")
for c in kampanyalar.find().limit(3):
    genel = c.get("genel_bilgi", {})
    print(f"Banka ID: {genel.get('banka_id')}, Tür: {genel.get('kampanya_turu')}")
