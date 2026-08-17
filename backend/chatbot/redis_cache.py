import os
import json
import hashlib
import redis.asyncio as redis
from loguru import logger

# Docker Compose'da verdiğimiz isme (smartdata-redis) bağlanıyoruz
REDIS_URL = os.getenv("REDIS_URL", "redis://smartdata-redis:6379/0")

# Asenkron Redis İstemcisi
redis_db = redis.from_url(REDIS_URL, decode_responses=True)

def generate_hash_key(text: str) -> str:
    """Sorguları hash'leyerek benzersiz ve güvenli bir Redis key'i üretir."""
    return hashlib.md5(text.strip().lower().encode('utf-8')).hexdigest()

async def get_cached_db_params(query: str):
    """Kullanıcı sorusunun LLM JSON analizini önbellekten çeker."""
    key = f"db_params:{generate_hash_key(query)}"
    try:
        cached_data = await redis_db.get(key)
        if cached_data:
            logger.info("⚡ REDIS CACHE HIT: LLM yorulmadan veritabanı parametreleri RAM'den çekildi!")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis Get Hatası: {e}")
    return None

async def set_cached_db_params(query: str, params: dict, ttl_seconds: int = 86400):
    """LLM'in bulduğu parametreleri 24 saatliğine (86400 sn) Redis'e kaydeder."""
    key = f"db_params:{generate_hash_key(query)}"
    try:
        await redis_db.set(key, json.dumps(params), ex=ttl_seconds)
        logger.info("💾 REDIS CACHE SET: Ajanın kararı önbelleğe yazıldı.")
    except Exception as e:
        logger.warning(f"Redis Set Hatası: {e}")