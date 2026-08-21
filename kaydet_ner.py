import argparse
import importlib
import inspect
from datetime import date, datetime
from pathlib import Path
import json

from backend.nlp.preprocessing.cleaner import ATLATICAK_ANAHTARLAR
from scraper.base_scraper import TabanScraper

# Backend NLP temizleme modülünden gerekli bağımlılıkları yüklüyoruz
from backend.nlp.preprocessing.cleaner import temizle
from backend.nlp.extraction.rule_based import kategori_cikar
from backend.nlp.extraction.rule_based import tarihleri_cikar

# Banka listesini ve aktiflik durumunu okumak için DB bağlantısını dahil ediyoruz
from backend.db.ham_kampanya_kaydet import get_mongo_db

PROJE_KOK = Path(__file__).resolve().parent.parent


def json_serilestirici(obj):
    """Datetime objelerini JSON dosyasına yazılabilir string formatına çevirir."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Tip JSON serileştirilemedi: {type(obj)}")


def spider_sinifini_bul(spider_adi: str) -> type[TabanScraper]:
    """scraper/spiders/<ad>.py veya spiders/<ad>.py içindeki TabanScraper alt sınıfını döndürür."""
    modul_yollari = [
        f"scraper.spiders.{spider_adi}",
        f"spiders.{spider_adi}",
    ]

    modul = None
    for yol in modul_yollari:
        try:
            modul = importlib.import_module(yol)
            break
        except ModuleNotFoundError:
            continue

    if not modul:
        raise RuntimeError(
            f"'{spider_adi}' modülü 'scraper.spiders' veya 'spiders' paketleri altında bulunamadı."
        )

    for _, nesne in inspect.getmembers(modul, inspect.isclass):
        if (
            issubclass(nesne, TabanScraper)
            and nesne is not TabanScraper
            and nesne.__module__ == modul.__name__
        ):
            return nesne

    raise RuntimeError(f"'{spider_adi}' modülünde TabanScraper alt sınıfı bulunamadı.")


def ham_verileri_temizle_in_memory(raw_kayitlar: list[dict], spider_adi: str) -> list[dict]:
    """
    Spider'dan toplanan ham sözlük verilerini hafızada temizler, 
    Label Studio'nun doğrudan okuyabileceği sade formata dönüştürür.
    """
    if not raw_kayitlar:
        return []

    temiz_kayitlar = []
    print(f"🧹 Toplam {len(raw_kayitlar)} adet ham kampanya verisi işleniyor...")

    for doc in raw_kayitlar:
        clean_doc = doc.copy()
        clean_doc.pop("is_processed", None)

        # 1. Doküman içindeki tüm metin alanlarını otomatik temizle
        for anahtar, deger in clean_doc.items():
            if anahtar not in ATLATICAK_ANAHTARLAR and isinstance(deger, str):
                clean_doc[anahtar] = temizle(deger)

        # 2. Öncelikli Tarih Çıkarma Mantığı
        tarih_metni = clean_doc.get("tarih_metni", "")
        ham_metin = clean_doc.get("ham_metin", "")
        baslik = clean_doc.get("baslik", "")

        tarih_bulgulari = {}

        if tarih_metni and str(tarih_metni).strip().lower() != "none":
            tarih_bulgulari = tarihleri_cikar(tarih_metni)

        if not tarih_bulgulari.get("baslangic_tarihi") and not tarih_bulgulari.get("bitis_tarihi"):
            tarih_bulgulari = tarihleri_cikar(ham_metin)

        if "baslangic_tarihi" in tarih_bulgulari:
            clean_doc["baslangic_tarihi"] = tarih_bulgulari["baslangic_tarihi"].deger

        if "bitis_tarihi" in tarih_bulgulari:
            clean_doc["bitis_tarihi"] = tarih_bulgulari["bitis_tarihi"].deger

        if "sure_gun" in tarih_bulgulari:
            clean_doc["sure_gun"] = tarih_bulgulari["sure_gun"].deger
            
        siteden_gelen_kategori = clean_doc.get("kategori")

        if siteden_gelen_kategori and str(siteden_gelen_kategori).strip().lower() not in ["none", "null", ""]:
            clean_doc["kampanya_turu"] = siteden_gelen_kategori
        else:
            tur_bulgusu = kategori_cikar(
                baslik or "",
                ham_metin or "",
            )
            if isinstance(tur_bulgusu, dict):
                clean_doc["kampanya_turu"] = tur_bulgusu.get("tur", "genel")
            else:
                clean_doc["kampanya_turu"] = getattr(tur_bulgusu, "deger", "genel") 

        clean_doc["temizlenme_tarihi"] = datetime.now()
        clean_doc["is_extracted"] = False  

        # Banka adı boş geldiyse spider adından türet
        banka_adi = clean_doc.get("banka_adi")
        if not banka_adi or str(banka_adi).strip() == "":
            banka_adi = spider_adi.replace("_", " ").title()

        # Label Studio için yapı
        label_studio_formatli_kayit = {
            "ham_metin": clean_doc.get("ham_metin", ""),
            "baslik": clean_doc.get("baslik", ""),
            "banka_adi": banka_adi,
            "kategori": clean_doc.get("kampanya_turu", "genel")
        }

        temiz_kayitlar.append(label_studio_formatli_kayit)

    print(f"✅ {len(temiz_kayitlar)} adet kampanya Label Studio formatına hazırlandı.")
    return temiz_kayitlar


def spider_verilerini_cek(spider_adi: str) -> list[dict]:
    """Belirtilen spider'ı çalıştırır ve temizlenmiş kayıtları döndürür."""
    print(f"\n==========================================")
    print(f"🚀 [{spider_adi.upper()}] Spider Çalıştırılıyor...")
    print(f"==========================================")
    
    try:
        spider_class = spider_sinifini_bul(spider_adi)
        spider = spider_class()
        raw_kayitlar = list(spider.kampanyalari_topla())
        return ham_verileri_temizle_in_memory(raw_kayitlar, spider_adi)
    except NotImplementedError:
        print(f"  ⏭️ '{spider_adi}' spider'ı henüz yazılmadı (NotImplementedError), atlanıyor.")
        return []
    except Exception as hata:
        print(f"  ❌ HATA ({spider_adi}): {hata.__class__.__name__}: {hata}")
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="FinAgent / Label Studio JSON Veri Aktarıcısı")
    parser.add_argument("spider_adi", nargs="?", help="Çalıştırılacak tek bir bankanın spider adı (ör. hayat_finans)")
    parser.add_argument("--hepsi", action="store_true", help="MongoDB 'bankalar' koleksiyonundaki aktif tüm bankaları tara")
    parser.add_argument("--cikis", default="label_studio_veri.json", help="Kaydedilecek JSON dosyasının adı")
    args = parser.parse_args()

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
        parser.error("Lütfen bir banka spider adı belirtin (ör. python kaydet.py hayat_finans) ya da --hepsi kullanın.")

    if yeni_kayitlar:
        cikis_yolu = Path(args.cikis)
        
        # Eğer dosya zaten varsa, eski kayıtları oku ve yeni gelenleri üzerine ekle
        mevcut_kayitlar = []
        if cikis_yolu.exists():
            try:
                with open(cikis_yolu, "r", encoding="utf-8") as f:
                    mevcut_kayitlar = json.load(f)
                    if not isinstance(mevcut_kayitlar, list):
                        mevcut_kayitlar = []
            except Exception:
                mevcut_kayitlar = []

        # Eski veriler ile yeni verileri birleştir
        toplam_kayitlar = mevcut_kayitlar + yeni_kayitlar

        # Dosyaya güncel listeyi yaz
        with open(cikis_yolu, "w", encoding="utf-8") as f:
            json.dump(toplam_kayitlar, f, ensure_ascii=False, indent=4, default=json_serilestirici)

        print(f"\n✨ İşlem Başarılı!")
        print(f"   - Eklenen yeni kampanya: {len(yeni_kayitlar)}")
        print(f"   - Dosyadaki toplam kampanya: {len(toplam_kayitlar)}")
        print(f"   - Dosya Yolu: '{cikis_yolu.absolute()}'")
    else:
        print("\n⚠️ Ekenecek yeni veri bulunamadı.")


if __name__ == "__main__":
    main()