"""
finansman_runner.py

Elimizdeki banka bazlı scraper fonksiyonlarını sırayla çalıştırır ve her
bankanın kendi koleksiyonuna yazdığı verileri, tek bir ortak koleksiyon
olan "finansman_urun" altında toplar.

VARSAYIM: Her banka scripti, ekteki finansman_vakif.py dosyasındaki gibi
"finansmanX()" adında bir fonksiyon içeriyor ve kendi koleksiyonuna
(finansman_teklifleri_<banka>) doğrudan insert_one ile yazıyor.

Eğer fonksiyon/dosya adları aşağıdaki listeden farklıysa, sadece
BANKA_MODULLERI sözlüğünü kendi dosya/fonksiyon adlarınıza göre güncellemeniz
yeterli. Kod, her bankayı bağımsız try/except içinde çalıştırır; biri
hata verse dahi diğerleri çalışmaya devam eder.
"""
import os
import importlib
import traceback
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne, InsertOne

# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")


DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)

UNIFIED_COLLECTION_NAME = "finansman_urun"

# --- Banka -> (modül adı, fonksiyon adı, o bankanın yazdığı koleksiyon) ---
# Modül adı, aynı dizindeki .py dosyasının adıdır (uzantısız).
# Gerekirse burayı kendi dosya isimlerinize göre düzenleyin.
BANKA_MODULLERI = {
    "vakif": {
        "modul": "finansman_vakif",
        "fonksiyon": "finansmanVakif",
        "koleksiyon": "finansman_urun",
    },
    "kuveyt": {
        "modul": "finansman_kuveytturk",
        "fonksiyon": "finansmanKuveyt",
        "koleksiyon": "finansman_urun",
    },
    "ziraat": {
        "modul": "finansman_ziraat",
        "fonksiyon": "finansmanZiraat",
        "koleksiyon": "finansman_urun",
    },
    "albaraka": {
        "modul": "finansman_albaraka",
        "fonksiyon": "finansmanAlbaraka",
        "koleksiyon": "finansman_urun",
    },
    "turkiye_finans": {
        "modul": "finansman_dunyakatilim",
        "fonksiyon": "finansmanDunyaKatilim",
        "koleksiyon": "finansman_urun",
    },
    # emlak_katilim ve dunya_katilim scriptleriniz hazır olduğunda
    # buraya aynı şablonla ekleyebilirsiniz.
}


def bankayi_calistir(banka_key: str, bilgi: dict) -> bool:
    """İlgili bankanın scraper fonksiyonunu çalıştırır. Başarılıysa True döner."""
    modul_adi = bilgi["modul"]
    fonksiyon_adi = bilgi["fonksiyon"]

    print(f"\n=== [{banka_key}] {modul_adi}.{fonksiyon_adi}() calistiriliyor ===")
    try:
        modul = importlib.import_module(modul_adi)
        fonksiyon = getattr(modul, fonksiyon_adi)
        fonksiyon()
        print(f"[{banka_key}] tamamlandi.")
        return True
    except ModuleNotFoundError:
        print(f"[{banka_key}] UYARI: '{modul_adi}.py' bulunamadi, atlaniyor.")
    except AttributeError:
        print(f"[{banka_key}] UYARI: '{fonksiyon_adi}' fonksiyonu '{modul_adi}' icinde bulunamadi, atlaniyor.")
    except Exception:
        print(f"[{banka_key}] HATA: scraper calisirken sorun olustu:")
        traceback.print_exc()
    return False


def koleksiyonu_birlestir(db, banka_key: str, kaynak_koleksiyon: str, hedef_koleksiyon):
    """
    Bankanın kendi koleksiyonundaki dokumanlari, ortak finansman_urun
    koleksiyonuna upsert eder. Ayirt edici anahtar:
    (banka, urun_kodu, finansman_tutari, vade)
    Bu sayede runner tekrar calistirilirsa ayni kayitlar duplike edilmez,
    guncel degerlerle uzerine yazilir.
    """
    kaynak = db[kaynak_koleksiyon]
    islemler = []
    now = datetime.now(timezone.utc)

    for doc in kaynak.find({}):
        filtre = {
            "banka": doc.get("banka", banka_key),
            "urun_kodu": doc.get("urun_kodu"),
            "finansman_tutari": doc.get("finansman_tutari"),
            "vade": doc.get("vade"),
        }
        guncelleme = dict(doc)
        guncelleme.pop("_id", None)
        guncelleme["guncellenme_tarihi"] = now

        islemler.append(UpdateOne(filtre, {"$set": guncelleme}, upsert=True))

    if not islemler:
        print(f"[{banka_key}] '{kaynak_koleksiyon}' icinde birlestirilecek kayit bulunamadi.")
        return 0

    sonuc = hedef_koleksiyon.bulk_write(islemler, ordered=False)
    toplam = sonuc.upserted_count + sonuc.modified_count
    print(f"[{banka_key}] {toplam} kayit '{UNIFIED_COLLECTION_NAME}' koleksiyonuna aktarildi "
          f"(yeni: {sonuc.upserted_count}, guncellenen: {sonuc.modified_count}).")
    return toplam


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    hedef_koleksiyon = db[UNIFIED_COLLECTION_NAME]

    # Ayirt edici anahtar uzerinde unique index (varsa olusturmaz, hata vermez)
    try:
        hedef_koleksiyon.create_index(
            [("banka", 1), ("urun_kodu", 1), ("finansman_tutari", 1), ("vade", 1)],
            unique=True,
            name="banka_urun_tutar_vade_unique",
        )
    except Exception as e:
        print(f"Index olusturulurken uyari (muhtemelen zaten mevcut): {e}")

    toplam_aktarilan = 0
    basarili_bankalar = []
    basarisiz_bankalar = []

    for banka_key, bilgi in BANKA_MODULLERI.items():
        basarili = bankayi_calistir(banka_key, bilgi)
        if basarili:
            basarili_bankalar.append(banka_key)
            aktarilan = koleksiyonu_birlestir(db, banka_key, bilgi["koleksiyon"], hedef_koleksiyon)
            toplam_aktarilan += aktarilan
        else:
            basarisiz_bankalar.append(banka_key)

    #print("\n=== OZET ===")
    #print(f"Basarili bankalar: {basarili_bankalar}")
    #print(f"Basarisiz/atlanan bankalar: {basarisiz_bankalar}")
    #print(f"Toplam '{UNIFIED_COLLECTION_NAME}' koleksiyonuna aktarilan/guncellenen kayit: {toplam_aktarilan}")

    client.close()


if __name__ == "__main__":
    main()