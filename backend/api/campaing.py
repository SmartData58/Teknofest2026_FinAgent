from datetime import datetime
import re
import json
import os
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from pymongo import MongoClient
from loguru import logger

# 🚀 MONGODB BAĞLANTISI
MONGO_URI = "mongodb://admin:admin123@smartdata-mongodb:27017/?authSource=admin"
client = MongoClient(MONGO_URI)
db = client["smartdata"]
kampanyalar_col = db["bankalar"]

# 🚀 REDIS BAĞLANTISI (Frontend API'si için)
REDIS_URL = os.getenv("REDIS_URL", "redis://smartdata-redis:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

router = APIRouter(tags=["kampanyalar"])

# -----------------------------------------------------------------------------
# PYDANTIC ŞEMALARI (Aynı Bırakıyoruz)
# -----------------------------------------------------------------------------

class KampanyaOzet(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: str = Field(alias="_id") 
    banka: str
    banka_kodu: str
    baslik: Optional[str] = None
    url: str = ""
    kampanya_turu: Optional[str] = None
    kar_payi_orani: Optional[float] = None
    finansman_tutari: Optional[float] = None
    vade_ay: Optional[int] = None
    taksit_sayisi: Optional[int] = None
    tahsis_ucreti: Optional[float] = None
    odul_miktari: Optional[float] = None
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
async def kampanya_listesi( # 🚀 DİKKAT: Artık asenkron (async def) çalışıyor!
    banka: Optional[str] = Query(None, description="Banka kodu (ör. kuveytturk)"),
    tur: Optional[str] = Query(None, description="Kampanya türü (ör. kart)"),
    hedef: Optional[str] = Query(None, description="Hedef kitle (ör. yeni_musteri)"),
    arama: Optional[str] = Query(None, description="Başlıkta geçen kelime"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    # 1. Filtrelere göre benzersiz bir Redis Anahtarı (Cache Key) üretiyoruz
    cache_key = f"api:campaigns:{banka}:{tur}:{hedef}:{arama}:{limit}:{offset}"
    
    # 2. ÖNCE REDİS'E BAK!
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"⚡ REDIS CACHE HIT: Kampanya listesi saniyenin binde birinde RAM'den çekildi! Key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis Okuma Hatası: {e}")

    # 3. REDİS'TE YOKSA MONGODB'Yİ YOR (Sadece ilk giren kişi için)
    logger.info("🐢 CACHE MISS: Veriler MongoDB'den çekiliyor...")
    query = {}
    if banka: query["banka_kodu"] = banka
    if tur: query["kampanya_turu"] = tur
    if hedef: query["hedef_kitle"] = hedef
    if arama: query["baslik"] = {"$regex": re.escape(arama), "$options": "i"}

    kampanyalar_cursor = kampanyalar_col.find(query).skip(offset).limit(limit)
    
    sonuclar = []
    for k in kampanyalar_cursor:
        if "_id" in k: k["_id"] = str(k["_id"])
        if isinstance(k.get("banka"), dict):
            k["banka_kodu"] = k["banka"].get("kod", k.get("banka_kodu", ""))
            k["banka"] = k["banka"].get("kisa_ad", k.get("banka", ""))
        sonuclar.append(k)

    # 4. SONUCU 1 SAATLİĞİNE (3600 sn) REDİS'E KAYDET!
    try:
        await redis_client.set(cache_key, json.dumps(sonuclar), ex=3600)
        logger.info(f"💾 REDIS CACHE SET: Veriler 1 saatliğine belleğe yazıldı. Key: {cache_key}")
    except Exception as e:
        logger.warning(f"Redis Yazma Hatası: {e}")

    return sonuclar


@router.get("/campaigns/{kampanya_id}", response_model=KampanyaDetay)
async def kampanya_detay(kampanya_id: str):
    # 1. Benzersiz Redis Anahtarı
    cache_key = f"api:campaign_detail:{kampanya_id}"
    
    # 2. Redis'ten Getir
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"⚡ REDIS CACHE HIT: Kampanya detayı RAM'den çekildi! Key: {cache_key}")
            return json.loads(cached_data)
    except Exception:
        pass

    # 3. MongoDB'den Getir
    k = kampanyalar_col.find_one({"_id": kampanya_id})
    if not k and kampanya_id.isdigit():
        k = kampanyalar_col.find_one({"_id": int(kampanya_id)})

    if k is None:
        raise HTTPException(status_code=404, detail=f"Kampanya bulunamadı: id={kampanya_id}")

    k["_id"] = str(k["_id"])
    if isinstance(k.get("banka"), dict):
        k["banka_kodu"] = k["banka"].get("kod", k.get("banka_kodu", ""))
        k["banka"] = k["banka"].get("kisa_ad", k.get("banka", ""))
        
    # 4. MongoDB'den alınanı 1 saatliğine Redis'e kaydet
    try:
        await redis_client.set(cache_key, json.dumps(k), ex=3600)
    except Exception:
        pass

    return k