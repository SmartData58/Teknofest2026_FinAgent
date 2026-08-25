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
finansman_col = db["finansman_urun"]

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


BANK_CODE_MAP = {
    "albaraka": "albaraka",
    "kuveyt": "kuveytturk",
    "kuveytturk": "kuveytturk",
    "vakif": "vakif_katilim",
    "vakif_katilim": "vakif_katilim",
    "ziraat": "ziraat_katilim",
    "ziraat_katilim": "ziraat_katilim",
    "dunya_katilim": "dunya_katilim",
    "turkiye_finans": "turkiye_finans",
    "emlak_katilim": "emlak_katilim",
    "hayat_finans": "hayat_finans",
    "tom_katilim": "tom_katilim",
    "adil_katilim": "adil_katilim"
}

def _parse_num(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    s = s.replace('TL', '').replace('tl', '').replace('%', '').replace('₺', '').strip()
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except Exception:
        return 0.0

@router.get("/finansman")
async def get_finansman_urunleri(
    banka: Optional[str] = Query(None, description="Banka kodu (virgülle ayrılmış çoklu olabilir)"),
    urun: Optional[str] = Query(None, description="Ürün türü: ihtiyac, konut, tasit"),
    tutar: Optional[float] = Query(None, description="Finansman tutarı"),
    vade: Optional[int] = Query(None, description="Vade süresi (ay)"),
    sort_by: Optional[str] = Query("kar_orani", description="Sıralama: kar_orani, aylik_taksit, toplam_tutar, vade, tutar"),
    order: Optional[str] = Query("asc", description="Sıralama yönü: asc, desc")
):
    cache_key = _cache_key(f"finansman_{banka}_{urun}_{tutar}_{vade}_{sort_by}_{order}")
    cached = await _redisten_al(cache_key)
    if cached is not None:
        return cached

    # Bankalar sözlüğü
    bankalar_cursor = bankalar_col.find({})
    banka_dict = {b.get("_id"): b for b in bankalar_cursor}

    # MongoDB Filtresi
    q = {}
    if banka:
        b_list = [b.strip() for b in banka.split(',') if b.strip()]
        matched_codes = []
        for b_item in b_list:
            matched_codes.append(b_item)
            for k, v in BANK_CODE_MAP.items():
                if b_item in (k, v):
                    matched_codes.extend([k, v])
        q["banka"] = {"$in": list(set(matched_codes))}

    if urun:
        u_list = [u.strip() for u in urun.split(',') if u.strip()]
        q["urun"] = {"$in": u_list}

    if tutar is not None and tutar > 0:
        q["finansman_tutari"] = tutar

    if vade is not None and vade > 0:
        q["vade"] = vade

    raw_docs = list(finansman_col.find(q))

    # Dinamik filtre seçenekleri
    all_raw = list(finansman_col.find({}, {"banka": 1, "urun": 1, "finansman_tutari": 1, "vade": 1}))
    distinct_banks_raw = sorted(list(set(d.get("banka") for d in all_raw if d.get("banka"))))
    distinct_products = sorted(list(set(d.get("urun") for d in all_raw if d.get("urun"))))
    distinct_amounts = sorted(list(set(d.get("finansman_tutari") for d in all_raw if d.get("finansman_tutari") is not None)))
    distinct_terms = sorted(list(set(d.get("vade") for d in all_raw if d.get("vade") is not None)))

    # Banka filtrelerini zenginleştir
    filters_banks = []
    for b_raw in distinct_banks_raw:
        b_id = BANK_CODE_MAP.get(b_raw, b_raw)
        b_info = banka_dict.get(b_id, {})
        filters_banks.append({
            "code": b_raw,
            "bank_id": b_id,
            "name": b_info.get("kisa_ad", b_raw.replace('_', ' ').title()),
            "logo_url": b_info.get("logo_url", "/logo.svg")
        })

    products = []
    for doc in raw_docs:
        doc_id = str(doc.get("_id"))
        b_raw = doc.get("banka", "")
        b_id = BANK_CODE_MAP.get(b_raw, b_raw)
        b_info = banka_dict.get(b_id, {})

        kar_orani_raw = doc.get("kar_orani")
        kar_orani_val = _parse_num(kar_orani_raw)

        taksit_raw = doc.get("aylik_taksit_tutari")
        taksit_val = _parse_num(taksit_raw)

        toplam_raw = doc.get("geri_odenecek_toplam_tutar")
        toplam_val = _parse_num(toplam_raw)

        tutar_val = doc.get("finansman_tutari") or 0
        vade_val = doc.get("vade") or 0

        tahsis_val = _parse_num(doc.get("tahsis_ucreti"))
        ipotek_val = _parse_num(doc.get("ipotek_tesis_ucreti"))
        ekspertiz_val = _parse_num(doc.get("ekspertiz_ucreti"))

        guncellenme = doc.get("guncellenme_tarihi")
        if isinstance(guncellenme, datetime):
            guncellenme_str = guncellenme.strftime("%d.%m.%Y")
        else:
            guncellenme_str = str(guncellenme) if guncellenme else ""

        products.append({
            "id": doc_id,
            "banka_kodu": b_raw,
            "banka_id": b_id,
            "banka_adi": b_info.get("kisa_ad", b_raw.replace('_', ' ').title()),
            "resmi_ad": b_info.get("resmi_ad", ""),
            "logo_url": b_info.get("logo_url", "/logo.svg"),
            "tier": b_info.get("tier", "Tier 2"),
            "urun": doc.get("urun", ""),
            "urun_kodu": doc.get("urun_kodu", ""),
            "finansman_tutari": tutar_val,
            "vade": vade_val,
            "kar_orani": kar_orani_val,
            "kar_orani_str": kar_orani_raw or f"%{kar_orani_val:.2f}".replace('.', ','),
            "aylik_taksit_tutari": taksit_val,
            "aylik_taksit_str": taksit_raw or f"{taksit_val:,.2f} TL",
            "geri_odenecek_toplam_tutar": toplam_val,
            "geri_odenecek_toplam_str": toplam_raw or f"{toplam_val:,.2f} TL",
            "tahsis_ucreti": tahsis_val,
            "tahsis_ucreti_str": doc.get("tahsis_ucreti") or (f"{tahsis_val:,.2f} TL" if tahsis_val else "0,00 TL"),
            "ipotek_tesis_ucreti": ipotek_val,
            "ipotek_tesis_ucreti_str": doc.get("ipotek_tesis_ucreti") or "0,00 TL",
            "ekspertiz_ucreti": ekspertiz_val,
            "ekspertiz_ucreti_str": doc.get("ekspertiz_ucreti") or "0,00 TL",
            "guncellenme_tarihi": guncellenme_str
        })

    # Sıralama
    reverse_order = (order.lower() == "desc")
    if sort_by == "kar_orani":
        if not reverse_order:
            key_fn = lambda x: (1 if x["kar_orani"] <= 0 else 0, x["kar_orani"])
        else:
            key_fn = lambda x: x["kar_orani"]
    elif sort_by == "aylik_taksit":
        key_fn = lambda x: (1 if x["aylik_taksit_tutari"] <= 0 else 0, x["aylik_taksit_tutari"]) if not reverse_order else lambda x: x["aylik_taksit_tutari"]
    elif sort_by == "toplam_tutar":
        key_fn = lambda x: (1 if x["geri_odenecek_toplam_tutar"] <= 0 else 0, x["geri_odenecek_toplam_tutar"]) if not reverse_order else lambda x: x["geri_odenecek_toplam_tutar"]
    elif sort_by == "vade":
        key_fn = lambda x: x["vade"]
    elif sort_by == "tutar":
        key_fn = lambda x: x["finansman_tutari"]
    else:
        key_fn = lambda x: (1 if x["kar_orani"] <= 0 else 0, x["kar_orani"])

    products = sorted(products, key=key_fn, reverse=reverse_order)

    # İstatistikler
    valid_rates = [p["kar_orani"] for p in products if p["kar_orani"] > 0]
    min_rate = min(valid_rates) if valid_rates else 0.0
    avg_rate = (sum(valid_rates) / len(valid_rates)) if valid_rates else 0.0

    valid_installments = [p["aylik_taksit_tutari"] for p in products if p["aylik_taksit_tutari"] > 0]
    min_installment = min(valid_installments) if valid_installments else 0.0

    valid_totals = [p["geri_odenecek_toplam_tutar"] for p in products if p["geri_odenecek_toplam_tutar"] > 0]
    min_total = min(valid_totals) if valid_totals else 0.0

    best_rate_product = next((p for p in products if p["kar_orani"] == min_rate), None) if min_rate > 0 else None

    result = {
        "total_count": len(products),
        "products": products,
        "filters": {
            "banks": filters_banks,
            "products": distinct_products,
            "amounts": distinct_amounts,
            "terms": distinct_terms
        },
        "stats": {
            "min_rate": min_rate,
            "avg_rate": round(avg_rate, 2),
            "min_installment": min_installment,
            "min_total": min_total,
            "best_bank": best_rate_product.get("banka_adi") if best_rate_product else "-"
        }
    }

    result_encoded = jsonable_encoder(result)
    await _redise_yaz(cache_key, result_encoded, ttl=1800)
    return result_encoded
