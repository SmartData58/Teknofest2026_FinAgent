import argparse
import importlib
import inspect

import yaml

from backend.db.database import PROJE_KOK, get_session, init_db
from backend.db.models import Banka, ScrapeLog
from scraper.base_scraper import TabanScraper


def spider_sinifini_bul(spider_adi: str) -> type[TabanScraper]:
    """scraper/spiders/<ad>.py içindeki TabanScraper alt sınıfını döndürür."""
    modul = importlib.import_module(f"scraper.spiders.{spider_adi}")
    # inspect.getmembers: modüldeki tüm isimleri (sınıf, fonksiyon...) listeler.
    # TabanScraper'dan türeyen ve BU MODÜLDE TANIMLANMIŞ sınıfı arıyoruz.
    # __module__ şartı olmazsa import edilen temel sınıflar da (örn.
    # PlaywrightTabanScraper) eşleşir ve alfabetik sırada spider'dan önce
    # bulunup NotImplementedError'a yol açar.
    for _, nesne in inspect.getmembers(modul, inspect.isclass):
        if (issubclass(nesne, TabanScraper)
                and nesne.__module__ == modul.__name__):
            return nesne
    raise RuntimeError(f"{spider_adi} modülünde TabanScraper alt sınıfı yok")


def bankayi_calistir(banka_conf: dict) -> None:
    """Tek bankanın spider'ını çalıştırır ve sonucu loglar."""
    kod = banka_conf["id"]
    print(f"\n=== {banka_conf['kisa_ad']} ({kod}) ===")

    with get_session() as session:
        banka = session.query(Banka).filter_by(kod=kod).first()
        if banka is None:
            print("  Banka veritabanında yok — önce 'python -m backend.db.seed' çalıştırın")
            return

        # ScrapeLog: başarı da hata da kayda geçer (izlenebilirlik).
        log = ScrapeLog(banka_id=banka.id, durum="hata", kampanya_sayisi=0)
        try:
            spider = spider_sinifini_bul(banka_conf["spider"])()
            kayitlar = list(spider.kampanyalari_topla())
            spider.kaydet(kayitlar)
            log.durum = "basarili" if kayitlar else "kismi"
            log.kampanya_sayisi = len(kayitlar)
            log.hata_mesaji = None
        except NotImplementedError:
            log.hata_mesaji = "spider henüz yazılmadı"
            print("  Spider henüz yazılmadı, atlanıyor")
        except Exception as hata:  # tek bankanın hatası tüm koşuyu durdurmasın
            log.hata_mesaji = f"{hata.__class__.__name__}: {hata}"
            print(f"  HATA: {log.hata_mesaji}")

        session.add(log)
        session.commit()


def main() -> None:
    # argparse: Python'un standart komut satırı argüman ayrıştırıcısı.
    # --hepsi bayrağı ile ya da banka kodu vererek çalıştırılır.
    parser = argparse.ArgumentParser(description="FinAgent veri toplama çalıştırıcısı")
    parser.add_argument("banka", nargs="?", help="banks.yaml'daki banka id'si")
    parser.add_argument("--hepsi", action="store_true", help="aktif tüm bankaları çek")
    args = parser.parse_args()

    init_db()  # tablolar yoksa oluştur (idempotent)

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