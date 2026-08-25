from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
client = MongoClient(MONGO_URI)
db = client["smartdata"]
kampanyalar = db["islenmis_kampanyalar"]

print("Distinct kampanya_turu:")
for t in kampanyalar.distinct("genel_bilgi.kampanya_turu"):
    print(t)
