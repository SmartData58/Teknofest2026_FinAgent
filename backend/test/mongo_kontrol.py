# -*- coding: utf-8 -*-
"""
mongo_kontrol.py — islenmis_kampanyalar koleksiyonunun GERÇEK içeriğini raporlar.

⚠️ SALT OKUNUR: hiçbir şey yazmaz, silmez, güncellemez.

Amaç: chatbot/generate_response.py::extract_campaign_data() ve
chatbot/indexing.py'nin okuduğu alan yollarının gerçekten dolu olup olmadığını
TAHMİN ETMEDEN görmek. Compass'ın şema ağacı alan ADLARINI gösteriyor ama
DEĞERLERİ ve doluluk oranını göstermiyor — asıl soru orada.

Çalıştırma (backend klasöründen ya da chatbot klasöründen, fark etmez):
    python mongo_kontrol.py

Bağlantı adresi ortam değişkeninden okunur; Docker dışından çalıştırıyorsan:
    $env:MONGO_URI="mongodb://<user>:<password>@localhost:27017/?authSource=admin"
    python mongo_kontrol.py
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from pymongo import MongoClient
except ImportError:
    raise SystemExit("pymongo kurulu değil:  pip install pymongo")

def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    user = os.getenv("MONGO_USER", "admin")
    password = os.getenv("MONGO_PASSWORD", "")
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    if password:
        return f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
    return f"mongodb://{host}:{port}/?authSource=admin"

MONGO_URI = _get_mongo_uri()
KOLEKSIYON = "islenmis_kampanyalar"

# extract_campaign_data()'nın okumaya çalıştığı yollar (öncelik sırasıyla)
KONTROL_YOLLARI = [
    "banka_kodu",                        # ÜST SEVİYE — şema ağacında görünmüyordu
    "banka_adi",
    "banka",
    "kampanya_turu",                     # üst seviye
    "hedef_kitle",                       # üst seviye
    "genel_bilgi.banka_id",
    "genel_bilgi.kampanya_adi",
    "genel_bilgi.kampanya_turu",
    "genel_bilgi.hedef_kitle",
    "genel_bilgi.kaynak_url",
    "genel_bilgi.bitis_tarihi",
    "genel_bilgi.metin",
    "finansman_detay.kar_payi_orani",
    "finansman_detay.vade_ay",
    "finansman_detay.taksit",
    "finansman_detay.finansman_tutari",
    "finansman_detay.tahsis_ucreti",
    "promosyon_detay.odul_tutari",
    "promosyon_detay.odul_metni",
    "promosyon_detay.odul_tip",
    "promosyon_detay.nakit_iade_yuzde",
    "promosyon_detay.puan_kazanc",
    "mgm_detay.kisi_basi_kazanc",
]


def kisalt(v, n=90):
    s = str(v)
    return s if len(s) <= n else s[:n] + "…"


def deger_al(doc, yol):
    """'a.b.c' yolunu güvenle okur; yoksa özel bir işaret döner."""
    parca = doc
    for anahtar in yol.split("."):
        if not isinstance(parca, dict) or anahtar not in parca:
            return "__YOK__"
        parca = parca[anahtar]
    return parca


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    # 1) Koleksiyon hangi veritabanında?
    hedef_db = None
    for db_adi in client.list_database_names():
        if db_adi in ("admin", "local", "config"):
            continue
        if KOLEKSIYON in client[db_adi].list_collection_names():
            hedef_db = db_adi
            break
    if not hedef_db:
        raise SystemExit(f"'{KOLEKSIYON}' hiçbir veritabanında bulunamadı.")

    col = client[hedef_db][KOLEKSIYON]
    toplam = col.count_documents({})
    print("=" * 78)
    print(f"KOLEKSİYON: {hedef_db}.{KOLEKSIYON}   |   {toplam} doküman")
    print("=" * 78)

    # 2) Alan doluluk raporu — asıl bilmek istediğimiz bu
    print("\n--- ALAN DOLULUK RAPORU ---")
    print(f"{'YOL':<38} {'VAR':>5} {'DOLU':>6}  ÖRNEK DEĞER (tip)")
    print("-" * 78)
    for yol in KONTROL_YOLLARI:
        var = col.count_documents({yol: {"$exists": True}})
        dolu = col.count_documents({yol: {"$nin": [None, "", 0]}})
        ornek = col.find_one({yol: {"$nin": [None, "", 0]}}, {yol: 1})
        if ornek:
            deger = deger_al(ornek, yol)
            gosterim = f"{kisalt(deger, 46)}  ({type(deger).__name__})"
        else:
            gosterim = "— hiç dolu kayıt yok —"
        isaret = " " if dolu else "⚠"
        print(f"{isaret}{yol:<37} {var:>5} {dolu:>6}  {gosterim}")

    # 3) Banka dağılımı — filtreleme bu alana bağlı
    print("\n--- BANKA ALANLARI ---")
    for yol in ("banka_kodu", "genel_bilgi.banka_id"):
        try:
            degerler = col.distinct(yol)
        except Exception as e:
            degerler = [f"(okunamadı: {e})"]
        print(f"{yol}: {len(degerler)} farklı değer")
        for d in degerler[:15]:
            print(f"    - {kisalt(d, 60)}  ({type(d).__name__})")
        if len(degerler) > 15:
            print(f"    … ve {len(degerler) - 15} tane daha")

    # 4) kar_payi_orani'nın gerçek tip dağılımı (string mi sayı mı?)
    print("\n--- kar_payi_orani TİP DAĞILIMI ---")
    for tip_adi, bson_tip in (("sayı (double/int)", ["double", "int", "long"]),
                              ("metin (string)", ["string"]),
                              ("null", ["null"])):
        adet = col.count_documents({"finansman_detay.kar_payi_orani": {"$type": bson_tip}})
        print(f"    {tip_adi:<20}: {adet}")

    # 5) taksit alanı ne? (kod bunu dict sanıyor)
    print("\n--- finansman_detay.taksit ÖRNEĞİ ---")
    ornek = col.find_one({"finansman_detay.taksit": {"$nin": [None, ""]}}, {"finansman_detay.taksit": 1})
    if ornek:
        t = deger_al(ornek, "finansman_detay.taksit")
        print(f"    tip={type(t).__name__}  değer={kisalt(t, 200)}")
    else:
        print("    — dolu kayıt yok —")

    # 6) Tam bir örnek doküman (metin alanı kısaltılmış)
    print("\n--- ÖRNEK DOKÜMAN (kâr payı DOLU olan bir kayıt) ---")
    ornek = col.find_one({"finansman_detay.kar_payi_orani": {"$nin": [None, 0]}})
    if not ornek:
        print("    (kâr payı dolu kayıt bulunamadı, rastgele bir kayıt gösteriliyor)")
        ornek = col.find_one({})
    if ornek:
        ornek = dict(ornek)
        ornek["_id"] = str(ornek.get("_id"))
        gb = ornek.get("genel_bilgi")
        if isinstance(gb, dict) and isinstance(gb.get("metin"), str):
            gb["metin"] = kisalt(gb["metin"], 200)
        print(json.dumps(ornek, indent=2, ensure_ascii=False, default=str))

    client.close()
    print("\n" + "=" * 78)
    print("Bu çıktıyı olduğu gibi paylaşabilirsin — hiçbir şey değiştirilmedi.")


if __name__ == "__main__":
    main()