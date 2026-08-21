import os
import json
import hashlib
import redis.asyncio as aioredis
from loguru import logger

_redis_client = None

# 🚀 TOKAT: Docker Ağ Duvarını Delen "Akıllı Tarayıcı (Smart Fallback)" Sistemi!
async def get_redis():
    global _redis_client
    if _redis_client is None:
        # Tıpkı API'de yaptığımız gibi bütün muhtemel kapıları çalıyoruz
        olasi_adresler = [
            "host.docker.internal",  # 1. İhtimal: Docker Desktop Köprüsü (Bizi kurtaran kapı!)
            "smartdata-redis",       # 2. İhtimal: Konteyner adı
            "redis",                 # 3. İhtimal: Servis adı
            "172.17.0.1",            # 4. İhtimal: Linux Varsayılan Docker Gateway
            "172.18.0.1",            # 5. İhtimal: Alternatif Docker Gateway
            "127.0.0.1"              # 6. İhtimal: En son çare (Lokal)
        ]
        
        for adres in olasi_adresler:
            try:
                # logger.info(f"🔄 Redis kapısı zorlanıyor (Cache Modülü): {adres} ...")
                temp_client = aioredis.Redis(
                    host=adres, 
                    port=6379, 
                    db=0, 
                    decode_responses=True, 
                    socket_connect_timeout=0.5 # Hızlı pes edip sonrakine geçsin
                )
                await temp_client.ping()
                _redis_client = temp_client
                logger.info(f"✅ BİNGO! Cache Modülü Redis'e '{adres}' üzerinden içeri sızdık!")
                break
            except Exception:
                continue
        
        if _redis_client is None:
            logger.error("❌ CACHE MODÜLÜ HİÇBİR KAPIDAN GİREMEDİ! Redis kapalı olabilir.")
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
    except Exception:
        pass


# 🚀 YENİ: FULL RESPONSE CACHE (LLM'i atlayıp tabloyu ve metni direkt fırlatmak için)
async def get_cached_full_response(query: str):
    redis_db = await get_redis()
    key = f"full_res:{generate_hash_key(query)}"
    try:
        data = await redis_db.get(key)
        if data:
            logger.info("⚡ REDIS FULL CACHE HIT: Tablo ve LLM yanıtı direkt Redis'ten verildi!")
            return data
    except Exception: 
        pass
    return None


async def set_cached_full_response(query: str, response_text: str, ttl: int=86400):
    redis_db = await get_redis()
    key = f"full_res:{generate_hash_key(query)}"
    try:
        await redis_db.set(key, response_text, ex=ttl)
    except Exception: 
        pass