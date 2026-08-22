from datetime import datetime
import re
import json
import os
import asyncio
import hashlib
from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, ASCENDING
from loguru import logger

# 🛠️ Redis bağlantısı artık chatbot/redis_cache.py'den PAYLAŞILIYOR.
# Bu dosyada get_redis()'in neredeyse birebir aynı ÜÇÜNCÜ bir kopyası vardı
# (adres listesinin sırası bile farklıydı: burada "redis" önce, orada
# "host.docker.internal" önce geliyordu). İki ayrı global istemci = iki ayrı
# bağlantı havuzu ve iki farklı bağlanma davranışı demekti.
from chatbot.redis_cache import get_redis

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")

# 🛠️ Koleksiyon adı artık ortam değişkeninden ayarlanabilir.
# ⚠️ DAHA ÖNCE BURADA UYUŞMAZLIK VARDI: bu REST API varsayılan olarak
# `smartdata.kampanyalar` okuyordu — MongoDB Compass'ta doğrulandı, bu
# koleksiyonda 0 (sıfır) doküman var, yani /campaigns ucu hep boş dönüyordu.
# Gerçek veri (pipeline.py ADIM 1-3'ün yazdığı) `smartdata.islenmis_kampanyalar`
# koleksiyonunda (344 kayıt). Varsayılan artık buna güncellendi.
# chatbot/indexing.py ve chatbot/generate_response.py da AYNI koleksiyonu
# öncelikli olarak arayacak şekilde hizalandı — üçü artık aynı kaynağı okuyor.
DB_ADI = os.getenv("CAMPAIGN_DB", "smartdata")
KOLEKSIYON_ADI = os.getenv("CAMPAIGN_COLLECTION", "islenmis_kampanyalar")

# serverSelectionTimeoutMS: Mongo erişilemezse istek 30sn (varsayılan) asılı
# kalmasın, hızlıca hata versin.
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_ADI]
kampanyalar_col = db[KOLEKSIYON_ADI]

router = APIRouter(tags=["kampanyalar"])

# main.py'deki başlangıç önbellek temizliği bu ön eki de silebilsin diye dışa açık.
CACHE_ONEKI = "api:"

# 🛠️ @router.on_event("startup") KALDIRILDI.
# İki sebep:
#  1) main.py artık lifespan= kullanıyor. Starlette'te özel bir lifespan
#     verildiğinde on_startup/on_shutdown handler'ları ÇALIŞTIRILMAZ — yani bu
#     handler sessizce ölü koda dönüşmüştü (bunu main.py'yi lifespan'e
#     geçirirken ben yaptım, farkında değildim).
#  2) Zaten yalnızca Redis bağlantısını önden ısıtıyordu; get_redis() ilk
#     istekte kendiliğinden bağlanıyor, dolayısıyla işlevsel bir kaybı yok.


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


# 🛠️ Liste ucu artık MongoDB'den YALNIZCA özet alanlarını çekiyor (projeksiyon).
# Önceki hâlde tüm belge (ham_metin, kanitlar, kosullar dahil) çekiliyor,
# response_model tarafından zaten atılacak alanlar boşuna ağ üzerinden taşınıyor
# VE olduğu gibi Redis'e yazılıyordu. limit=500 varsayılanıyla tek bir önbellek
# anahtarı megabaytlarca yer kaplayabiliyordu. Projeksiyon şemadan türetiliyor
# ki model değişince elle güncellemek gerekmesin.
_OZET_PROJEKSIYONU = {(alan.alias or ad): 1 for ad, alan in KampanyaOzet.model_fields.items()}


# -----------------------------------------------------------------------------
# YARDIMCILAR
# -----------------------------------------------------------------------------

def _cache_key(*parcalar) -> str:
    """Çakışmaya dayanıklı önbellek anahtarı.

    🛠️ Eski anahtar f"api:campaigns:{banka}:{tur}:{hedef}:{arama}:..." biçimindeydi;
    parametrelerin kendisi iki nokta içerebildiği için farklı sorgular AYNI
    anahtara düşebiliyordu (ör. tur="a:b" ile tur="a", hedef="b"). Parametreler
    artık hash'leniyor.
    """
    ham = "\x00".join("" if p is None else str(p) for p in parcalar)
    return f"{CACHE_ONEKI}campaigns:{hashlib.md5(ham.encode('utf-8')).hexdigest()}"


async def _redisten_al(anahtar: str):
    try:
        redis_db = await get_redis()
        veri = await redis_db.get(anahtar)
        if veri:
            return json.loads(veri)
    except Exception as e:
        # 🛠️ Eskiden burada `pass` vardı — Redis bozuksa hiçbir iz kalmıyordu.
        logger.debug(f"Redis okuma atlandı ({anahtar}): {e}")
    return None


async def _redise_yaz(anahtar: str, veri, ttl: int = 3600) -> None:
    try:
        redis_db = await get_redis()
        await redis_db.set(anahtar, json.dumps(veri), ex=ttl)
    except Exception as e:
        logger.debug(f"Redis yazma atlandı ({anahtar}): {e}")


def _banka_alanlarini_duzelt(k: dict) -> dict:
    k["_id"] = str(k["_id"])
    if isinstance(k.get("banka"), dict):
        k["banka_kodu"] = k["banka"].get("kod", k.get("banka_kodu", ""))
        k["banka"] = k["banka"].get("kisa_ad", k.get("banka", ""))
    return k


def _listeyi_getir(query: dict, offset: int, limit: int) -> list:
    """Senkron pymongo çağrısı — asyncio.to_thread ile sarmalanarak çağrılır."""
    imlec = kampanyalar_col.find(query, _OZET_PROJEKSIYONU).skip(offset).limit(limit)
    return [_banka_alanlarini_duzelt(k) for k in imlec]


def _detayi_getir(kampanya_id: str):
    """Senkron pymongo çağrısı — _id string / ObjectId / int olabilir."""
    k = kampanyalar_col.find_one({"_id": kampanya_id})

    if not k:
        try:
            k = kampanyalar_col.find_one({"_id": ObjectId(kampanya_id)})
        except (InvalidId, TypeError):
            # 🛠️ Eskiden çıplak `except:` vardı; KeyboardInterrupt/SystemExit
            # gibi kritik sinyalleri de yutuyordu. Artık yalnızca geçersiz
            # ObjectId hataları yakalanıyor.
            k = None

    if not k and kampanya_id.isdigit():
        k = kampanyalar_col.find_one({"_id": int(kampanya_id)})

    return k


def indeksleri_kur() -> None:
    """Sorgulanan alanlar için MongoDB indekslerini oluşturur.

    Bu uç `banka_kodu`, `kampanya_turu`, `hedef_kitle` alanlarında filtreleme
    yapıyor; indeks olmadan her istek tüm koleksiyonu tarar. Uygulama açılışında
    bir kez çağrılabilir (main.py lifespan'inden) veya elle çalıştırılabilir.
    """
    try:
        kampanyalar_col.create_index([("banka_kodu", ASCENDING)], background=True)
        kampanyalar_col.create_index([("kampanya_turu", ASCENDING)], background=True)
        kampanyalar_col.create_index([("hedef_kitle", ASCENDING)], background=True)
        logger.info(f"✅ {DB_ADI}.{KOLEKSIYON_ADI} indeksleri hazır.")
    except Exception as e:
        logger.warning(f"MongoDB indeksleri oluşturulamadı: {e}")


# -----------------------------------------------------------------------------
# API ENDPOINTLERİ (Redis Önbellekli Asenkron Yapı)
# -----------------------------------------------------------------------------

@router.get("/campaigns", response_model=List[KampanyaOzet])
async def kampanya_listesi(
    banka: Optional[str] = Query(None, description="Banka kodu (ör. kuveytturk)"),
    tur: Optional[str] = Query(None, description="Kampanya türü (ör. kart)"),
    hedef: Optional[str] = Query(None, description="Hedef kitle (ör. yeni_musteri)"),
    arama: Optional[str] = Query(None, description="Başlıkta geçen kelime"),
    limit: int = Query(100, ge=1, le=1000, description="Sayfa başına kayıt"),
    offset: int = Query(0, ge=0),
):
    cache_key = _cache_key("liste", banka, tur, hedef, arama, limit, offset)

    onbellek = await _redisten_al(cache_key)
    if onbellek is not None:
        logger.info("⚡ REDIS CACHE HIT: Kampanya listesi RAM'den çekildi.")
        return onbellek

    logger.info("🐢 CACHE MISS: Veriler MongoDB'den çekiliyor...")
    query = {}
    if banka:
        query["banka_kodu"] = banka
    if tur:
        query["kampanya_turu"] = tur
    if hedef:
        query["hedef_kitle"] = hedef
    if arama:
        # re.escape: kullanıcı girdisinin regex olarak yorumlanmasını engeller.
        query["baslik"] = {"$regex": re.escape(arama), "$options": "i"}

    try:
        # 🛠️ pymongo SENKRON bir kütüphane. Eski kod bu çağrıyı doğrudan
        # `async def` içinden yapıyordu; bu, sorgu süresince TÜM olay
        # döngüsünü (event loop) bloke ediyordu — yani bu endpoint'e gelen tek
        # bir yavaş sorgu, aynı anda akan sohbet yanıtlarını (streaming) da
        # dondurabiliyordu. Artık ayrı bir thread'e devrediliyor.
        sonuclar = await asyncio.to_thread(_listeyi_getir, query, offset, limit)
    except Exception as e:
        logger.error(f"MongoDB liste sorgusu başarısız: {e}")
        raise HTTPException(status_code=503, detail="Kampanya veritabanına erişilemiyor.")

    uyumlu_sonuclar = jsonable_encoder(sonuclar)
    await _redise_yaz(cache_key, uyumlu_sonuclar)
    return uyumlu_sonuclar


@router.get("/campaigns/{kampanya_id}", response_model=KampanyaDetay)
async def kampanya_detay(kampanya_id: str):
    cache_key = f"{CACHE_ONEKI}campaign_detail:{hashlib.md5(kampanya_id.encode()).hexdigest()}"

    onbellek = await _redisten_al(cache_key)
    if onbellek is not None:
        logger.info("⚡ REDIS CACHE HIT: Kampanya detayı RAM'den çekildi.")
        return onbellek

    try:
        k = await asyncio.to_thread(_detayi_getir, kampanya_id)
    except Exception as e:
        logger.error(f"MongoDB detay sorgusu başarısız: {e}")
        raise HTTPException(status_code=503, detail="Kampanya veritabanına erişilemiyor.")

    if k is None:
        raise HTTPException(status_code=404, detail=f"Kampanya bulunamadı: id={kampanya_id}")

    uyumlu_sonuc = jsonable_encoder(_banka_alanlarini_duzelt(k))
    await _redise_yaz(cache_key, uyumlu_sonuc)
    return uyumlu_sonuc