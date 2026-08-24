import os
import re
from datetime import date, datetime, timezone
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError

# Göreceli Import
from .hybrid import hibrit_cikar, _llm_var_mi


# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)

GEÇERLİ_YÖNTEMLER = {"regex", "ner", "berturk_classifier", "llm"}

# Kanıt dokümanlarında hangi kayıt tipine hangi ön ek / id alanı kullanılacağını belirler
KAYIT_TIPI_AYARLARI = {
    "kampanya": {
        "id_onek": "kamp",
        "id_alani": "kampanya_id",
        "raw_id_alani": "raw_campaign_id",
    },
    "urun": {
        "id_onek": "urun",
        "id_alani": "urun_id",
        "raw_id_alani": "raw_urun_id",
    },
}


def prepare_for_mongo(data):
    if isinstance(data, dict):
        return {k: prepare_for_mongo(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [prepare_for_mongo(i) for i in data]
    elif isinstance(data, date) and not isinstance(data, datetime):
        return data.isoformat()
    return data


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        if isinstance(val, str):
            val = val.replace("%", "").replace("TL", "").replace(".", "").replace(",", ".").strip()
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=None):
    f_val = _safe_float(val)
    return int(f_val) if f_val is not None else default


def _get_val(bulgular: dict, keys: str | list[str], default=None):
    """
    Tek bir anahtar veya alternatif anahtar listesi alarak
    bulgular nesnesinden/dict yapısından 'deger'i çeker.
    """
    if not isinstance(bulgular, dict):
        return default

    if isinstance(keys, str):
        keys = [keys]

    for key in keys:
        if key in bulgular and bulgular[key] is not None:
            obj = bulgular[key]
            if hasattr(obj, "deger"):
                if obj.deger is not None:
                    return obj.deger
            elif isinstance(obj, dict):
                if obj.get("deger") is not None:
                    return obj.get("deger")
            elif obj is not None:
                return obj

    return default


def semaya_donustur(doc: dict, bulgular: dict) -> dict:
    kar_payı = _get_val(bulgular, ["kar_payi_orani", "kar_payi"])
    vade = _get_val(bulgular, ["vade", "vade_ay"])
    finansman_tutari = _get_val(bulgular, ["finansman_tutari", "tutar"])
    masraf = _get_val(bulgular, "masraf")
    odul_tutari_tl = _get_val(bulgular, ["odul_tutari", "odul_tutari_tl"])

    # Kampanya Türü için Çoklu Anahtar Kontrolü
    kampanya_turu = _get_val(bulgular, "kampanya_turu")
    kategori = (
        doc.get("kategori") or
        doc.get("sektor") or 
        _get_val(bulgular, ["kategori", "sektor"]) or 
        "Genel"
    )
    # Banka ve ID standartlaştırma
    banka_id = doc.get("banka") or doc.get("banka_kodu") or "genel"
    raw_id = str(doc["_id"])
    kampanya_adi = doc.get("baslik") or doc.get("kampanya_adi", "")


    baslangic_tarihi = _get_val(bulgular, "baslangic_tarihi")
    bitis_tarihi = _get_val(bulgular, "bitis_tarihi")
    sure_gun = _get_val(bulgular, "sure_gun") or doc.get("sure_gun")
    
    masraf_bilgi_val = _get_val(bulgular, "masraf_bilgi")

    if not masraf_bilgi_val:
        oran = _get_val(bulgular, "tahsis_ucreti_orani")
        if oran is not None:
            masraf_bilgi_val = f"Tahsis ücreti oranı: %{oran}"
        else:
            masraf_bilgi_val = "Tahsis ücreti belirtilmemiştir."
    
    

    structured_doc = {
        "_id": f"kamp_{banka_id}_{raw_id}",
        "genel_bilgi": {
            "banka_id": banka_id,
            "temiz_kampanya_id": raw_id,
            "kampanya_adi": kampanya_adi,
            "kaynak_url": doc.get("url"),
            "baslangic_tarihi": baslangic_tarihi,
            "bitis_tarihi": bitis_tarihi,
            "sure_gun": _safe_int(sure_gun),
            "is_active": "aktif",
            "hedef_kitle": _get_val(bulgular, "hedef_kitle"),
            "kampanya_turu": kampanya_turu,
            "kategori": kategori,
            "metin": doc.get("ham_metin"),
            "cekilis_tarihi": doc.get("cekilis_tarihi")
        },
        "finansman_detay": {
            "kar_payi_orani": _safe_float(kar_payı),
            "vade_ay": _safe_int(vade),
            "finansman_tutari": _safe_float(finansman_tutari),
            "taksit": _safe_float(_get_val(bulgular, "taksit")),
            "tahsis_ucreti": _get_val(bulgular, "tahsis_ucreti_orani"),
            "masraf_bilgi": masraf_bilgi_val
        },
        "promosyon_detay": {
            "odul_tip": _get_val(bulgular, "odul_tip"),
            "odul_tutari": _safe_float(odul_tutari_tl),
            "odul_metni": _get_val(bulgular, "odul_metni"),
            "nakit_iade_yuzde": _safe_float(_get_val(bulgular, ["cashback_orani", "nakit_iade_yuzde"])),
            "puan_kazanc": _safe_float(_get_val(bulgular, "puan_kazanc")),
            "kazanc_metin": _get_val(bulgular, "kazanc_metin")
        },
        "mgm_detay": {
            #"is_mgm": False,
            "kisi_basi_kazanc": _get_val(bulgular, "kisi_basi_kazanc"),
            "mgm_limit_tl": _get_val(bulgular, "mgm_limit_tl")
        }
    }
    return structured_doc


def urun_semasina_donustur(doc: dict, bulgular: dict) -> dict:
    simdi = datetime.now(timezone.utc).isoformat()
    banka_id = doc.get("banka") or doc.get("banka_kodu") or "genel"
    raw_id = str(doc["_id"])
    
    urun_adi = doc.get("baslik") or doc.get("kampanya_adi") or _get_val(bulgular, "baslik")
    urun_kategori = _get_val(bulgular, "urun_kategori")
    
    # Scraper'dan (doc) veya NLP bulgularından alt kategori çekimi
    #kategori = doc.get("kategori") or doc.get("kategori") or _get_val(bulgular, ["kategori", "sektor"]) or "Genel"

    return {
        "_id": f"fin_{banka_id}_{raw_id}",
        "banka_id": banka_id,
        #"kategori": kategori,
        "baslik": urun_adi,  # <-- Ürün başlığı buraya eklendi
        
        "urun_kategori": urun_kategori,
        #"max_vade_ay": _safe_int(_get_val(bulgular, ["max_vade_ay", "vade"])),
        #"min_vade_ay": _safe_int(_get_val(bulgular, "min_vade_ay")),
        #"min_finansman_tutari": _safe_float(_get_val(bulgular, ["min_finansman_tutar", "finansman_tutari"])),
        #"max_finansman_tutari": _safe_float(_get_val(bulgular, "max_finansman_tutar")),
        #"standart_masraf_tutari": _safe_float(_get_val(bulgular, ["masraf_tl", "masraf"])),
        #"standart_masraf_bilgisi": _get_val(bulgular, ["masraf_bilgisi", "masraf_bilgi"]),
        "durum": "aktif",
        "olusturma_tarihi": simdi,
        "kaynak_url": doc.get("url"),
    }


def _kanit_dokumani_hazirla(doc: dict, alan_adi: str, bulgu_obj, kayit_tipi: str = "kampanya") -> dict | None:
    """
    Tek bir AlanBulgusu nesnesini Jüri Kanıt Şemasına (extracted_fields) dönüştürür.

    kayit_tipi: "kampanya" veya "urun" -> kanıt dokümanındaki id alanlarının
    ve ön eklerin hangi kayıt tipine göre üretileceğini belirler.
    """
    if bulgu_obj is None:
        return None

    if hasattr(bulgu_obj, "deger"):
        norm_deger = bulgu_obj.deger
        ham_değer = getattr(bulgu_obj, "ham_metin", None) or str(norm_deger)
        unit_val = getattr(bulgu_obj, "birim", "metin")
        metot = getattr(bulgu_obj, "yontem", "regex")
        guven_score = getattr(bulgu_obj, "guven", 1.0)
        evidence_val = getattr(bulgu_obj, "kanit_metni", "") or doc.get("baslik", "")
        start_pos = getattr(bulgu_obj, "baslangic_konum", None)
        end_pos = getattr(bulgu_obj, "bitis_konum", None)
    elif isinstance(bulgu_obj, dict):
        norm_deger = bulgu_obj.get("deger")
        ham_değer = bulgu_obj.get("ham_metin", str(norm_deger))
        unit_val = bulgu_obj.get("birim", "metin")
        metot = bulgu_obj.get("yontem", "llm")
        guven_score = bulgu_obj.get("guven", 0.85)
        evidence_val = bulgu_obj.get("kanit_metni", "")
        start_pos = bulgu_obj.get("baslangic_konum")
        end_pos = bulgu_obj.get("bitis_konum")
    else:
        return None

    if norm_deger is None:
        return None

    if metot not in GEÇERLİ_YÖNTEMLER:
        metot = "regex"

    ayar = KAYIT_TIPI_AYARLARI.get(kayit_tipi, KAYIT_TIPI_AYARLARI["kampanya"])

    simdi = datetime.now(timezone.utc).isoformat()
    banka_id = doc.get("banka") or doc.get("banka_kodu") or "genel"
    raw_id = str(doc["_id"])
    ust_kayit_id = f"{ayar['id_onek']}_{banka_id}_{raw_id}"

    kanit_doc = {
        "_id": f"field_{ayar['id_onek']}_{raw_id}_{alan_adi}",
        ayar["id_alani"]: ust_kayit_id,
        ayar["raw_id_alani"]: raw_id,
        "kayit_tipi": kayit_tipi,
        "banka_id": banka_id,
        "alan_adi": alan_adi,
        "ham_değer": ham_değer,
        "norm_deger": norm_deger,
        "unit": unit_val,
        "metod": metot,
        "evidence_text": evidence_val,
        "guven_score": float(guven_score) if guven_score is not None else 0.0,
        "start_char": start_pos,
        "end_char": end_pos,
        "created_at": simdi
    }

    # Kampanya kayıtları için geriye dönük uyumluluk (eski alan adı)
    if kayit_tipi == "kampanya":
        kanit_doc["kampanya_id"] = ust_kayit_id

    return kanit_doc


def _kampanyalari_isle(db) -> tuple[int, int]:
    """ham_kampanyalar koleksiyonunu işleyip islenmis_kampanyalar + urun (finansman_detay)
    + cıkarılan_alanlar koleksiyonlarına yazar. (islenmis_sayisi, kanit_sayisi) döner."""

    clean_col = db["ham_kampanyalar"]
    structured_col = db["islenmis_kampanyalar"]
    fields_col = db["cıkarılan_alanlar"]

    sorgu = {"$or": [{"is_extracted": False}, {"is_extracted": {"$exists": False}}]}
    temiz_kampanyalar = list(clean_col.find(sorgu))

    if not temiz_kampanyalar:
        print(" Bilgi çıkarımı yapılacak yeni temiz kampanya bulunamadı.")
        return 0, 0

    print(f" Toplam {len(temiz_kampanyalar)} kampanya Hedef Şemalara Dönüştürülüyor...")

    islanan_sayisi = 0
    toplam_kanit_sayisi = 0

    for doc in temiz_kampanyalar:
        baslik = doc.get("baslik") or doc.get("kampanya_adi", "")
        metin = doc.get("ham_metin", "")

        cikarim_sonucu = hibrit_cikar(baslik, metin) or {}

        structured_doc = prepare_for_mongo(semaya_donustur(doc, cikarim_sonucu))
        structured_col.update_one(
            {"_id": structured_doc["_id"]},
            {"$set": structured_doc},
            upsert=True
        )

        kanit_islemleri = []
        for alan_adi, bulgu in cikarim_sonucu.items():
            kanit_doc = _kanit_dokumani_hazirla(doc, alan_adi, bulgu, kayit_tipi="kampanya")
            if kanit_doc:
                kanit_doc = prepare_for_mongo(kanit_doc)
                kanit_islemleri.append(
                    UpdateOne(
                        {"_id": kanit_doc["_id"]},
                        {"$set": kanit_doc},
                        upsert=True
                    )
                )

        if kanit_islemleri:
            kanit_sonuc = fields_col.bulk_write(kanit_islemleri)
            toplam_kanit_sayisi += kanit_sonuc.upserted_count + kanit_sonuc.modified_count

        clean_col.update_one({"_id": doc["_id"]}, {"$set": {"is_extracted": True}})

        islanan_sayisi += 1
        banka_adi = doc.get("banka") or doc.get("banka_kodu") or "genel"
        print(f"    ✅ [{banka_adi.upper()}] Kampanya dönüştürüldü: {baslik[:40]}...")

    return islanan_sayisi, toplam_kanit_sayisi


def _urunleri_isle(db) -> tuple[int, int]:
    """ham_urun koleksiyonunu işleyip islenmis_urunler + cıkarılan_alanlar
    koleksiyonlarına yazar. (islenmis_sayisi, kanit_sayisi) döner."""

    ham_urun_col = db["ham_urun"]
    islenmis_urun_col = db["islenmis_urunler"]
    fields_col = db["cıkarılan_alanlar"]

    sorgu = {"$or": [{"is_extracted": False}, {"is_extracted": {"$exists": False}}]}
    ham_urunler = list(ham_urun_col.find(sorgu))

    if not ham_urunler:
        print(" Bilgi çıkarımı yapılacak yeni ham ürün bulunamadı.")
        return 0, 0

    print(f" Toplam {len(ham_urunler)} ürün Hedef Şemalara Dönüştürülüyor...")

    islanan_sayisi = 0
    toplam_kanit_sayisi = 0

    for doc in ham_urunler:
        baslik = doc.get("baslik") or doc.get("kampanya_adi", "")
        metin = doc.get("ham_metin", "")

        cikarim_sonucu = hibrit_cikar(baslik, metin) or {}

        urun_doc = prepare_for_mongo(urun_semasina_donustur(doc, cikarim_sonucu))
        # urun_semasina_donustur "_id"yi "fin_" ile üretiyor; ham_urun kaynaklı
        # kayıtları kampanyadan türeyen "urun" koleksiyonuyla karıştırmamak için
        # burada "urn_" ön ekiyle yeniden üretiyoruz.
        banka_id = doc.get("banka") or doc.get("banka_kodu") or "genel"
        raw_id = str(doc["_id"])
        urun_doc["_id"] = f"urn_{banka_id}_{raw_id}"
        urun_doc["kaynak_kayit_id"] = raw_id

        islenmis_urun_col.update_one(
            {"_id": urun_doc["_id"]},
            {"$set": urun_doc},
            upsert=True
        )

        kanit_islemleri = []
        for alan_adi, bulgu in cikarim_sonucu.items():
            kanit_doc = _kanit_dokumani_hazirla(doc, alan_adi, bulgu, kayit_tipi="urun")
            if kanit_doc:
                kanit_doc = prepare_for_mongo(kanit_doc)
                kanit_islemleri.append(
                    UpdateOne(
                        {"_id": kanit_doc["_id"]},
                        {"$set": kanit_doc},
                        upsert=True
                    )
                )

        if kanit_islemleri:
            kanit_sonuc = fields_col.bulk_write(kanit_islemleri)
            toplam_kanit_sayisi += kanit_sonuc.upserted_count + kanit_sonuc.modified_count

        ham_urun_col.update_one({"_id": doc["_id"]}, {"$set": {"is_extracted": True}})

        islanan_sayisi += 1
        banka_adi = doc.get("banka") or doc.get("banka_kodu") or "genel"
        print(f"    ✅ [{banka_adi.upper()}] Ürün dönüştürüldü: {baslik[:40]}...")

    return islanan_sayisi, toplam_kanit_sayisi


def temiz_verilerden_bilgi_cikar() -> None:

    print(" 🔍 LLM servisi kontrol ediliyor...")
    if not _llm_var_mi():
        print(" ⚠️  UYARI: LLM servisine erişilemedi! İşlem Regex/Kural bazlı modda devam edecek.")
    else:
        print(" ✅ LLM servisi hazır ve aktif.")

    print(" 🚀 Veritabanı işlemleri başlatılıyor...\n")

    client = None
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]

        # 1. KAMPANYALAR
        kampanya_sayisi, kampanya_kanit_sayisi = _kampanyalari_isle(db)

        # 2. FİNANSMAN ÜRÜNLERİ (spider'ların urunleri_topla() ile topladığı ham_urun verisi)
        print()
        urun_sayisi, urun_kanit_sayisi = _urunleri_isle(db)

        toplam_kanit_sayisi = kampanya_kanit_sayisi + urun_kanit_sayisi

        print(f"\n🎉 İşlem Tamamlandı!")
        print(f"   • {kampanya_sayisi} kampanya 'islenmis_kampanyalar' koleksiyonuna kaydedildi.")
        print(f"   • {urun_sayisi} ürün 'islenmis_urunler' koleksiyonuna kaydedildi (spider kaynaklı).")
        print(f"   • {toplam_kanit_sayisi} alan kanıtı 'cıkarılan_alanlar' koleksiyonuna kaydedildi.")

    except PyMongoError as err:
        print(f"❌ MongoDB Hata: {err}")
    except Exception as err:
        print(f"❌ Dönüştürme Hatası: {err}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    temiz_verilerden_bilgi_cikar()