import argparse
import importlib
import inspect
import json
import re
import traceback
from datetime import date, datetime
from pathlib import Path

from backend.db.ham_kampanya_kaydet import get_mongo_db
from backend.nlp.extraction.rule_based import kategori_cikar, tarihleri_cikar
from backend.nlp.preprocessing.cleaner import ATLATICAK_ANAHTARLAR, temizle
from scraper.base_scraper import TabanScraper

# 1. Proje kök dizin kontrolü (Script'in konumuna göre ayarlayın)
PROJE_KOK = Path(__file__).resolve().parent

GEREKSIZ_METIN_PATTERNS = [
    r"Tüm Kampanyalar\s+\d+\s+Kuyum,\s+Optik ve Saat\s+\d+\s+Market ve Gıda\s+\d+\s+E-Ticaret\s+\d+\s+Elektronik ve Telekomünikasyon\s+\d+\s+Yapı Sektörü ve İklimlendirme\s+\d+\s+Akaryakıt\s+\d+\s+Diğer Kampanyalar\s+\d+\s+Eğitim,\s+Kitap ve Kırtasiye\s+\d+\s+Genel Kampanyalar\s+\d+\s+Turizm ve Seyahat\s+\d+\s+Hobi ve Oyuncak\s+\d+\s+Mobilya ve Dekorasyon\s+\d+\s+Beyaz Eşya ve Ev Aletleri\s+\d+\s+Giyim ve Aksesuar\s+Arşiv",
    r"Anasayfa Kart Kampanyaları",
]


def metin_menu_temizle(metin: str) -> str:
    if not metin or not isinstance(metin, str):
        return metin
    for pattern in GEREKSIZ_METIN_PATTERNS:
        metin = re.sub(pattern, "", metin, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", metin).strip()


def json_serilestirici(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)  # Bilinmeyen tipleri hataya düşürmemek için stringe çevir


def spider_sinifini_bul(spider_adi: str) -> type[TabanScraper]:
    modul_yollari = [f"scraper.spiders.{spider_adi}", f"spiders.{spider_adi}"]
    modul = None
    for yol in modul_yollari:
        try:
            modul = importlib.import_module(yol)
            break
        except ModuleNotFoundError:
            continue

    if not modul:
        raise RuntimeError(f"'{spider_adi}' modülü bulunamadı.")

    for _, nesne in inspect.getmembers(modul, inspect.isclass):
        if (
            issubclass(nesne, TabanScraper)
            and nesne is not TabanScraper
            and nesne.__module__ == modul.__name__
        ):
            return nesne

    raise RuntimeError(f"'{spider_adi}' içinde TabanScraper alt sınıfı bulunamadı.")


def ham_verileri_temizle_in_memory(raw_kayitlar: list[dict], spider_adi: str) -> list[dict]:
    if not raw_kayitlar:
        return []

    temiz_kayitlar = []
    print(f"🧹 Toplam {len(raw_kayitlar)} adet ham kampanya verisi işleniyor...")

    for doc in raw_kayitlar:
        clean_doc = doc.copy()
        clean_doc.pop("is_processed", None)

        for anahtar, deger in clean_doc.items():
            if anahtar not in ATLATICAK_ANAHTARLAR and isinstance(deger, str):
                temiz_metin = temizle(deger)
                clean_doc[anahtar] = metin_menu_temizle(temiz_metin)

        tarih_metni = clean_doc.get("tarih_metni", "")
        ham_metin = clean_doc.get("ham_metin", "")
        baslik = clean_doc.get("baslik", "")

        tarih_bulgulari = {}
        if tarih_metni and str(tarih_metni).strip().lower() != "none":
            tarih_bulgulari = tarihleri_cikar(tarih_metni)

        if not tarih_bulgulari.get("baslangic_tarihi") and not tarih_bulgulari.get("bitis_tarihi"):
            tarih_bulgulari = tarihleri_cikar(ham_metin)

        siteden_gelen_kategori = clean_doc.get("kategori")
        if siteden_gelen_kategori and str(siteden_gelen_kategori).strip().lower() not in ["none", "null", ""]:
            clean_doc["kampanya_turu"] = siteden_gelen_kategori
        else:
            tur_bulgusu = kategori_cikar(baslik or "", ham_metin or "")
            clean_doc["kampanya_turu"] = (
                tur_bulgusu.get("tur", "genel")
                if isinstance(tur_bulgusu, dict)
                else getattr(tur_bulgusu, "deger", "genel")
            )

        banka_adi = clean_doc.get("banka_adi")
        if not banka_adi or str(banka_adi).strip() == "":
            banka_adi = spider_adi.replace("_", " ").title()

        label_studio_formatli_kayit = {
            "ham_metin": clean_doc.get("ham_metin", ""),
            "baslik": clean_doc.get("baslik", ""),
            "banka_adi": banka_adi,
            "kategori": clean_doc.get("kampanya_turu", "genel"),
        }

        temiz_kayitlar.append(label_studio_formatli_kayit)

    print(f"✅ {len(temiz_kayitlar)} adet kampanya Label Studio formatına hazırlandı.")
    return temiz_kayitlar


def spider_verilerini_cek(spider_adi: str) -> list[dict]:
    print(f"\n==========================================")
    print(f"🚀 [{spider_adi.upper()}] Spider Çalıştırılıyor...")
    print(f"==========================================")

    try:
        spider_class = spider_sinifini_bul(spider_adi)
        spider = spider_class()
        raw_kayitlar = list(spider.kampanyalari_topla())
        print(f"📊 Çekilen ham kayıt sayısı: {len(raw_kayitlar)}")
        return ham_verileri_temizle_in_memory(raw_kayitlar, spider_adi)
    except NotImplementedError:
        print(f"  ⏭️ '{spider_adi}' spider'ı henüz yazılmadı, atlanıyor.")
        return []
    except Exception as hata:
        print(f"  ❌ HATA ({spider_adi}): {hata.__class__.__name__}: {hata}")
        traceback.print_exc()  # Hatanın tam izini basar
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="FinAgent / Label Studio JSON Veri Aktarıcısı")
    parser.add_argument("spider_adi", nargs="?", help="Çalıştırılacak tek bir bankanın spider adı")
    parser.add_argument("--hepsi", action="store_true", help="MongoDB 'bankalar' koleksiyonundaki tüm bankaları tara")
    args = parser.parse_args()

    cikis_yolu = PROJE_KOK / "backend" / "nlp" / "ner" / "datasets" / "label_studio_veri.json"
    
    # Klasörü oluştur
    cikis_yolu.parent.mkdir(parents=True, exist_ok=True)
    print(f"📁 Hedef Dosya Konumu: {cikis_yolu.absolute()}")

    yeni_kayitlar = []

    if args.hepsi:
        print("🔍 MongoDB 'bankalar' koleksiyonundan aktif bankalar sorgulanıyor...")
        try:
            mongo_client, db = get_mongo_db()
            bankalar_col = db["bankalar"]
            hedefler = list(bankalar_col.find({"aktif": True}))
            mongo_client.close()

            if not hedefler:
                print("⚠️ MongoDB 'bankalar' koleksiyonunda aktif banka bulunamadı!")
                return

            for banka_conf in hedefler:
                spider_adi = banka_conf.get("spider", banka_conf["_id"])
                kayitlar = spider_verilerini_cek(spider_adi)
                yeni_kayitlar.extend(kayitlar)

        except Exception as err:
            print(f"\n❌ MongoDB Bağlantı Hatası: {err}")
            return

    elif args.spider_adi:
        yeni_kayitlar = spider_verilerini_cek(args.spider_adi)
    else:
        parser.error("Lütfen bir spider adı belirtin ya da --hepsi kullanın.")

    if yeni_kayitlar:
        mevcut_kayitlar = []
        if cikis_yolu.exists():
            try:
                with open(cikis_yolu, "r", encoding="utf-8") as f:
                    mevcut_kayitlar = json.load(f)
                    if not isinstance(mevcut_kayitlar, list):
                        mevcut_kayitlar = []
            except Exception as e:
                print(f"⚠️ Mevcut JSON dosyası okunamadı (yeniden oluşturulacak): {e}")
                mevcut_kayitlar = []

        toplam_kayitlar = mevcut_kayitlar + yeni_kayitlar

        try:
            with open(cikis_yolu, "w", encoding="utf-8") as f:
                json.dump(toplam_kayitlar, f, ensure_ascii=False, indent=4, default=json_serilestirici)

            print(f"\n✨ İşlem Başarılı!")
            print(f"   - Eklenen yeni kampanya: {len(yeni_kayitlar)}")
            print(f"   - Dosyadaki toplam kampanya: {len(toplam_kayitlar)}")
            print(f"   - Dosya Yolu: '{cikis_yolu.absolute()}'")
        except Exception as write_err:
            print(f"\n❌ JSON Dosyasına Yazma Hatası: {write_err}")
    else:
        print("\n⚠️ Eklenecek yeni veri bulunamadı. JSON dosyası güncellenmedi.")


if __name__ == "__main__":
    main()