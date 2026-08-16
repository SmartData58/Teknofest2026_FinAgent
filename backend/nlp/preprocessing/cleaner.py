import os
import re
import unicodedata
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")  # Docker içi varsayılan servis adı
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)


# --- SİZİN TEMİZLİK KURALLARINIZ ---
unicode_esleme = {
    # Boşluklar
    "\xa0": " ",       # Bölünmez boşluk
    "\u200b": "",      # Genişliksiz/Gizli boşluk
    "\u200c": "",      # Zero-width non-joiner
    "\ufeff": "",      # BOM (Byte Order Mark)
    
    # Kesme ve Tırnak İşaretleri
    "’": "'",          # Süslü kesme
    "‘": "'",          # Süslü sol tek tırnak
    "“": '"',          # Süslü sol çift tırnak
    "”": '"',          # Süslü sağ çift tırnak
    "„": '"',          # Alt çift tırnak
    
    # Tire ve Maddeler
    "–": "-",          # En dash
    "—": "-",          # Em dash
    "•": "",           # Madde işareti silinir
    "·": "",           # Orta nokta madde işareti silinir
    ">": "",
    "!": "",
    
    # Finansal / Genel Semboller
    "₺": "TL",         # Tek formata getirme
}

_GURULTU = [
    re.compile(r"Kampanyayı\s+Paylaş(?:\s+\S+'\s*d[ae]\s+paylaş)*", re.IGNORECASE),
    re.compile(r"\S+'\s*d[ae]\s+paylaş", re.IGNORECASE),
    re.compile(r"Sayfayı\s+Yazdır|Sayfa\s+Görüntüsü|Sayfa\s+İçeriği", re.IGNORECASE),
    re.compile(r"Ana\s+Sayfa\s*/\s*Kampanyalar\s*/?", re.IGNORECASE),
]


def unicode_normalize(metin: str) -> str:
    # Bozuk karakter birleşimlerini düzeltir
    metin = unicodedata.normalize("NFKC", metin)
    for kaynak, hedef in unicode_esleme.items():
        metin = metin.replace(kaynak, hedef)
    return metin      


def bosluk_duzelt(metin: str) -> str:
    # Ardışık birden fazla boşluğu teke indirir
    return " ".join(metin.split())


def gurultu_temizle(metin: str) -> str:
    for desen in _GURULTU:
        metin = desen.sub(" ", metin)
    return metin


def temizle(metin: str) -> str:
    if not metin or not isinstance(metin, str):
        return "" 
        
    # Bankanın standart çöplerini kesip atma giyotini
    cop_belirtecleri = [
        "Yukarıdaki QR kodunu", 
        "Merhaba, ben Alba", 
        "ÇEREZ AYDINLATMA METNİ"
    ]
    for belirtec in cop_belirtecleri:
        if belirtec in metin:
            metin = metin.split(belirtec)[0]

    metin = unicode_normalize(metin)
    metin = gurultu_temizle(metin)
    metin = bosluk_duzelt(metin)
    
    return metin


# Metadata, URL veya sistem alanı olduğu için temizlikten muaf tutulacak anahtarlar
ATLATICAK_ANAHTARLAR = {
    "_id", "url", "link", "banka_kodu", "mulkiyet_turu", 
    "buyukluk_kategorisi", "cekilis_tarihi", "is_processed"
}


def ham_verileri_temizle() -> None:
    """
    MongoDB 'kampanyalar' koleksiyonundaki işlenmemiş ham verileri okur,
    temizler ve 'temiz_kampanyalar' koleksiyonuna kaydeder.
    """
    client = None
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]

        raw_col = db["ham_kampanyalar"]
        clean_col = db["temiz_kampanyalar"]

        # Yalnızca is_processed: False veya is_processed alanı olmayan kayıtları getir
        sorgu = {"$or": [{"is_processed": False}, {"is_processed": {"$exists": False}}]}
        ham_kampanyalar = list(raw_col.find(sorgu))

        if not ham_kampanyalar:
            print(" Temizlenecek yeni ham kampanya bulunamadı.")
            return

        print(f" Toplam {len(ham_kampanyalar)} adet işlenmemiş ham kampanya temizleniyor...")

        islenen_sayisi = 0
        for doc in ham_kampanyalar:
            
            clean_doc = doc.copy()
            clean_doc.pop("is_processed", None)

            # Doküman içindeki tüm metin alanlarını (baslik, detay, icerik vs.) otomatik temizle
            for anahtar, deger in clean_doc.items():
                if anahtar not in ATLATICAK_ANAHTARLAR and isinstance(deger, str):
                    clean_doc[anahtar] = temizle(deger)

            # İşleme zamanı ve bir sonraki aşama (LLM) için bayrak ekleme
            clean_doc["temizlenme_tarihi"] = datetime.now(timezone.utc)
            clean_doc["is_extracted"] = False  # 3. Aşama (LLM) için hazır işareti

            # Temizlenmiş veriyi 'temiz_kampanyalar' koleksiyonuna yaz/güncelle
            kampanya_url = clean_doc.get("url")
            if kampanya_url:
                clean_col.update_one(
                    {"url": kampanya_url},
                    {"$set": clean_doc},
                    upsert=True
                )
            else:
                clean_col.update_one(
                    {"_id": clean_doc["_id"]},
                    {"$set": clean_doc},
                    upsert=True
                )

            # Ham verideki 'is_processed' durumunu True yap (Tekrar temizlenmesin)
            #raw_col.update_one(
                #{"_id": doc["_id"]},
                #{"$set": {"is_processed": True}}
            #)

            islenen_sayisi += 1

        print(f"✅ {islenen_sayisi} kampanya başarıyla temizlendi ve 'temiz_kampanyalar' koleksiyonuna kaydedildi.")

    except PyMongoError as err:
        print(f"❌ MongoDB İşlem Hatası: {err}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    ham_verileri_temizle()