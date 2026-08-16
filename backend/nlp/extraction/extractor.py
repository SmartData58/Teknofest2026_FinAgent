import os
from datetime import date, datetime, timezone
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError

# Göreceli Import
from .hybrid import hibrit_cikar

# --- MONGODB BAĞLANTI AYARLARI ---
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartdata")

DEFAULT_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)

# Geçerli NLP / Çıkarım Metotları (Jüri İzlenebilirliği İçin)
GEÇERLİ_YÖNTEMLER = {"regex", "ner", "berturk_classifier", "llm"}


def prepare_for_mongo(data):
    """
    Sözlük, liste veya nesne içindeki tüm `datetime.date` değerlerini
    PyMongo'nun BSON olarak kabul edeceği ISO metnine ('YYYY-MM-DD') dönüştürür.
    """
    if isinstance(data, dict):
        return {k: prepare_for_mongo(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [prepare_for_mongo(i) for i in data]
    elif isinstance(data, date) and not isinstance(data, datetime):
        return data.isoformat()
    return data


def _safe_float(val, default=None):
    """Metin veya Sayısal veriyi güvenli bir şekilde float'a dönüştürür."""
    if val is None:
        return default
    try:
        if isinstance(val, str):
            val = val.replace("%", "").replace("TL", "").replace(".", "").replace(",", ".").strip()
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=None):
    """Metin veya Sayısal veriyi güvenli bir şekilde int'e dönüştürür."""
    f_val = _safe_float(val)
    return int(f_val) if f_val is not None else default


def _get_val(bulgular: dict, key: str, default=None):
    """
    AlanBulgusu nesnesinden veya dict yapısından ham değeri (deger) güvenli şekilde çeker.
    """
    if not isinstance(bulgular, dict) or key not in bulgular or bulgular[key] is None:
        return default
    
    obj = bulgular[key]
    if hasattr(obj, "deger"):
        return obj.deger if obj.deger is not None else default
    elif isinstance(obj, dict):
        return obj.get("deger", default)
    return default


def semaya_donustur(doc: dict, bulgular: dict) -> dict:
    """
    Kural + LLM hibrit çıkarım sonuçlarını hedef Türkçe Altın Kampanya Şeması'na dönüştürür.
    """
    k_kar_paylasim_orani = _get_val(bulgular, "k_kar_paylasim_orani")
    finansman_tutari = _get_val(bulgular, "finansman_tutari")
    taksit = _get_val(bulgular, "taksit")
    odul_tutari_tl = _get_val(bulgular, "odul_tutari_tl")
    indirim_orani_yuzde = _get_val(bulgular, "indirim_orani_yuzde")
    puan_kazanc = _get_val(bulgular, "puan_kazan") or _get_val(bulgular, "paun_kazanc")
    min_harcama_tl = _get_val(bulgular, "min_harcama_tl")

    banka_kodu = doc.get("banka_kodu", "genel")
    raw_id = str(doc["_id"])

    structured_doc = {
        "_id": f"kamp_{banka_kodu}_{raw_id}",
        "genel_bilgi": {
            "banka_id": banka_kodu,
            "temiz_kampanya_id": raw_id,
            "kampanya_adi": doc.get("kampanya_adi"),
            "kaynak_url": doc.get("url"),
            "baslangic_tarihi": _get_val(bulgular, "baslangic_tarihi"),
            "bitis_tarihi": _get_val(bulgular, "bitis_tarihi"),
            "sure_gun": doc.get("sure_gun"),
            "is_active": "aktif",
            "hedef_kitle": _get_val(bulgular, "hedef_kitle", ["tum_musteriler"]),
            "kampanya_turu": _get_val(bulgular, "kampanya_turu"),
            "alt_kategori": _get_val(bulgular, "alt_kategori")
        },
        "finansman_detay": {
            "k_kar_paylasım_orani": _safe_float(k_kar_paylasim_orani),
            "k_vade_ay": _safe_int(taksit),
            "k_finansman_tutari": _safe_float(finansman_tutari),
            "taksit": taksit,
            "hesaplanan_kar_tl": doc.get("hesaplanan_kar_tl"),
            "k_tahsis_ucreti": _get_val(bulgular, "tahsis_ucreti"),
            "k_masraf_bilgi": _get_val(bulgular, "masraf_bilgi", "Tahsis ücreti belirtilmemiştir.")
        },
        "promosyon_detay": {
            "odul_tutari_tl": _safe_float(odul_tutari_tl),
            "odul_metni": _get_val(bulgular, "odul_metni"),
            "nakit_iade_yuzde": _safe_float(_get_val(bulgular, "cashback_orani")),
            "indirim_orani_yuzde": _safe_float(indirim_orani_yuzde),
            "puan_kazanc": _safe_float(puan_kazanc),
            "min_harcama_tl": _safe_float(min_harcama_tl),
            "kazanc_metin": _get_val(bulgular, "kazanc_metin")
        },
        "mgm_detay": {
            "kisi_basi_kazanc": _get_val(bulgular, "kisi_basi_kazanc"),
            "mgm_limit_tl": _get_val(bulgular, "mgm_limit_tl")
        }
    }
    return structured_doc


def finansman_semasina_donustur(doc: dict, bulgular: dict) -> dict:
    """
    Finansman koleksiyonu için istenen verileri hazırlar.
    """
    simdi = datetime.now(timezone.utc).isoformat()
    banka_kodu = doc.get("banka_kodu", "genel")
    raw_id = str(doc["_id"])

    return {
        "_id": f"fin_{banka_kodu}_{raw_id}",
        "banka_id": banka_kodu,
        "alt_kategori": _get_val(bulgular, "alt_kategori"),
        "hedef_kitle": _get_val(bulgular, "hedef_kitle", ["tum_musteriler"]),
        "sfinansman_kar_orani": _safe_float(_get_val(bulgular, "finansman_kar_orani")),
        "maks_vade_ay": _safe_int(_get_val(bulgular, "max_vade_ay")),
        "min_finansman_tutari": _safe_float(_get_val(bulgular, "min_fin_tutar")),
        "maks_finansman_tutari": _safe_float(_get_val(bulgular, "max_fin_tutar")),
        "standart_masraf_tutari": _safe_float(_get_val(bulgular, "masraf_tl")),
        "standart_masraf_bilgisi": _get_val(bulgular, "masraf_bilgisi"),
        "durum": "aktif",
        "olusturma_tarihi": simdi
    }


def _kanit_dokumani_hazirla(doc: dict, alan_adi: str, bulgu_obj) -> dict | None:
    """
    AlanBulgusu nesnesinden 'cıkarılan_alanlar' koleksiyonu için kanıt kaydı oluşturur.
    """
    if bulgu_obj is None:
        return None

    if hasattr(bulgu_obj, "deger"):
        norm_deger = bulgu_obj.deger
        ham_değer = getattr(bulgu_obj, "ham_metin", None) or str(norm_deger)
        unit_val = getattr(bulgu_obj, "birim", "metin")
        metot = getattr(bulgu_obj, "yontem", "regex")
        guven_score = getattr(bulgu_obj, "guven", 1.0)
        kanıt_metin = getattr(bulgu_obj, "kanit_metni", "") or doc.get("kampanya_adi", "")
        start_pos = getattr(bulgu_obj, "baslangic_konum", None)
        end_pos = getattr(bulgu_obj, "bitis_konum", None)
    elif isinstance(bulgu_obj, dict):
        norm_deger = bulgu_obj.get("deger")
        ham_değer = bulgu_obj.get("ham_metin", str(norm_deger))
        unit_val = bulgu_obj.get("birim", "metin")
        metot = bulgu_obj.get("yontem", "llm")
        guven_score = bulgu_obj.get("guven", 0.85)
        kanıt_metin = bulgu_obj.get("kanit_metni", "") or doc.get("kampanya_adi", "")
        start_pos = bulgu_obj.get("baslangic_konum")
        end_pos = bulgu_obj.get("bitis_konum")
    else:
        return None

    if norm_deger is None:
        return None

    if metot not in GEÇERLİ_YÖNTEMLER:
        metot = "regex"

    simdi = datetime.now(timezone.utc).isoformat()
    banka_id = doc.get("banka_kodu", "genel")
    raw_campaign_id = str(doc["_id"])
    kampanya_id = f"kamp_{banka_id}_{raw_campaign_id}"

    return {
        "_id": f"field_{raw_campaign_id}_{alan_adi}",
        "kampanya_id": kampanya_id,
        "raw_campaign_id": raw_campaign_id,
        "banka_id": banka_id,
        "alan_adi": alan_adi,
        "ham_değer": ham_değer,
        "norm_deger": norm_deger,
        "unit": unit_val,
        "metod": metot,
        "guven_score": float(guven_score) if guven_score is not None else 0.0,
        "kanıt_metin": kanıt_metin,
        "start_char": start_pos,
        "end_char": end_pos,
        "created_at": simdi
    }


def temiz_verilerden_bilgi_cikar() -> None:
    """
    MongoDB üzerindeki işlenmemiş kampanyaları okur;
    1) islenmis_kampanyalar
    2) finansman
    3) cıkarılan_alanlar
    koleksiyonlarına dönüştürerek kaydeder.
    """
    client = None
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]

        clean_col = db["temiz_kampanyalar"]
        structured_col = db["islenmis_kampanyalar"]
        finansman_col = db["finansman"]
        fields_col = db["cıkarılan_alanlar"]

        sorgu = {"$or": [{"is_extracted": False}, {"is_extracted": {"$exists": False}}]}
        temiz_kampanyalar = list(clean_col.find(sorgu))

        if not temiz_kampanyalar:
            print(" Bilgi çıkarımı yapılacak yeni temiz kampanya bulunamadı.")
            return

        print(f" Toplam {len(temiz_kampanyalar)} kampanya Hedef Şemalara Dönüştürülüyor...")

        islenen_sayisi = 0
        toplam_kanit_sayisi = 0

        for doc in temiz_kampanyalar:
            baslik = doc.get("kampanya_adi", "")
            metin = doc.get("ham_metin", "")

            # 1. Kural + LLM Hibrit Çıkarımı Yap
            cikarim_sonucu = hibrit_cikar(baslik, metin) or {}

            # 2. Altın Kampanya Şemasına Dönüştür ve Kaydet (1. Koleksiyon)
            structured_doc = prepare_for_mongo(semaya_donustur(doc, cikarim_sonucu))
            structured_col.update_one(
                {"_id": structured_doc["_id"]},
                {"$set": structured_doc},
                upsert=True
            )

            # 3. Finansman Şemasına Dönüştür ve Kaydet (2. Koleksiyon)
            finansman_doc = prepare_for_mongo(finansman_semasina_donustur(doc, cikarim_sonucu))
            finansman_col.update_one(
                {"_id": finansman_doc["_id"]},
                {"$set": finansman_doc},
                upsert=True
            )

            # 4. Jüri Kanıt Şemasını (cıkarılan_alanlar) Oluştur ve Kaydet (3. Koleksiyon)
            kanit_islemleri = []
            for alan_adi, bulgu in cikarim_sonucu.items():
                kanit_doc = _kanit_dokumani_hazirla(doc, alan_adi, bulgu)
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
                eklenen_kanit = kanit_sonuc.upserted_count + kanit_sonuc.modified_count
                toplam_kanit_sayisi += eklenen_kanit

            # 5. Kaynak Dokümanda İşlendi İşaretini Güncelle
            clean_col.update_one(
                {"_id": doc["_id"]},
                {"$set": {"is_extracted": True}}
            )

            islenen_sayisi += 1
            print(f"   ✅ [{doc.get('banka_kodu', '').upper()}] Dönüştürüldü: {baslik[:40]}...")

        print(f"\n🎉 İşlem Tamamlandı!")
        print(f"   • {islenen_sayisi} kampanya 'islenmis_kampanyalar' koleksiyonuna kaydedildi.")
        print(f"   • {islenen_sayisi} finansman kaydı 'finansman' koleksiyonuna kaydedildi.")
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