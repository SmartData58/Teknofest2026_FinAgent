import os
from datetime import datetime, timezone
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


def _get_val(bulgular: dict, key: str, default=None):
    """
    AlanBulgusu nesnesinden veya dict yapısından ham değeri (deger) güvenli şekilde çeker.
    """
    if key not in bulgular or bulgular[key] is None:
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
    simdi = datetime.now(timezone.utc).isoformat()
    
    # --- 1. ÇIKARILAN HAM DEĞERLERİ AL ---
    kar_orani = _get_val(bulgular, "kar_orani") or _get_val(bulgular, "faiz_orani")
    taksit = _get_val(bulgular, "taksit_sayisi") or _get_val(bulgular, "vade")
    finansman_tutari = _get_val(bulgular, "finansman_tutari") or _get_val(bulgular, "maks_tutar")
    
    odul_tutari = _get_val(bulgular, "odul_tutari") or _get_val(bulgular, "nakit_iade")
    indirim_orani = _get_val(bulgular, "indirim_orani")
    puan_tutari = _get_val(bulgular, "puan_tutari")
    min_harcama = _get_val(bulgular, "minimum_harcama")

    baslik = doc.get("baslik", "")
    metin = doc.get("detay") or doc.get("icerik") or doc.get("metin") or ""

    # --- 2. HEDEF TÜRKÇE DOKÜMAN YAPISI ---
    structured_doc = {
        # Unique Kampanya Kimliği (Örn: camp_albaraka_60c72b2f9b1e)
        "_id": f"camp_{doc.get('banka_kodu', 'genel')}_{doc['_id']}",
        
        # Temizlenmiş verinin MongoDB ID'si
        "temizlenmis_kampanya_id": str(doc["_id"]),
        
        # Bankanın Sistem Kodu (Örn: 'albaraka', 'garanti')
        "banka_kodu": doc.get("banka_kodu"),
        
        # Bankanın Resmi/Görünür Adı (Örn: 'Albaraka Türk', 'Garanti BBVA')
        "banka_adi": doc.get("banka_adi", doc.get("banka_kodu", "").upper()),
        
        # Kampanyanın Başlığı
        "baslik": baslik,
        
        # Kampanyanın Orijinal Web Adresi (URL)
        "kaynak_url": doc.get("url"),
        
        # Kampanyanın Metin İçeriği / Detayı
        "temiz_metin": metin,
        
        # 🏷️ KATEGORİZASYON VE DURUM
        # Kampanyanın Ana Kategorisi (Örn: 'Finansman', 'Kredi Kartı', 'Mevduat/Katılma')
        "ana_kategori": _get_val(bulgular, "ana_kategori", "genel"),
        
        # Kampanyanın Alt Kategorisi (Örn: 'Otomotiv', 'Gıda/Restoran', 'Eğitim')
        "alt_kategori": _get_val(bulgular, "alt_kategori", "diğer"),
        
        # Kampanyanın Sunduğu Ana Özellik Türü (Örn: 'Taksit', 'Puan/Ödül', 'İndirim')
        "ozellik_turu": _get_val(bulgular, "ozellik_turu"),
        
        # Kampanyanın Yayında Olma Durumu ('aktif', 'pasif', 'suresi_doldu')
        "kampanya_durumu": "aktif",
        
        # 📅 TARİH VE SÜRE BİLGİLERİ
        # Kampanya Başlangıç Tarihi (ISO Formatında String / Date)
        "baslangic_tarihi": doc.get("baslangic_tarihi"),
        
        # Kampanya Bitiş Tarihi (ISO Formatında String / Date)
        "bitis_tarihi": doc.get("bitis_tarihi"),
        
        # Kampanyanın Toplam Süresi (Gün cinsinden Sayı)
        "sure_gun_sayisi": doc.get("sure_gun"),
        
        # Kampanyadan Yararlanabilecek Kitle (Örn: ['yeni_musteriler', 'emekliler'])
        "hedef_kitle": _get_val(bulgular, "hedef_kitle", ["tum_musteriler"]),
        
        # 🟢 FİNANSMAN / KREDİ BİLGİLERİ
        "finansman_detayi": {
            # Kar / Faiz Oranı (Yüzde cinsinden float, Örn: 1.99)
            "kar_orani_yuzde": float(kar_orani) if kar_orani is not None else None,
            
            # Hesaplanan veya Belirtilen Kar / Faiz Tutarı (TL)
            "kar_tutari_tl": _get_val(bulgular, "kar_tutari_tl"),
            
            # Sunulan Maksimum Vade / Taksit Sayısı (Ay cinsinden tamsayı)
            "maks_vade_ay": int(taksit) if taksit is not None else None,
            
            # Çekilebilecek Maksimum Finansman / Kredi Tutarı (TL)
            "maks_finansman_tutari_tl": float(finansman_tutari) if finansman_tutari is not None else None,
            
            # Dosya / Tahsis Ücreti Tutarı (TL)
            "tahsis_ucreti_tl": _get_val(bulgular, "tahsis_ucreti"),
            
            # Masraflar ve Ücretler Hakkında Ek Açıklama Metni
            "masraf_aciklamasi": _get_val(bulgular, "masraf_bilgisi", "Tahsis ücreti belirtilmemiştir."),
            
            # Vade Farksız / Kar Oransız Finansman mı? (True/False)
            "sifir_kar_orani_mi": kar_orani == 0 or _get_val(bulgular, "vade_farksiz", False)
        },
        
        # 🎁 ÖDÜL, PROMOSYON VE KAZANÇ BİLGİLERİ
        "promosyon_detayi": {
            # Kazanılacak Nakit / Ödül Tutarı (TL)
            "odul_tutari_tl": float(odul_tutari) if odul_tutari is not None else None,
            
            # Ödül Tutarı Aralığı (Örn: '100 TL - 500 TL arası')
            "odul_araligi_metni": _get_val(bulgular, "odul_araligi"),
            
            # Cash-Back / Nakit İade Yüzdesi (Float)
            "nakit_iade_orani_yuzde": float(_get_val(bulgular, "cashback_orani")) if _get_val(bulgular, "cashback_orani") else None,
            
            # Uygulanan İndirim Yüzdesi (Float, Örn: 20.0)
            "indirim_orani_yuzde": float(indirim_orani) if indirim_orani is not None else None,
            
            # Kazanılacak Puan / Chip-Para / Worldpuan Miktarı (Float)
            "puan_kazanci": float(puan_tutari) if puan_tutari is not None else None,
            
            # Ödüle Hak Kazanmak İçin Gereken Minimum Harcama Tutarı (TL)
            "minimum_harcama_tutari_tl": float(min_harcama) if min_harcama is not None else None,
            
            # Müşteri Başına Kazanılabilecek Azami Ödül Tutarı (TL)
            "musteri_basi_maks_odul_tl": _get_val(bulgular, "musteri_basi_odul"),
            
            # Kampanya Kapsamında Dağıtılacak Toplam Ödül Bütçesi (TL)
            "toplam_kampanya_odul_butcesi_tl": _get_val(bulgular, "maks_toplam_odul")
        },
        
        # 🚩 HIZLI ARAMA VE FİLTRELEME İŞARETLERİ (Boolean Flags)
        "isaretler": {
            # Arkadaşını Getir (Member Get Member) Kampanyası mı?
            "mgm_kampanyasi_mi": _get_val(bulgular, "is_mgm", False),
            
            # Puan / Worldpuan / Chip-Para Kazandırıyor mu?
            "puan_kazandiriyor_mu": puan_tutari is not None,
            
            # Doğrudan Fiyat/Sipariş İndirimi Var mı?
            "indirim_var_mi": indirim_orani is not None,
            
            # Taksit İmkanı Var mı?
            "taksit_var_mi": taksit is not None and taksit > 1,
            
            # Taksit Erteleme Fırsatı Var mı?
            "taksit_erteleme_var_mi": _get_val(bulgular, "taksit_erteleme", False),
            
            # Kar/Faiz Oranı İçeriyor mu?
            "kar_orani_iceriyor_mu": kar_orani is not None,
            
            # Herhangi Bir Ödül/Kazanım İçeriyor mu?
            "odul_iceriyor_mu": odul_tutari is not None or puan_tutari is not None
        },
        
        # 🤖 YAPAY ZEKA VE SİSTEM MİMARİSİ METAVERİLERİ
        "nlp_metaverileri": {
            # Kullanılan Algoritma/Model Sürümü
            "islem_hattı_surumu": "v1.0",
            
            # Bilgi Çıkarım Metodu ('hybrid_rule_llm', 'rule_based', 'llm_only')
            "siniflandirma_metodu": "hybrid_rule_llm",
            
            # Çıkarımın Tahmini Doğruluk/Güven Skoru (0.00 - 1.00 arası)
            "guven_skoru": 0.90 if kar_orani or odul_tutari else 0.70
        },
        
        # Kaydın Veritabanına İlk Eklendiği Tarih
        "olusturulma_tarihi": simdi,
        
        # Kaydın Veritabanında Son Güncellendiği Tarih
        "guncellenme_tarihi": simdi
    }
    
    return structured_doc


def _kanit_dokumani_hazirla(doc: dict, alan_adi: str, bulgu_obj) -> dict | None:
    """
    AlanBulgusu nesnesinden 'extracted_fields' koleksiyonu için kanıt kaydı oluşturur.
    """
    if bulgu_obj is None:
        return None

    if hasattr(bulgu_obj, "deger"):
        norm_val = bulgu_obj.deger
        raw_val = getattr(bulgu_obj, "ham_metin", None) or str(norm_val)
        unit_val = getattr(bulgu_obj, "birim", "metin")
        method_val = getattr(bulgu_obj, "yontem", "regex")
        conf_val = getattr(bulgu_obj, "guven", 1.0)
        evidence_val = getattr(bulgu_obj, "kanit_metni", "") or doc.get("baslik", "")
        start_pos = getattr(bulgu_obj, "baslangic_konum", None)
        end_pos = getattr(bulgu_obj, "bitis_konum", None)
    elif isinstance(bulgu_obj, dict):
        norm_val = bulgu_obj.get("deger")
        raw_val = bulgu_obj.get("ham_metin", str(norm_val))
        unit_val = bulgu_obj.get("birim", "metin")
        method_val = bulgu_obj.get("yontem", "llm")
        conf_val = bulgu_obj.get("guven", 0.85)
        evidence_val = bulgu_obj.get("kanit_metni", "")
        start_pos = bulgu_obj.get("baslangic_konum")
        end_pos = bulgu_obj.get("bitis_konum")
    else:
        return None

    if norm_val is None:
        return None

    if method_val not in GEÇERLİ_YÖNTEMLER:
        method_val = "regex"

    simdi = datetime.now(timezone.utc).isoformat()
    bank_id = doc.get("banka_kodu", "genel")
    campaign_id = f"camp_{bank_id}_{doc['_id']}"
    raw_campaign_id = str(doc["_id"])

    return {
        "_id": f"field_{doc['_id']}_{alan_adi}",
        "campaign_id": campaign_id,
        "raw_campaign_id": raw_campaign_id,
        "bank_id": bank_id,
        "field_name": alan_adi,
        "raw_value": raw_val,
        "normalized_value": norm_val,
        "unit": unit_val,
        "method": method_val,
        "confidence_score": float(conf_val),
        "evidence_text": evidence_val,
        "start_char": start_pos,
        "end_char": end_pos,
        "created_at": simdi
    }


def temiz_verilerden_bilgi_cikar() -> None:
    """
    MongoDB üzerindeki işlenmemiş kampanyaları okur; Altın Şemaya (structured_campaigns)
    ve Jüri Kanıt Şemasına (extracted_fields) dönüştürerek kaydeder.
    """
    client = None
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]

        clean_col = db["processed_campaigns"]
        structured_col = db["structured_campaigns"]
        fields_col = db["extracted_fields"]

        sorgu = {"$or": [{"is_extracted": False}, {"is_extracted": {"$exists": False}}]}
        temiz_kampanyalar = list(clean_col.find(sorgu))

        if not temiz_kampanyalar:
            print("ℹ️ Bilgi çıkarımı yapılacak yeni temiz kampanya bulunamadı.")
            return

        print(f"🤖 Toplam {len(temiz_kampanyalar)} kampanya Hedef Şemaya Dönüştürülüyor...")

        islenen_sayisi = 0
        toplam_kanit_sayisi = 0

        for doc in temiz_kampanyalar:
            baslik = doc.get("baslik", "")
            metin = doc.get("detay") or doc.get("icerik") or doc.get("metin") or ""

            # 1. Kural + LLM Hibrit Çıkarımı Yap
            cikarim_sonucu = hibrit_cikar(baslik, metin)

            # 2. Altın Şemaya Dönüştür
            structured_doc = semaya_donustur(doc, cikarim_sonucu)

            # 3. 'structured_campaigns' Koleksiyonuna Yaz
            structured_col.update_one(
                {"_id": structured_doc["_id"]},
                {"$set": structured_doc},
                upsert=True
            )

            # 4. Jüri Kanıt Şemasını (extracted_fields) Oluştur ve Kaydet
            kanit_islemleri = []
            for alan_adi, bulgu in cikarim_sonucu.items():
                kanit_doc = _kanit_dokumani_hazirla(doc, alan_adi, bulgu)
                if kanit_doc:
                    kanit_islemleri.append(
                        UpdateOne({"_id": kanit_doc["_id"]}, {"$set": kanit_doc}, upsert=True)
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
        print(f"   • {islenen_sayisi} kampanya 'structured_campaigns' koleksiyonuna kaydedildi.")
        print(f"   • {toplam_kanit_sayisi} alan kanıtı 'extracted_fields' koleksiyonuna kaydedildi.")

    except PyMongoError as err:
        print(f"❌ MongoDB Hata: {err}")
    except Exception as err:
        print(f"❌ Dönüştürme Hatası: {err}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    temiz_verilerden_bilgi_cikar()