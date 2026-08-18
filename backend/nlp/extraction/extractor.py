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
    kar_payı = _get_val(bulgular, ["k_kar_paylasim_orani", "kar_payi"])
    vade = _get_val(bulgular, ["vade", "vade_ay"])
    finansman_tutari = _get_val(bulgular, ["finansman_tutari", "tutar"])
    masraf = _get_val(bulgular, "masraf")
    odul_tutari = _get_val(bulgular, ["odul_tutari", "odul_tutari_tl"])

    # Kampanya Türü için Çoklu Anahtar Kontrolü
    kampanya_turu = _get_val(bulgular, ["tur", "kampanya_turu", "kampanya_tipi", "kategori"], default="Genel")
    alt_kategori = (
        doc.get("alt_kategori") or 
        doc.get("kategori") or 
        doc.get("sektor") or 
        _get_val(bulgular, ["alt_kategori", "kategori", "sektor"]) or 
        "Genel"
    )
    # Banka ve ID standartlaştırma
    banka_id = doc.get("banka") or doc.get("banka_kodu") or "genel"
    raw_id = str(doc["_id"])
    kampanya_adi = doc.get("baslik") or doc.get("kampanya_adi", "")

    baslangic_tarihi = _get_val(bulgular, "baslangic_tarihi")
    bitis_tarihi = _get_val(bulgular, "bitis_tarihi")
    sure_gun = _get_val(bulgular, "sure_gun") or doc.get("sure_gun")

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
            "hedef_kitle": _get_val(bulgular, "hedef_kitle", ["tum_musteriler"]),
            "kampanya_turu": kampanya_turu,
            "alt_kategori": alt_kategori,
            "metin": doc.get("ham_metin")
        },
        "finansman_detay": {
            "kar_paylasım_orani": _safe_float(kar_payı),
            "vade_ay": _safe_int(vade),
            "finansman_tutari": _safe_float(finansman_tutari),
            "taksit": _safe_float(_get_val(bulgular, "taksit")),
            "tahsis_ucreti": _get_val(bulgular, "tahsis_ucreti"),
            "masraf_bilgi": _get_val(bulgular, "masraf_bilgi", "Tahsis ücreti belirtilmemiştir.")
        },
        "promosyon_detay": {
            "odul_tip": _get_val(bulgular, "odul_tip"),
            "odul_tutari_tl": _safe_float(odul_tutari),
            "odul_metni": _get_val(bulgular, "odul_metni"),
            "nakit_iade_yuzde": _safe_float(_get_val(bulgular, ["cashback_orani", "nakit_iade_yuzde"])),
            "puan_kazanc": _safe_float(_get_val(bulgular, "puan_kazanc")),
            "kazanc_metin": _get_val(bulgular, "kazanc_metin")
        },
        "mgm_detay": {
            "is_mgm": False,
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
    tur = _get_val(bulgular, ["tur", "kampanya_turu", "kampanya_tipi"], default="Diğer")
    
    # Scraper'dan (doc) veya NLP bulgularından alt kategori çekimi
    alt_kategori = doc.get("alt_kategori") or doc.get("kategori") or _get_val(bulgular, ["alt_kategori", "sektor"]) or "Genel"

    return {
        "_id": f"fin_{banka_id}_{raw_id}",
        "banka_id": banka_id,
        "alt_kategori": alt_kategori,
        "urun_adı": urun_adi,
        "tur": tur,
        "max_vade_ay": _safe_int(_get_val(bulgular, ["max_vade_ay", "vade"])),
        "min_vade_ay": _safe_int(_get_val(bulgular, "min_vade_ay")),
        "min_finansman_tutari": _safe_float(_get_val(bulgular, ["min_fin_tutar", "finansman_tutari"])),
        "max_finansman_tutari": _safe_float(_get_val(bulgular, "max_fin_tutar")),
        "standart_masraf_tutari": _safe_float(_get_val(bulgular, ["masraf_tl", "masraf"])),
        "standart_masraf_bilgisi": _get_val(bulgular, ["masraf_bilgisi", "masraf_bilgi"]),
        "durum": "aktif",
        "olusturma_tarihi": simdi,
        "kaynak_url": doc.get("url"),
    }


def _kanit_dokumani_hazirla(doc: dict, alan_adi: str, bulgu_obj) -> dict | None:
    """
    Tek bir AlanBulgusu nesnesini Jüri Kanıt Şemasına (extracted_fields) dönüştürür.
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

    simdi = datetime.now(timezone.utc).isoformat()
    banka_id = doc.get("banka") or doc.get("banka_kodu") or "genel"
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
        "evidence_text": evidence_val,
        "guven_score": float(guven_score) if guven_score is not None else 0.0,
        "start_char": start_pos,
        "end_char": end_pos,
        "created_at": simdi
    }


def temiz_verilerden_bilgi_cikar() -> None:
    
    print(" 🔍 LLM servisi ve model erişilebilirliği kontrol ediliyor...")
    if not _llm_var_mi():
        print(" ❌ HATA: LLM (Ollama/Model) hazır veya erişilebilir değil!")
        print(" ⛔ İşlem iptal edildi. Lütfen LLM servisini başlatıp tekrar deneyin.")
        return

    print(" ✅ LLM hazır! Veritabanı işlemleri başlatılıyor...\n")
    
    client = None
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]

        clean_col = db["ham_kampanyalar"]
        structured_col = db["islenmis_kampanyalar"]
        urun_col = db["urun"]
        fields_col = db["cıkarılan_alanlar"]

        sorgu = {"$or": [{"is_extracted": False}, {"is_extracted": {"$exists": False}}]}
        temiz_kampanyalar = list(clean_col.find(sorgu))

        if not temiz_kampanyalar:
            print(" Bilgi çıkarımı yapılacak yeni temiz kampanya bulunamadı.")
            return

        print(f" Toplam {len(temiz_kampanyalar)} kampanya Hedef Şemalara Dönüştürülüyor...")

        islanan_sayisi = 0
        toplam_kanit_sayisi = 0

        for doc in temiz_kampanyalar:
            baslik = doc.get("baslik") or doc.get("kampanya_adi", "")
            metin = doc.get("ham_metin", "")

            # 1. Kural + LLM Hibrit Çıkarımı Yap
            
            cikarim_sonucu = hibrit_cikar(baslik, metin) or {}

            # 2. Altın Kampanya Şemasına Dönüştür ve Kaydet
            structured_doc = prepare_for_mongo(semaya_donustur(doc, cikarim_sonucu))
            structured_col.update_one(
                {"_id": structured_doc["_id"]},
                {"$set": structured_doc},
                upsert=True
            )

            # 3. Finansman Şemasına Dönüştür ve Kaydet
            urun_doc = prepare_for_mongo(urun_semasina_donustur(doc, cikarim_sonucu))
            urun_col.update_one(
                {"_id": urun_doc["_id"]},
                {"$set": urun_doc},
                upsert=True
            )

            # 4. Jüri Kanıt Şemasını Oluştur ve Kaydet
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

            islanan_sayisi += 1
            banka_adi = doc.get("banka") or doc.get("banka_kodu") or "genel"
            print(f"    ✅ [{banka_adi.upper()}] Dönüştürüldü: {baslik[:40]}...")

        print(f"\n🎉 İşlem Tamamlandı!")
        print(f"   • {islanan_sayisi} kampanya 'islenmis_kampanyalar' koleksiyonuna kaydedildi.")
        print(f"   • {islanan_sayisi} finansman kaydı 'urun' koleksiyonuna kaydedildi.")
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