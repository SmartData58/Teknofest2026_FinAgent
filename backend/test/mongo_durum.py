"""
mongo_durum.py — MongoDB'de hangi veritabanında/koleksiyonda ne var, gösterir.

Container içinde çalıştırın:
    python mongo_durum.py

Neden gerekli: chatbot/indexing.py önce `smartdata.processed_campaigns`'e bakar,
BOŞSA `finagent.kampanyalar`'a düşer. Log'da "32 kampanya" görülüyorsa bu,
tools.py içindeki 32 adetlik SAHTE DEMO havuzunun yüklendiği anlamına gelir —
yani gerçek kazınmış veri sisteme hiç girmemiş demektir. Bu script hangi
koleksiyonda kaç kayıt olduğunu ve örnek bir kaydın alanlarını dökerek
gerçek verinin nerede durduğunu bulmanızı sağlar.
"""

import os
from pymongo import MongoClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    user = os.getenv("MONGO_USER", "admin")
    password = os.getenv("MONGO_PASSWORD", "")
    host = os.getenv("MONGO_HOST", "mongodb")
    port = os.getenv("MONGO_PORT", "27017")
    if password:
        return f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
    return f"mongodb://{host}:{port}/?authSource=admin"

MONGO_URI = _get_mongo_uri()

# indexing.py ve generate_response.py'nin baktığı yerler
BEKLENEN = [
    ("smartdata", "processed_campaigns"),
    ("smartdata", "extracted_fields"),
    ("smartdata", "structured_campaigns"),
    ("smartdata", "kampanyalar"),
    ("finagent", "kampanyalar"),
]


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    print("=" * 70)
    print("TÜM VERİTABANLARI VE KOLEKSİYONLAR")
    print("=" * 70)
    for db_adi in client.list_database_names():
        if db_adi in ("admin", "config", "local"):
            continue
        db = client[db_adi]
        koleksiyonlar = db.list_collection_names()
        if not koleksiyonlar:
            print(f"\n[{db_adi}]  (boş)")
            continue
        print(f"\n[{db_adi}]")
        for kol in sorted(koleksiyonlar):
            sayi = db[kol].count_documents({})
            isaret = "  <-- BURADA VERİ VAR" if sayi > 0 else ""
            print(f"    {kol:<30} {sayi:>6} kayıt{isaret}")

    print()
    print("=" * 70)
    print("UYGULAMANIN BAKTIĞI SIRA (ilk dolu olan kullanılır)")
    print("=" * 70)
    secilen = None
    for db_adi, kol in BEKLENEN:
        try:
            sayi = client[db_adi][kol].count_documents({})
        except Exception as e:
            print(f"  {db_adi}.{kol:<28} HATA: {e}")
            continue
        durum = "DOLU" if sayi else "boş"
        yildiz = ""
        if sayi and secilen is None:
            secilen = (db_adi, kol, sayi)
            yildiz = "   ***** UYGULAMA BUNU KULLANIYOR *****"
        print(f"  {db_adi}.{kol:<28} {sayi:>6} kayıt  [{durum}]{yildiz}")

    if not secilen:
        print("\n  ⚠️ Hiçbiri dolu değil — Qdrant indeksi boş kalacak.")
        client.close()
        return

    db_adi, kol, sayi = secilen
    print()
    print("=" * 70)
    print(f"ÖRNEK KAYIT — {db_adi}.{kol}")
    print("=" * 70)
    ornek = client[db_adi][kol].find_one({})
    if ornek:
        for k, v in ornek.items():
            gosterim = str(v)
            if len(gosterim) > 90:
                gosterim = gosterim[:90] + "..."
            print(f"  {k:<24} = {gosterim}")

    # Sahte demo verisi mi kontrolü
    print()
    print("=" * 70)
    print("TEŞHİS")
    print("=" * 70)
    demo_isaretleri = ["Sağlam Business Kart Erteleme", "Taksitlio'da Yeni Müşterilere",
                       "İhracatınız Fazlaysa Bonus", "Giyim Sektörüne Özel"]
    eslesme = client[db_adi][kol].count_documents({"kampanya_adi": {"$in": demo_isaretleri}})

    if sayi == 32 and eslesme >= 3:
        print("  🚨 Bu, tools.py içindeki 32 adetlik SAHTE DEMO havuzu!")
        print("     Gerçek kazınmış veriniz sisteme girmemiş.")
        print()
        print("  Yapılacaklar:")
        print("   1) Gerçek veriyi üreten pipeline'ı çalıştırın; sonucu")
        print("      smartdata.processed_campaigns koleksiyonuna yazdığından emin olun.")
        print("   2) Bu sahte kayıtları temizleyin:")
        print(f"      db.getSiblingDB('{db_adi}').{kol}.deleteMany({{}})")
        print("   3) Uygulamayı yeniden başlatın (Qdrant otomatik yeniden kurulur).")
    else:
        bankalar = client[db_adi][kol].distinct("banka_adi") or client[db_adi][kol].distinct("banka")
        print(f"  ✅ Demo verisi gibi görünmüyor. {sayi} kayıt, {len(bankalar)} farklı banka:")
        for b in sorted(str(x) for x in bankalar)[:15]:
            print(f"     - {b}")

    client.close()


if __name__ == "__main__":
    main()