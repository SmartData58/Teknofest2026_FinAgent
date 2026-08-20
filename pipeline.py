import argparse
import sys
from datetime import datetime, timezone


def log(msg: str):
    print(f"\n==========================================")
    print(f"🚀 [PIPELINE] {msg}")
    print(f"==========================================")


def run_step_1_seed():
    log("ADIM 1: Banka Seed İşlemi Başlatılıyor...")

    try:
        from backend.db.seed_banks import seed_bankalar
        seed_bankalar()
    except ModuleNotFoundError:
        try:
            from seed import seed_bankalar
            seed_bankalar()
        except Exception as e:
            print(f"❌ Seed çalıştırma hatası: {e}")
            sys.exit(1)


def run_step_2_runner(banka: str = None, hepsi: bool = False):
    log("ADIM 2: Scraper Verileri Toplanıyor...")

    try:
        from scraper.runner import main as runner_main

        # Scraper runner'ının beklediği sys.argv simülasyonu
        if hepsi:
            sys.argv = ["runner.py", "--hepsi"]
        elif banka:
            sys.argv = ["runner.py", banka]

        runner_main()
    except Exception as e:
        print(f"❌ Scraper / Runner çalıştırma hatası: {e}")
        sys.exit(1)


def run_step_3_extraction():
    log("ADIM 3: LLM & Kural Tabanlı Bilgi Çıkarımı Yapılıyor...")
    try:
        from backend.nlp.extraction.extractor import temiz_verilerden_bilgi_cikar
        temiz_verilerden_bilgi_cikar()
    except Exception as e:
        print(f"❌ Bilgi Çıkarım (Extractor) hatası: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="SmartData Uçtan Uca Pipeline")
    parser.add_argument("banka", nargs="?", help="Çalıştırılacak banka id'si (ör. albaraka)")
    parser.add_argument("--hepsi", action="store_true", help="Aktif tüm bankaları sırayla çek")
    args = parser.parse_args()

    if not args.hepsi and not args.banka:
        parser.error("Lütfen bir banka id'si belirtin (ör. python pipeline.py albaraka) ya da --hepsi kullanın.")

    baslangic = datetime.now(timezone.utc)
    print("⚡ SmartData Uçtan Uca Pipeline Başlatılıyor...")

    # Sırasıyla Pipeline Adımları
    run_step_1_seed()
    run_step_2_runner(banka=args.banka, hepsi=args.hepsi)
    run_step_3_extraction()

    gecen_sure = (datetime.now(timezone.utc) - baslangic).seconds
    log(f"🎉 TÜM PIPELINE BAŞARIYLA TAMAMLANDI! (Süre: {gecen_sure} saniye)")


if __name__ == "__main__":
    main()