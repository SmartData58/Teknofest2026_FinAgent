from datetime import datetime
import re
import json
import os
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder  
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from pymongo import MongoClient
from loguru import logger

# 🚀 MONGODB (Burası zaten sorunsuz çalışıyor)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")
client = MongoClient(MONGO_URI)
db = client["smartdata"]
kampanyalar_col = db["kampanyalar"]

router = APIRouter(tags=["kampanyalar"])
_redis_client = None

# 🚀 TOKAT: Docker Ağ Duvarını Delen "Akıllı Tarayıcı (Smart Fallback)" Sistemi!
async def get_redis():
    global _redis_client
    if _redis_client is None:
        # Backend ve Redis farklı ağlardaysa diye bütün muhtemel kapıları çalıyoruz:
        olasi_adresler = [
            "redis",                 # 1. İhtimal: Aynı docker-compose ağındalarsa
            "smartdata-redis",       # 2. İhtimal: Konteyner adı
            "host.docker.internal",  # 3. İhtimal: Docker Desktop Windows/Mac Köprüsü (Dışarıdan içeri sızma)
            "172.17.0.1",            # 4. İhtimal: Linux Varsayılan Docker Gateway
            "172.18.0.1",            # 5. İhtimal: Alternatif Docker Gateway
            "127.0.0.1"              # 6. İhtimal: En son çare (Lokal)
        ]
        
        for adres in olasi_adresler:
            try:
                logger.info(f"🔄 Redis kapısı zorlanıyor: {adres} ...")
                temp_client = aioredis.Redis(
                    host=adres, 
                    port=6379, 
                    db=0, 
                    decode_responses=True, 
                    socket_connect_timeout=0.5 # Hızlı pes etsin, diğerine geçsin
                )
                await temp_client.ping()
                _redis_client = temp_client
                logger.info(f"✅ BİNGO! Redis'e '{adres}' üzerinden içeri sızdık!")
                break
            except Exception:
                continue
        
        if _redis_client is None:
            logger.error("❌ HİÇBİR KAPIDAN GİRİLEMEDİ! Redis kapalı veya tamamen farklı bir ağda.")
            # Uygulama çökmesin diye boş bir istemci bırakıyoruz
            _redis_client = aioredis.Redis(host="localhost", port=6379, socket_connect_timeout=0.1)

    return _redis_client

# 🚀 YENİ EKLENTİ: Sunucu başlarken Redis ağlarını tarayacak
@router.on_event("startup")
async def startup_event():
    logger.info("🔍 Redis zırhı test ediliyor, ağlar taranıyor...")
    await get_redis()

# -----------------------------------------------------------------------------
# PYDANTIC ŞEMALARI
# -----------------------------------------------------------------------------

class KampanyaOzet(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: str = Field(default="", alias="_id") 
    banka: str = ""
    banka_kodu: str = ""
    baslik: Optional[str] = None
    url: str = ""
    kampanya_turu: Optional[str] = None
    kar_payi_orani: Optional[float] = None
    finansman_tutari: Optional[float] = None
    vade_ay: Optional[int] = None
    taksit_sayisi: Optional[int] = None
    tahsis_ucreti: Optional[float] = None
    odul_tutari_tl: Optional[float] = None
    indirim_orani: Optional[float] = None
    baslangic_tarihi: Optional[str] = None
    bitis_tarihi: Optional[str] = None
    hedef_kitle: Optional[str] = None

class KanitKaydi(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    alan_adi: str
    ham_deger: Optional[str] = None
    normalize_deger: Optional[str] = None
    yontem: str
    guven_skoru: float

class KampanyaDetay(KampanyaOzet):
    ham_metin: str = ""
    kosullar: Optional[str] = None
    odul_aciklama: Optional[str] = None
    alisveris_puani: Optional[float] = None
    masraf_bilgisi: Optional[str] = None
    cekilme_tarihi: Optional[datetime] = None
    kanitlar: List[KanitKaydi] = []

# -----------------------------------------------------------------------------
# API ENDPOINTLERİ (Redis Önbellekli Asenkron Yapı)
# -----------------------------------------------------------------------------

@router.get("/campaigns", response_model=List[KampanyaOzet])
async def kampanya_listesi(
    banka: Optional[str] = Query(None, description="Banka kodu (ör. kuveytturk)"),
    tur: Optional[str] = Query(None, description="Kampanya türü (ör. kart)"),
    hedef: Optional[str] = Query(None, description="Hedef kitle (ör. yeni_musteri)"),
    arama: Optional[str] = Query(None, description="Başlıkta geçen kelime"),
    limit: int = Query(500, ge=1, le=1000),  
    offset: int = Query(0, ge=0),
):
    redis_db = await get_redis()
    cache_key = f"api:campaigns:{banka}:{tur}:{hedef}:{arama}:{limit}:{offset}"
    
    # 1. ÖNCE REDİS'E BAK
    try:
        cached_data = await redis_db.get(cache_key)
        if cached_data:
            logger.info(f"⚡ REDIS CACHE HIT: Kampanya listesi RAM'den çekildi! Key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        pass # Artık uyarıyı gizledik, sessizce mongo'ya geçecek

    # 2. REDİS'TE YOKSA MONGODB'Yİ YOR
    logger.info("🐢 CACHE MISS: Veriler MongoDB'den çekiliyor...")
    query = {}
    if banka: query["banka_kodu"] = banka
    if tur: query["kampanya_turu"] = tur
    if hedef: query["hedef_kitle"] = hedef
    if arama: query["baslik"] = {"$regex": re.escape(arama), "$options": "i"}

    kampanyalar_cursor = kampanyalar_col.find(query).skip(offset).limit(limit)
    
    sonuclar = []
    for k in kampanyalar_cursor:
        k["_id"] = str(k["_id"])
        if isinstance(k.get("banka"), dict):
            k["banka_kodu"] = k["banka"].get("kod", k.get("banka_kodu", ""))
            k["banka"] = k["banka"].get("kisa_ad", k.get("banka", ""))
        sonuclar.append(k)

    uyumlu_sonuclar = jsonable_encoder(sonuclar)

    # 3. SONUCU 1 SAATLİĞİNE REDİS'E KAYDET
    try:
        await redis_db.set(cache_key, json.dumps(uyumlu_sonuclar), ex=3600)
        logger.info(f"💾 REDIS CACHE SET: Veriler belleğe yazıldı. Key: {cache_key}")
    except Exception as e:
        pass

    return uyumlu_sonuclar

@router.get("/campaigns/{kampanya_id}", response_model=KampanyaDetay)
async def kampanya_detay(kampanya_id: str):
    redis_db = await get_redis()
    cache_key = f"api:campaign_detail:{kampanya_id}"
    
    try:
        cached_data = await redis_db.get(cache_key)
        if cached_data:
            logger.info(f"⚡ REDIS CACHE HIT: Kampanya detayı RAM'den çekildi! Key: {cache_key}")
            return json.loads(cached_data)
    except Exception:
        pass

    k = kampanyalar_col.find_one({"_id": kampanya_id})
    
    if not k:
        from bson import ObjectId
        try:
            k = kampanyalar_col.find_one({"_id": ObjectId(kampanya_id)})
        except:
            pass

    if not k and kampanya_id.isdigit():
        k = kampanyalar_col.find_one({"_id": int(kampanya_id)})

    if k is None:
        raise HTTPException(status_code=404, detail=f"Kampanya bulunamadı: id={kampanya_id}")

    k["_id"] = str(k["_id"])
    if isinstance(k.get("banka"), dict):
        k["banka_kodu"] = k["banka"].get("kod", k.get("banka_kodu", ""))
        k["banka"] = k["banka"].get("kisa_ad", k.get("banka", ""))
        
    uyumlu_sonuc = jsonable_encoder(k)

    try:
        await redis_db.set(cache_key, json.dumps(uyumlu_sonuc), ex=3600)
    except Exception:
        pass

    return uyumlu_sonuc