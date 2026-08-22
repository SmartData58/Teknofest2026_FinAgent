# 🛠️ TEMİZLİK: `os` ve `json` importları kaldırıldı — bu dosyada artık ikisi de
# kullanılmıyor. `os` zaten önceden de kullanılmıyordu (mevcut kod hiçbir yerde
# os.* çağırmıyordu); `json` ise sadece aşağıda silinen get_cached_db_params/
# set_cached_db_params fonksiyonlarında kullanılıyordu.
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