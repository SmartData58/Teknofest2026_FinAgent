import os
import json
import hashlib
import redis.asyncio as aioredis
from loguru import logger

_redis_client = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        olasi_adresler = [
            "host.docker.internal",
            "smartdata-redis",
            "redis",
            "172.17.0.1",
            "172.18.0.1",
            "127.0.0.1"
        ]

        for adres in olasi_adresler:
            try:
                temp_client = aioredis.Redis(
                    host=adres,
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=0.5
                )
                await temp_client.ping()
                _redis_client = temp_client
                logger.info(f"✅ Cache modülü Redis'e '{adres}' üzerinden bağlandı!")
                break
            except Exception:
                continue

        if _redis_client is None:
            logger.error("❌ Cache modülü hiçbir adresten Redis'e bağlanamadı! Redis kapalı olabilir.")
            _redis_client = aioredis.Redis(host="localhost", port=6379, socket_connect_timeout=0.1)

    return _redis_client


def generate_hash_key(text: str) -> str:
    """Sorguları hash'leyerek benzersiz ve güvenli bir Redis key'i üretir."""
    return hashlib.md5(text.strip().lower().encode('utf-8')).hexdigest()


async def get_cached_db_params(query: str):
    redis_db = await get_redis()
    key = f"db_params:{generate_hash_key(query)}"
    try:
        cached_data = await redis_db.get(key)
        if cached_data:
            logger.info("⚡ REDIS CACHE HIT: Veritabanı parametreleri RAM'den çekildi!")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis Get Hatası: {e}")
    return None


async def set_cached_db_params(query: str, params: dict, ttl_seconds: int = 86400):
    redis_db = await get_redis()
    key = f"db_params:{generate_hash_key(query)}"
    try:
        await redis_db.set(key, json.dumps(params), ex=ttl_seconds)
    except Exception as e:
        logger.warning(f"Redis Set Hatası (db_params): {e}")


async def get_cached_full_response(query: str):
    redis_db = await get_redis()
    key = f"full_res:{generate_hash_key(query)}"
    try:
        data = await redis_db.get(key)
        if data:
            logger.info("⚡ REDIS FULL CACHE HIT: Tablo ve LLM yanıtı direkt Redis'ten verildi!")
            return data
    except Exception as e:
        logger.warning(f"Redis Get Hatası (full_response): {e}")
    return None


async def set_cached_full_response(query: str, response_text: str, ttl: int = 86400):
    redis_db = await get_redis()
    key = f"full_res:{generate_hash_key(query)}"
    try:
        await redis_db.set(key, response_text, ex=ttl)
    except Exception as e:
        logger.warning(f"Redis Set Hatası (full_response): {e}")