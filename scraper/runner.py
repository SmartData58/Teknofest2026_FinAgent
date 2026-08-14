import argparse
import importlib
import inspect
from datetime import datetime, timezone
from pathlib import Path

from pymongo.errors import PyMongoError

# Yeni oluşturduğumuz modülden fonksiyonları ve veritabanı bağlantısını içe aktarıyoruz
from backend.db.ham_kampanya_kaydet import get_mongo_db, ham_kampanyalari_kaydet
from scraper.base_scraper import TabanScraper

PROJE_KOK = Path(__file__).resolve().parent.parent


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


def bankayi_calistir(banka_conf: dict, db) -> None:
    """Tek bankanın spider'ını çalıştırır ve verileri DB kaydı için ham_kampanya_kaydet modülüne iletir."""
    kod = banka_conf["id"]
    kisa_ad = banka_conf.get("kisa_ad", kod)
    spider_adi = banka_conf.get("spider", kod)

    mulkiyet_turu = banka_conf.get("mulkiyet_turu", "özel")
    buyukluk_kategorisi = banka_conf.get("buyukluk_kategorisi", "belirtilmedi")

    print(f"\n==========================================")
    print(f"🚀 [{kod.upper()}] {kisa_ad} Tarama Başlatılıyor...")
    print(f"==========================================")

    baslangic_zamani = datetime.now(timezone.utc)

    try:
        spider_class = spider_sinifini_bul(spider_adi)
        spider = spider_class()

        # Spider'dan gelen ham verileri topluyoruz
        raw_kayitlar = list(spider.kampanyalari_topla())

        # Kaydetme işlemini DB modülüne devrediyoruz
        ham_kampanyalari_kaydet(
            banka_conf=banka_conf,
            raw_kayitlar=raw_kayitlar,
            baslangic_zamani=baslangic_zamani,
            db=db,
        )

    except NotImplementedError:
        print("  ⏭️ Spider henüz yazılmadı (NotImplementedError), atlanıyor.")
    except Exception as hata:
        hata_str = f"{hata.__class__.__name__}: {hata}"
        print(f"   HATA: {hata_str}")


def main() -> None:
    parser = argparse.ArgumentParser(description="FinAgent / SmartData Veri Toplama Çalıştırıcısı")
    parser.add_argument("banka", nargs="?", help="MongoDB 'bankalar' koleksiyonundaki banka id'si (ör. albaraka)")
    parser.add_argument("--hepsi", action="store_true", help="Aktif tüm bankaları sırayla çek")
    args = parser.parse_args()

    mongo_client = None
    try:
        mongo_client, db = get_mongo_db()
        bankalar_col = db["bankalar"]

        if args.hepsi:
            hedefler = list(bankalar_col.find({"aktif": True}))
            if not hedefler:
                print("⚠️ MongoDB 'bankalar' koleksiyonunda aktif banka bulunamadı!")
                return
        elif args.banka:
            hedefler = list(bankalar_col.find({"id": args.banka}))
            if not hedefler:
                tum_bankalar = [b["id"] for b in bankalar_col.find({}, {"id": 1})]
                gecerli_idler = ", ".join(tum_bankalar) if tum_bankalar else "Hiç banka kayıtlı değil"
                parser.error(
                    f"'{args.banka}' MongoDB 'bankalar' koleksiyonunda bulunamadı. Geçerli id'ler: {gecerli_idler}"
                )
        else:
            parser.error("Lütfen bir banka id'si belirtin (ör. python runner.py albaraka) ya da --hepsi kullanın.")

        for banka_conf in hedefler:
            bankayi_calistir(banka_conf, db)

    except PyMongoError as err:
        print(f"\n❌ MongoDB Bağlantı/Yazma Hatası: {err}")
    finally:
        if mongo_client:
            mongo_client.close()


if __name__ == "__main__":
    main()