import os
from pymongo import MongoClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    user = os.getenv("MONGO_USER", "admin")
    password = os.getenv("MONGO_PASSWORD", "")
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    if password:
        return f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
    return f"mongodb://{host}:{port}/?authSource=admin"

MONGO_URI = _get_mongo_uri()
client = MongoClient(MONGO_URI)
db = client["smartdata"]
kampanyalar = db["islenmis_kampanyalar"]

print("Distinct kampanya_turu:")
for t in kampanyalar.distinct("genel_bilgi.kampanya_turu"):
    print(t)
