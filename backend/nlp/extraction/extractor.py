import os
import re
from datetime import date, datetime, timezone
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError

# 🛠️ ÇİFT YOL: bu modül iki farklı kökten çalıştırılıyor — pipeline.py depo
# kökünden `backend.*` diye, backend konteyneri ise WORKDIR /app (yani
# backend/) içinden `nlp.*` diye import ediyor. Tek biçim kullanmak,
# diğerinde ModuleNotFoundError veriyor ve bu yüzden geçici bir symlink
# gerekiyordu. agents.py'deki yerleşik kalıp buraya da uygulandı.
try:
    from backend.db.banka_istatistikleri import banka_istatistiklerini_guncelle
except ModuleNotFoundError:
    from db.banka_istatistikleri import banka_istatistiklerini_guncelle


# Göreceli Import
from .hybrid import hibrit_cikar, _llm_var_mi


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

# Kampanya tarihleri için makul yıl penceresi; dışındaki değer kampanya
# gerçeği değil, tarama/ayrıştırma artefaktıdır (ör. "31.07.2076").
_YIL_ALT, _YIL_UST = 12, 8


def _yil_makul_mu(dt) -> bool:
    if dt is None:
        return False
    bu_yil = date.today().year
    return (bu_yil - _YIL_ALT) <= dt.year <= (bu_yil + _YIL_UST)


def _tarih_metni_ayristir(tarih_str):
    """'01.08.2026 - 31.08.2026' benzeri metinleri (başlangıç, bitiş) döner.

    ⚠️ Önceki sürüm YALNIZCA tam olarak "DD.MM.YYYY - DD.MM.YYYY" biçimini
    tanıyordu ve başka her şeyde (None, None) dönüyordu. `semaya_donustur`
    bu durumda ham belgenin ÖNCEDEN HESAPLANMIŞ tarihlerine düşüyor, onlar
    da hatalı olabildiği için hatalar sessizce depoya geçiyordu:
        "31 Ağustos 2026"                 -> tek tarih, tanınmıyordu
        "05 Aralık - 15 Ocak 2025"        -> yıl aşan aralık, iki tarihe de
                                             2025 verilip bitiş < başlangıç
    Artık sözel aylar (`tarih_normalize`) da tanınıyor, tek tarih BİTİŞ
    kabul ediliyor ve yıl aşan aralıkta başlangıç bir yıl geri alınıyor.
    """
    if not tarih_str or not isinstance(tarih_str, str):
        return None, None

    from ..normalizasyon.date import tarih_normalize

    def _coz(parca: str):
        """Bir parçayı datetime'a çevirir; sayısal ve sözel biçimleri kapsar."""
        parca = parca.strip()
        # `%d-%m-%Y` EKLENDİ: Ziraat Katılım tarihleri tireli yazıyor
        # ("10-07-2025"). Bu kalıp yokken tüm Ziraat kayıtlarında bitiş
        # tarihi boş kalıyordu (139 boş kaydın büyük çoğunluğu).
        for kalip in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(parca, kalip)
            except ValueError:
                pass
        d = tarih_normalize(parca)
        return datetime.combine(d, datetime.min.time()) if d else None

    ham = tarih_str.strip()

    # ⚠️ AYRAÇ BELİRSİZLİĞİ.
    # "08-08-2026 - 07-09-2026" ifadesinde tire HEM tarihin içindeki ayraç
    # HEM de aralık işareti. Koşulsuz `[-–—]` ile bölmek altı parça üretiyor
    # ve hiçbiri tarih olmuyordu. Türkçe metinlerde aralık işareti neredeyse
    # her zaman BOŞLUKLA yazılıyor; önce boşluklu ayraç deneniyor, yalnızca
    # o işe yaramazsa çıplak tireye düşülüyor.
    parcalar = re.split(r"\s+[-–—]\s+", ham)
    if len(parcalar) == 1:
        parcalar = re.split(r"\s*[–—]\s*", ham)
    if len(parcalar) == 1:
        parcalar = re.split(r"\s*-\s*", ham)

    if len(parcalar) == 2:
        ilk, ikinci = parcalar[0], parcalar[1]
        bitis = _coz(ikinci)

        # "05 Aralık - 15 Ocak 2025": yıl yalnızca İKİNCİ parçada yazılıdır;
        # ilk parça o yıl olmadan hiç ayrıştırılamıyordu. Yılı ödünç alıp
        # ayrıştırıyor, sonra sıralama bozuksa başlangıcı bir yıl geri
        # alıyoruz — "5 Aralık 2024 – 15 Ocak 2025" doğru okumadır.
        yil_ilkte = re.search(r"\d{4}", ilk)
        if re.fullmatch(r"\d{1,2}", ilk.strip()) and bitis is not None:
            # "22 - 30 Nisan 2026": ilk parça YALNIZCA GÜN. Ay ve yıl ikinci
            # parçada yazılı; ikisini de ödünç alıyoruz. Önceden yalnızca yıl
            # ödünç alınıyordu, ay eksik kaldığı için parça çözülemiyordu.
            try:
                baslangic = bitis.replace(day=int(ilk.strip()))
            except ValueError:      # ör. 31 - 30 Nisan
                baslangic = None
        elif not yil_ilkte and bitis is not None:
            baslangic = _coz("%s %d" % (ilk, bitis.year))
        else:
            baslangic = _coz(ilk)

        if baslangic and bitis and baslangic > bitis and not yil_ilkte:
            try:
                baslangic = baslangic.replace(year=baslangic.year - 1)
            except ValueError:      # 29 Şubat
                baslangic = None

        bas_ok, bit_ok = _yil_makul_mu(baslangic), _yil_makul_mu(bitis)
        if bas_ok and bit_ok and baslangic <= bitis:
            return baslangic, bitis

        # Aralığın bir tarafı bozuksa (ör. "1.07.2026 - 31.07.2076") sağlam
        # olan taraf korunur; uydurma yapılmaz.
        return (baslangic if bas_ok else None, bitis if bit_ok else None)

    if len(parcalar) == 1:
        # Tek tarih kampanyanın SON günüdür ("31 Ağustos 2026'ya kadar").
        tek = _coz(parcalar[0])
        return (None, tek) if _yil_makul_mu(tek) else (None, None)

    return None, None


def _tarihleri_dogrula(baslangic, bitis, sure_gun):
    """Şemaya yazılmadan ÖNCEKİ son denetim.

    Tarihler üç ayrı kaynaktan gelebiliyor (tarih_metni, ham belgenin hazır
    alanları, NLP çıkarımı) ve `sure_gun` bunlardan BAĞIMSIZ olarak seçiliyor.
    Hiçbir yerde tutarlılık kontrolü yoktu; sonuç: bitişten sonra başlayan 10
    kayıt, tarihleriyle uyuşmayan 15 `sure_gun`, sıfır süreli 6 kayıt.
    Kaynak ne olursa olsun burada tek bir kez doğrulanıyor.
    """
    b = baslangic if isinstance(baslangic, datetime) else None
    s = bitis if isinstance(bitis, datetime) else None

    if b is not None and not _yil_makul_mu(b):
        b, baslangic = None, None
    if s is not None and not _yil_makul_mu(s):
        s, bitis = None, None

    # Bitiş başlangıçtan önceyse başlangıç güvenilmezdir. Bitiş kampanyanın
    # geçerliliğini belirleyen alan olduğu için o korunur, başlangıç düşer.
    if b is not None and s is not None and s < b:
        baslangic = None
        b = None

    # sure_gun DAİMA nihai tarihlerden türetilir. Bir tarih düşürüldüyse
    # devralınan süre o düşürülen tarihten hesaplanmıştır ve artık geçersizdir
    # (ör. bitiş 2076 atılınca sure_gun 18293 kalıyordu; uydurma başlangıç
    # atılınca max(0,...) kırpmasından gelen 0 kalıyordu). Böyle durumda
    # süreyi taşımak yerine boş bırakmak doğru.
    if b is not None and s is not None:
        sure_gun = (s - b).days
    elif baslangic is None or bitis is None:
        sure_gun = None

    return baslangic, bitis, sure_gun


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
    # ⚠️ `max_finansman_tutari` EKLENDİ.
    # Türkçe kampanya metinlerinde tutar en sık "X TL'ye KADAR / X TL'ye VARAN"
    # diye yazılır. Kural tabanlı çıkarıcı "kadar/varan" gördüğünde değeri
    # `max_finansman_tutari` alanına koyuyor, şema ise yalnızca
    # `finansman_tutari` / `tutar` anahtarlarını okuyordu — yani "250 Bin TL'ye
    # kadar konut finansmanı" kampanyasının tutarı sessizce KAYBOLUYORDU.
    # İlan edilen tavan, kampanyanın tutarıdır; sıralama bilinçli: önce kesin
    # tutar, yoksa ilan edilen tavan.
    finansman_tutari = _get_val(
        bulgular, ["finansman_tutari", "tutar", "max_finansman_tutari"]
    )
    masraf = _get_val(bulgular, "masraf")
    odul_tutari_tl = _get_val(bulgular, ["odul_tutari", "odul_tutari_tl"])

    # Kampanya Türü için Çoklu Anahtar Kontrolü
    # Hiçbir kural tutmazsa alan `None` kalıyordu (38 kayıt); oysa
    # configs/taxonomy.yaml bu durum için `belirtilmemis` etiketini tanımlıyor
    # ("Etiketi olmayan/boş kayıtlar için") ve arayüzde tr/en karşılığı hazır.
    # Etiket tanımlıydı ama hiçbir yer yazmıyordu; null yerine onu yazmak hem
    # gruplamayı hem arayüzü tutarlı kılıyor.
    kampanya_turu = _get_val(bulgular, "kampanya_turu") or "belirtilmemis"
    sektor = (
        doc.get("sektor") or
        doc.get("sektor") or 
        _get_val(bulgular, ["kategori", "sektor"]) or 
        "Genel"
    )
    # Banka ve ID standartlaştırma
    banka_id = doc.get("banka") or doc.get("banka_kodu") or "genel"
    raw_id = str(doc["_id"])
    kampanya_adi = doc.get("baslik") or doc.get("kampanya_adi", "")


    tarih_metni = doc.get("tarih_metni") or _get_val(bulgular, "tarih_metni")
    tm_baslangic, tm_bitis = _tarih_metni_ayristir(tarih_metni)

    if tm_baslangic and tm_bitis:
        baslangic_tarihi = tm_baslangic
        bitis_tarihi = tm_bitis
    else:
        # 2. Öncelik: tarih_metni yoksa veya ayrıştırılamadıysa
        # Ham doc içindeki ISODate tarihlerine veya bulgulardan gelen tarihlere bakılır
        baslangic_tarihi = doc.get("baslangic_tarihi") or _get_val(bulgular, "baslangic_tarihi")
        bitis_tarihi = doc.get("bitis_tarihi") or _get_val(bulgular, "bitis_tarihi")
        # tarih_metni yalnızca bitişi verebildiyse (tek tarih ya da bozuk
        # aralık) onu ham belgenin hazır alanına TERCİH et: metinden okunan
        # tarih, tarayıcının önceden hesapladığından daha güvenilir.
        if tm_bitis:
            bitis_tarihi = tm_bitis
    sure_gun = _get_val(bulgular, "sure_gun") or doc.get("sure_gun")

    baslangic_tarihi, bitis_tarihi, sure_gun = _tarihleri_dogrula(
        baslangic_tarihi, bitis_tarihi, sure_gun
    )
    
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
            "sektor": sektor,
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
            "mgm_limit_kisi": _get_val(bulgular, "mgm_limit_kisi")
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

        # 2. FİNANSMAN ÜRÜNLERİ
        print()
        urun_sayisi, urun_kanit_sayisi = _urunleri_isle(db)

        # 3. BANKA İSTATİSTİKLERİ (baskın kampanya türü / kategori)
        print()
        guncellenen_banka_sayisi = banka_istatistiklerini_guncelle(db)   # <-- burada, aynı db ile

        toplam_kanit_sayisi = kampanya_kanit_sayisi + urun_kanit_sayisi

        print(f"\n🎉 İşlem Tamamlandı!")
        print(f"   • {kampanya_sayisi} kampanya 'islenmis_kampanyalar' koleksiyonuna kaydedildi.")
        print(f"   • {urun_sayisi} ürün 'islenmis_urunler' koleksiyonuna kaydedildi (spider kaynaklı).")
        print(f"   • {toplam_kanit_sayisi} alan kanıtı 'cıkarılan_alanlar' koleksiyonuna kaydedildi.")
        print(f"   • {guncellenen_banka_sayisi} banka istatistiği güncellendi.")

    except PyMongoError as err:
        print(f"❌ MongoDB Hata: {err}")
    except Exception as err:
        print(f"❌ Dönüştürme Hatası: {err}")
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    temiz_verilerden_bilgi_cikar()
