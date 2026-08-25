from datetime import datetime
import re
import json
import yaml
import os
import asyncio
import hashlib
from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any, Union
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, ASCENDING
from loguru import logger

from chatbot.redis_cache import get_redis

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")
DB_ADI = os.getenv("CAMPAIGN_DB", "smartdata")
KOLEKSIYON_ADI = os.getenv("CAMPAIGN_COLLECTION", "islenmis_kampanyalar")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_ADI]
kampanyalar_col = db[KOLEKSIYON_ADI]
bankalar_col = db["bankalar"]

router = APIRouter(tags=["kampanyalar"])
CACHE_ONEKI = "api:"

class FinansmanDetay(BaseModel):
    kar_payi_orani: Optional[float] = None
    vade_ay: Optional[int] = None
    finansman_tutari: Optional[float] = None
    tahsis_ucreti: Optional[float] = None
    masraf_bilgi: Optional[str] = None
    taksit: Optional[Any] = None

class GenelBilgi(BaseModel):
    kampanya_adi: Optional[str] = None
    banka_id: Optional[str] = None
    hedef_kitle: Optional[List[str]] = None
    kampanya_turu: Optional[str] = None
    kategori: Optional[str] = None
    metin: Optional[str] = None
    is_active: Optional[Any] = None
    baslangic_tarihi: Optional[str] = None
    bitis_tarihi: Optional[str] = None
    cekilis_tarihi: Optional[str] = None
    kaynak_url: Optional[str] = None
    alt_kategori: Optional[str] = None
    sure_gun: Optional[Any] = None
    temiz_kampanya_id: Optional[str] = None

class PromosyonDetay(BaseModel):
    odul_metni: Optional[str] = None
    odul_tutari: Optional[float] = None
    nakit_iade_yuzde: Optional[float] = None
    kazanc_metin: Optional[str] = None
    odul_tip: Optional[str] = None
    puan_kazanc: Optional[Any] = None

class MgmDetay(BaseModel):
    is_mgm: Optional[bool] = None
    kisi_basi_kazanc: Optional[float] = None
    mgm_limit_tl: Optional[float] = None

class KampanyaOzet(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: str = Field(default="", alias="_id")
    finansman_detay: Optional[FinansmanDetay] = None
    genel_bilgi: Optional[GenelBilgi] = None
    promosyon_detay: Optional[PromosyonDetay] = None
    mgm_detay: Optional[MgmDetay] = None

class KampanyaDetay(KampanyaOzet):
    pass

class Banka(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: str = Field(default="", alias="_id")
    kisa_ad: Optional[str] = None
    resmi_ad: Optional[str] = None
    tier: Optional[str] = None
    mulkiyet_turu: Optional[str] = None
    aktif_buyukluk_milyar_tl: Optional[float] = None
    baskin_kategori: Optional[str] = None
    baskin_kategori_yuzde: Optional[Union[float, int]] = None
    logo_url: Optional[str] = None
    aktif: Optional[bool] = True
    is_monitored: Optional[bool] = True

_OZET_PROJEKSIYONU = {(alan.alias or ad): 1 for ad, alan in KampanyaOzet.model_fields.items()}

def _cache_key(*parcalar) -> str:
    ham = "\x00".join("" if p is None else str(p) for p in parcalar)
    return f"{CACHE_ONEKI}campaigns:{hashlib.md5(ham.encode('utf-8')).hexdigest()}"

async def _redisten_al(anahtar: str):
    try:
        redis_db = await get_redis()
        veri = await redis_db.get(anahtar)
        if veri:
            return json.loads(veri)
    except Exception as e:
        logger.debug(f"Redis okuma atlandi ({anahtar}): {e}")
    return None

async def _redise_yaz(anahtar: str, veri, ttl: int = 3600) -> None:
    try:
        redis_db = await get_redis()
        await redis_db.set(anahtar, json.dumps(veri), ex=ttl)
    except Exception as e:
        logger.debug(f"Redis yazma atlandi ({anahtar}): {e}")

def _id_duzelt(k: dict) -> dict:
    if "_id" in k:
        k["_id"] = str(k["_id"])
    return k

def _listeyi_getir(query: dict, offset: int, limit: int) -> list:
    imlec = kampanyalar_col.find(query, _OZET_PROJEKSIYONU).skip(offset).limit(limit)
    return [_id_duzelt(k) for k in imlec]

def _detayi_getir(kampanya_id: str):
    k = kampanyalar_col.find_one({"_id": kampanya_id})
    if not k:
        try:
            k = kampanyalar_col.find_one({"_id": ObjectId(kampanya_id)})
        except (InvalidId, TypeError):
            k = None
    if not k and kampanya_id.isdigit():
        k = kampanyalar_col.find_one({"_id": int(kampanya_id)})
    return k

def _bankalari_getir() -> list:
    # banks.yaml dosyasından oku
    config_yolu = os.path.join(os.path.dirname(__file__), "..", "configs", "banks.yaml")
    try:
        with open(config_yolu, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            bankalar = data.get("bankalar", [])
            for b in bankalar:
                b["_id"] = b["id"]  # Frontend uyumluluğu için
            return bankalar
    except Exception as e:
        logger.error(f"banks.yaml okunamadi: {e}")
        # Fallback: DB'den dön
        return [_id_duzelt(b) for b in bankalar_col.find()]

def indeksleri_kur() -> None:
    try:
        kampanyalar_col.create_index([("genel_bilgi.banka_id", ASCENDING)], background=True)
        kampanyalar_col.create_index([("genel_bilgi.kampanya_turu", ASCENDING)], background=True)
        kampanyalar_col.create_index([("genel_bilgi.hedef_kitle", ASCENDING)], background=True)
        logger.info(f"YENI SEMA indeksleri hazir.")
    except Exception as e:
        logger.warning(f"MongoDB indeksleri olusturulamadi: {e}")

@router.get("/banks", response_model=List[Banka])
async def banka_listesi():
    cache_key = f"{CACHE_ONEKI}banks:list"
    onbellek = await _redisten_al(cache_key)
    if onbellek is not None:
        return onbellek

    try:
        sonuclar = await asyncio.to_thread(_bankalari_getir)
    except Exception as e:
        logger.error(f"MongoDB bankalar sorgusu basarisiz: {e}")
        raise HTTPException(status_code=503, detail="Banka veritabanina erisilemiyor.")

    uyumlu_sonuclar = jsonable_encoder(sonuclar)
    await _redise_yaz(cache_key, uyumlu_sonuclar)
    return uyumlu_sonuclar

@router.get("/campaigns", response_model=List[KampanyaOzet])
async def kampanya_listesi(
    banka: Optional[str] = Query(None, description="Banka id"),
    tur: Optional[str] = Query(None, description="Kampanya turu"),
    hedef: Optional[str] = Query(None, description="Hedef kitle"),
    arama: Optional[str] = Query(None, description="Baslikta gecen kelime"),
    limit: int = Query(100, ge=1, le=1000, description="Sayfa basina kayit"),
    offset: int = Query(0, ge=0),
):
    cache_key = _cache_key("liste_v2", banka, tur, hedef, arama, limit, offset)

    onbellek = await _redisten_al(cache_key)
    if onbellek is not None:
        return onbellek

    query = {}
    if banka:
        query["genel_bilgi.banka_id"] = banka
    if tur:
        query["genel_bilgi.kampanya_turu"] = tur
    if hedef:
        query["genel_bilgi.hedef_kitle"] = hedef
    if arama:
        query["genel_bilgi.kampanya_adi"] = {"$regex": re.escape(arama), "$options": "i"}

    try:
        sonuclar = await asyncio.to_thread(_listeyi_getir, query, offset, limit)
    except Exception as e:
        logger.error(f"MongoDB liste sorgusu basarisiz: {e}")
        raise HTTPException(status_code=503, detail="Kampanya veritabanina erisilemiyor.")

    uyumlu_sonuclar = jsonable_encoder(sonuclar)
    await _redise_yaz(cache_key, uyumlu_sonuclar)
    return uyumlu_sonuclar


@router.get("/campaigns/top-advantageous")
async def top_advantageous_campaigns():
    cache_key = _cache_key("top_advantageous")
    cached = await _redisten_al(cache_key)
    if cached:
        return cached
        
    try:
        # Get all valid campaigns
        all_campaigns = await asyncio.to_thread(_listeyi_getir, {"gecerlilik.gecerli_mi": {"$ne": False}}, 0, 1000)
    except Exception as e:
        logger.error(f"MongoDB list query failed: {e}")
        raise HTTPException(status_code=503, detail="Database error.")
        
    def parse_float(val):
        if val is None or str(val).strip().lower() in ['', 'none', 'null']:
            return None
        try:
            return float(str(val).replace(',', '.'))
        except:
            return None

    # Filter and sort helper
    def get_top(key_path, reverse=False, limit=3):
        valid_items = []
        for c in all_campaigns:
            parts = key_path.split('.')
            val = c
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = None
                    break
            
            f_val = parse_float(val)
            if f_val is not None and f_val >= 0:
                # Exclude 0 for vade and odul
                if parts[-1] in ['vade_ay', 'odul_tutari'] and f_val <= 0:
                    continue
                valid_items.append((f_val, c))
                
        sorted_items = sorted(valid_items, key=lambda x: x[0], reverse=reverse)
        
        return [
            {
                "id": str(item[1].get("_id")),
                "banka": item[1].get("genel_bilgi", {}).get("banka_id"),
                "baslik": item[1].get("genel_bilgi", {}).get("kampanya_adi"),
                "deger": item[0],
                "tur": item[1].get("genel_bilgi", {}).get("kampanya_turu")
            } for item in sorted_items[:limit]
        ]

    result = {
        "lowest_profit": get_top("finansman_detay.kar_payi_orani", reverse=False, limit=3),
        "highest_reward": get_top("promosyon_detay.odul_tutari", reverse=True, limit=3),
        "longest_term": get_top("finansman_detay.vade_ay", reverse=True, limit=3),
        "lowest_fee": get_top("finansman_detay.tahsis_ucreti", reverse=False, limit=3),
        "highest_loan": get_top("finansman_detay.finansman_tutari", reverse=True, limit=3),
        "highest_mgm": get_top("mgm_detay.kisi_basi_kazanc", reverse=True, limit=3),
        "highest_cashback": get_top("promosyon_detay.nakit_iade_yuzde", reverse=True, limit=3)
    }
    
    await _redise_yaz(cache_key, result, ttl=3600)
    return result

@router.get("/campaigns/compare")
async def compare_campaigns(ids: str = Query(..., description="Comma separated campaign IDs")):
    cache_key = _cache_key(f"compare_v2_{ids}")
    cached = await _redisten_al(cache_key)
    if cached:
        return cached
        
    id_list = [i.strip() for i in ids.split(',') if i.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="No valid IDs provided.")
        
    query_ids = []
    for i in id_list:
        query_ids.append(i)
        if ObjectId.is_valid(i):
            query_ids.append(ObjectId(i))
            
    try:
        cursor = kampanyalar_col.find({"_id": {"$in": query_ids}})
        results = [_id_duzelt(doc) for doc in cursor]
    except Exception as e:
        logger.error(f"MongoDB compare query failed: {e}")
        raise HTTPException(status_code=503, detail="Database error.")
        
    formatted_results = []
    for c in results:
        doc_id = str(c.get("_id"))
        formatted_results.append({
            "_id": doc_id,
            "id": doc_id,
            "banka": c.get("genel_bilgi", {}).get("banka_id"),
            "baslik": c.get("genel_bilgi", {}).get("kampanya_adi"),
            "genel_bilgi": c.get("genel_bilgi", {}),
            "finansman_detay": c.get("finansman_detay", {}),
            "promosyon_detay": c.get("promosyon_detay", {}),
            "mgm_detay": c.get("mgm_detay", {})
        })
        
    uyumlu_sonuclar = jsonable_encoder(formatted_results)
    await _redise_yaz(cache_key, uyumlu_sonuclar, ttl=3600)
    return uyumlu_sonuclar

@router.get("/campaigns/{kampanya_id}", response_model=KampanyaDetay)
async def kampanya_detay(kampanya_id: str):
    cache_key = f"{CACHE_ONEKI}campaign_detail_v2:{hashlib.md5(kampanya_id.encode()).hexdigest()}"

    onbellek = await _redisten_al(cache_key)
    if onbellek is not None:
        return onbellek

    try:
        k = await asyncio.to_thread(_detayi_getir, kampanya_id)
    except Exception as e:
        logger.error(f"MongoDB detay sorgusu basarisiz: {e}")
        raise HTTPException(status_code=503, detail="Kampanya veritabanina erisilemiyor.")

    if k is None:
        raise HTTPException(status_code=404, detail=f"Kampanya bulunamadi: id={kampanya_id}")

    uyumlu_sonuc = jsonable_encoder(_id_duzelt(k))
    await _redise_yaz(cache_key, uyumlu_sonuc)
    return uyumlu_sonuc
