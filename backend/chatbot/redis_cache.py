import os
import hashlib
import redis.asyncio as aioredis
from loguru import logger

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

_redis_client = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        redis_password = os.getenv("REDIS_PASSWORD") or None
        
        # 1. Öncelik: REDIS_URL veya REDIS_HOST env tanımlıysa onu dene
        if redis_url:
            try:
                client = aioredis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1.0)
                await client.ping()
                _redis_client = client
                logger.info(f"✅ Cache modülü Redis'e REDIS_URL üzerinden bağlandı!")
                return _redis_client
            except Exception as e:
                logger.warning(f"⚠️ REDIS_URL bağlantısı başarısız ({e}), alternatifler deneniyor...")

        env_host = os.getenv("REDIS_HOST")
        env_port = int(os.getenv("REDIS_PORT", "6379"))

        olasi_adresler = []
        if env_host:
            olasi_adresler.append(env_host)
        olasi_adresler.extend([
            "host.docker.internal",
            "smartdata-redis",
            "redis",
            "172.17.0.1",
            "172.18.0.1",
            "127.0.0.1"
        ])

        for adres in olasi_adresler:
            try:
                temp_client = aioredis.Redis(
                    host=adres,
                    port=env_port,
                    password=redis_password,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=0.5
                )
                await temp_client.ping()
                _redis_client = temp_client
                logger.info(f"✅ Cache modülü Redis'e '{adres}:{env_port}' üzerinden bağlandı!")
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


# 🛠️ TEMİZLİK: get_cached_db_params()/set_cached_db_params() buradan SİLİNDİ.
# Kod tabanında hiçbir dosya bu iki fonksiyonu import etmiyor ya da çağırmıyordu
# (grep ile doğrulandı) — text-to-mongo ajanının (agents.py::yapisal_analiz_
# parametreleri_uret) parametrelerini önbelleğe almak için tasarlanmış olmalılar
# ama hiçbir zaman bağlanmamışlar. Gerçekten kullanılan tam-yanıt önbelleği
# (get_cached_full_response/set_cached_full_response, generate_response.py'de
# çağrılıyor) aşağıda korunuyor.


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