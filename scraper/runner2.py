import importlib
import sys
import traceback
from pathlib import Path

# Proje kök dizinini Python yoluna ekle
PROJE_KOK = Path(__file__).resolve().parent.parent
if str(PROJE_KOK) not in sys.path:
    sys.path.append(str(PROJE_KOK))

# scraper dizinini Python yoluna ekle
SCRAPER_DIZINI = Path(__file__).resolve().parent
if str(SCRAPER_DIZINI) not in sys.path:
    sys.path.append(str(SCRAPER_DIZINI))


def finansman_runner_calistir():
    """scraper/finans_hesap/finansman_runner.py çalıştırıcısı"""
    print("\n==========================================")
    print("🏦 Finansman Runner İşlemleri Başlatılıyor...")
    print("==========================================")
    try:
        finansman_modul = importlib.import_module("scraper.finans_hesap.finansman_runner")
        if hasattr(finansman_modul, "main"):
            finansman_modul.main()
            print("✅ Finansman runner başarıyla tamamlandı.")
        else:
            print("⚠️ 'finansman_runner' içinde 'main()' fonksiyonu bulunamadı.")
    except Exception:
        print("❌ Finansman runner çalıştırılırken bir hata oluştu:")
        traceback.print_exc()


def katilim_hesap_runner_calistir():
    """scraper/kar_payi_hesap/katilim_hesap_runner.py çalıştırıcısı"""
    print("\n==========================================")
    print("📊 Katılım Hesaplama İşlemleri Başlatılıyor...")
    print("==========================================")
    try:
        katilim_modul = importlib.import_module("scraper.kar_payi_hesap.katilim_hesap_runner")
        if hasattr(katilim_modul, "main"):
            katilim_modul.main()
            print("✅ Katılım hesaplama runner başarıyla tamamlandı.")
        else:
            print("⚠️ 'katilim_hesap_runner' içinde 'main()' fonksiyonu bulunamadı.")
    except Exception:
        print("❌ Katılım hesaplama runner çalıştırılırken bir hata oluştu:")
        traceback.print_exc()


def main():
    # 1. Finansman Verilerini Birleştirme
    finansman_runner_calistir()

    # 2. Mevduat / Katılım Hesaplamalarını Kaydetme
    katilim_hesap_runner_calistir()


if __name__ == "__main__":
    main()