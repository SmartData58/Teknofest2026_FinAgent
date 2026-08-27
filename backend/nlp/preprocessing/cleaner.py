import os
import re
import unicodedata
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# 🛠️ ÇİFT YOL: bu modül iki farklı kökten çalıştırılıyor — pipeline.py depo
# kökünden `backend.*` diye, backend konteyneri ise WORKDIR /app (yani
# backend/) içinden `nlp.*` diye import ediyor. Tek biçim kullanmak,
# diğerinde ModuleNotFoundError veriyor ve bu yüzden geçici bir symlink
# gerekiyordu. agents.py'deki yerleşik kalıp buraya da uygulandı.
try:
    from backend.nlp.extraction.rule_based import tarihleri_cikar
except ModuleNotFoundError:
    from nlp.extraction.rule_based import tarihleri_cikar


# Tarih ayrıştırma fonksiyonunuzu içe aktarın (extractor modülünüz neredeyse oradan çekin)
# from extractor import tarihleri_cikar, AlanBulgusu

# --- MONGODB BAĞLANTI AYARLARI ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    if MONGO_PASSWORD:
        return f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    return f"mongodb://{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

MONGO_URI = _get_mongo_uri()


# --- TEMİZLİK KURALLARI VE DİĞER FONKSİYONLARINIZ (AYNEN KORUNUYOR) ---
unicode_esleme = {
    "\xa0": " ", "\u200b": "", "\u200c": "", "\ufeff": "",
    "’": "'", "‘": "'", "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "•": "", "·": "", ">": "", "!": "", "₺": "TL",
}

_GURULTU = [
    re.compile(r"Kampanyayı\s+Paylaş(?:\s+\S+'\s*d[ae]\s+paylaş)*", re.IGNORECASE),
    re.compile(r"\S+'\s*d[ae]\s+paylaş", re.IGNORECASE),
    re.compile(r"Sayfayı\s+Yazdır|Sayfa\s+Görüntüsü|Sayfa\s+İçeriği", re.IGNORECASE),
    re.compile(r"Ana\s+Sayfa\s*/\s*Kampanyalar\s*/?", re.IGNORECASE),
]

def emojileri_temizle(metin: str) -> str:
    temiz_karakterler = [char if unicodedata.category(char) not in ("So", "Sk") else "" for char in metin]
    return "".join(temiz_karakterler)

def unicode_normalize(metin: str) -> str:
    metin = unicodedata.normalize("NFKC", metin)
    for kaynak, hedef in unicode_esleme.items():
        metin = metin.replace(kaynak, hedef)
    return metin      

def bosluk_duzelt(metin: str) -> str:
    return " ".join(metin.split())

def gurultu_temizle(metin: str) -> str:
    for desen in _GURULTU:
        metin = desen.sub(" ", metin)
    return metin

def temizle(metin: str) -> str:
    if not metin or not isinstance(metin, str):
        return "" 
    cop_belirtecleri = ["Yukarıdaki QR kodunu", "Merhaba, ben Alba", "ÇEREZ AYDINLATMA METNİ"]
    for belirtec in cop_belirtecleri:
        if belirtec in metin:
            metin = metin.split(belirtec)[0]

    metin = unicode_normalize(metin)
    metin = emojileri_temizle(metin)
    metin = gurultu_temizle(metin)
    metin = bosluk_duzelt(metin)
    return metin


# =============================================================================
# YENİ EKLENEN PIPELINE (TEMİZLİK + EXTRACTION + SÜRE HESABI) ADIMI
# =============================================================================
ATLATICAK_ANAHTARLAR = {
    "_id", "url", "link", "banka_kodu", "mulkiyet_turu", 
    "buyukluk_kategorisi", "cekilis_tarihi", "is_processed", "kampanya_turu", "kategori"
}

def kampanya_objesini_temizle(ham_veri: dict) -> dict:
    """
    MongoDB'ye kaydedilmeden önceki ham veriyi alır:
    1. Tüm metinsel alanları temizler (temizle fonksiyonu ile).
    2. Siteden hazır kazınan 'tarih_metni' alanını öncelikli olarak tarar.
    3. Eğer oradan tarih bulunamazsa temizlenmiş 'ham_metin' detayını tarar.
    4. baslangic_tarihi, bitis_tarihi ve sure_gun alanlarını objeye ekler.
    """
    islenmis = ham_veri.copy()

    # 1. Metinsel Alanları Temizle
    for anahtar, deger in islenmis.items():
        if anahtar not in ATLATICAK_ANAHTARLAR and isinstance(deger, str):
            islenmis[anahtar] = temizle(deger)

    # 2. Tarih ve Süre Tespiti (Yedekli Mantık)
    tarih_metni = islenmis.get("tarih_metni", "")
    ham_metin = islenmis.get("ham_metin", "")

    tarih_bulgulari = {}

    # A Önceliği: Liste sayfasından kazınan kısa 'tarih_metni'
    if tarih_metni and str(tarih_metni).strip().lower() != "none":
        tarih_bulgulari = tarihleri_cikar(tarih_metni)

    # B Önceliği: Kısa metinden sonuç alınamadıysa detay metnini tara
    if not tarih_bulgulari.get("baslangic_tarihi") and not tarih_bulgulari.get("bitis_tarihi"):
        tarih_bulgulari = tarihleri_cikar(ham_metin)

    # 3. Sonuçları Obfeye Yaz (MongoDB'ye Hazırlık)
    if "baslangic_tarihi" in tarih_bulgulari:
        islenmis["baslangic_tarihi"] = tarih_bulgulari["baslangic_tarihi"].deger

    if "bitis_tarihi" in tarih_bulgulari:
        islenmis["bitis_tarihi"] = tarih_bulgulari["bitis_tarihi"].deger

    if "sure_gun" in tarih_bulgulari:
        islenmis["sure_gun"] = tarih_bulgulari["sure_gun"].deger

    return islenmis