import argparse
import importlib
import inspect
import os
from datetime import datetime

import yaml
from pymongo import MongoClient # YENİ: MongoDB kütüphanesi eklendi

from backend.db.database import get_session, init_db
from backend.db.models import Banka, ScrapeLog
from scraper.base_scraper import TabanScraper
from pathlib import Path

PROJE_KOK = Path(__file__).resolve().parent.parent

# --- MONGODB BAĞLANTI AYARLARI ---
# Docker compose dosyasındaki ayarlara uygun olarak bağlanıyoruz
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
# Docker ağında MongoDB servisinin adı 'mongodb' olduğu için o adrese gidiyoruz
# --- ESKİ HALİ ---
# MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@mongodb:27017/"

# --- YENİ HALİ (BUNU YAPIŞTIR) ---
MONGO_URI = "mongodb://admin:admin123@mongodb:27017/?authSource=admin"

# MongoDB Client'ını başlat ve koleksiyonu seç
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["smartdata"]
raw_collection = mongo_db["raw_campaigns"]


def spider_sinifini_bul(spider_adi: str) -> type[TabanScraper]:
    """scraper/spiders/<ad>.py içindeki TabanScraper alt sınıfını döndürür."""
    modul = importlib.import_module(f"scraper.spiders.{spider_adi}")
    for _, nesne in inspect.getmembers(modul, inspect.isclass):
        if (issubclass(nesne, TabanScraper)
                and nesne.__module__ == modul.__name__):
            return nesne
    raise RuntimeError(f"{spider_adi} modülünde TabanScraper alt sınıfı yok")


def bankayi_calistir(banka_conf: dict) -> None:
    """Tek bankanın spider'ını çalıştırır ve sonucu MongoDB'ye aktarır."""
    kod = banka_conf["id"]
    print(f"\n=== {banka_conf['kisa_ad']} ({kod}) ===")

    with get_session() as session:
        banka = session.query(Banka).filter_by(kod=kod).first()
        if banka is None:
            print("  Banka veritabanında yok — önce 'python -m backend.db.seed' çalıştırın")
            return

        log = ScrapeLog(banka_id=banka.id, durum="hata", kampanya_sayisi=0)
        try:
            spider = spider_sinifini_bul(banka_conf["spider"])()
            kayitlar = list(spider.kampanyalari_topla())
            
            # Eski JSON kaydetme metodunu istersen yedek amaçlı tutabilirsin
            # veya tamamen kaldırabilirsin. Şimdilik koruyoruz:
            spider.kaydet(kayitlar)

            # --- YENİ: MONGODB'YE VERİ AKTARIMI ---
            if kayitlar:
                eklenen_guncellenen = 0
                for kayit in kayitlar:
                    # Kayda metadata (üst veri) ekliyoruz
                    kayit["banka_kodu"] = kod
                    kayit["cekilis_tarihi"] = datetime.utcnow()
                    kayit["is_processed"] = False # NLP Pipeline'ı için bayrak
                    
                    # Upsert (Update or Insert) Mantığı:
                    # Eğer bu URL veritabanında varsa üzerine yazar, yoksa yeni kayıt açar.
                    raw_collection.update_one(
                        {"url": kayit.get("url")}, 
                        {"$set": kayit}, 
                        upsert=True
                    )
                    eklenen_guncellenen += 1
                
                print(f"  MongoDB'ye {eklenen_guncellenen} adet kayıt başarıyla aktarıldı/güncellendi.")

            log.durum = "basarili" if kayitlar else "kismi"
            log.kampanya_sayisi = len(kayitlar)
            log.hata_mesaji = None
        except NotImplementedError:
            log.hata_mesaji = "spider henüz yazılmadı"
            print("  Spider henüz yazılmadı, atlanıyor")
        except Exception as hata:
            log.hata_mesaji = f"{hata.__class__.__name__}: {hata}"
            print(f"  HATA: {log.hata_mesaji}")

        session.add(log)
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="FinAgent veri toplama çalıştırıcısı")
    parser.add_argument("banka", nargs="?", help="banks.yaml'daki banka id'si")
    parser.add_argument("--hepsi", action="store_true", help="aktif tüm bankaları çek")
    args = parser.parse_args()

    init_db()

    with open(PROJE_KOK / "backend" / "configs" / "banks.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if args.hepsi:
        hedefler = [b for b in config["bankalar"] if b["aktif"]]
    elif args.banka:
        hedefler = [b for b in config["bankalar"] if b["id"] == args.banka]
        if not hedefler:
            parser.error(f"'{args.banka}' banks.yaml'da yok. Geçerli id'ler: "
                         + ", ".join(b["id"] for b in config["bankalar"]))
    else:
        parser.error("Banka id'si verin ya da --hepsi kullanın")

    for banka_conf in hedefler:
        bankayi_calistir(banka_conf)


if __name__ == "__main__":
    main()