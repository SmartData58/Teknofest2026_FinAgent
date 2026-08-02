import json
import os
from scraper.spiders.vakif_katilim import scrape_kampanyalar
from preprocessing import temizle

if __name__ == "__main__":
    
    # Gerekli klasör yollarını tanımlıyoruz
    raw_dir = os.path.join("data", "raw")
    processed_dir = os.path.join("data", "processed")

    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    # Dosya yolları
    raw_file_path = os.path.join(raw_dir, "kampanyalar_raw.json")
    processed_file_path = os.path.join(
        processed_dir, "kampanyalar_islenmis.json"
    )

    # 1. Adım: Veriyi Kazı
    
    ham_veriler = scrape_kampanyalar()

    # 2. Adım: Ham Veriyi 'data/raw' İçine Kaydet
    with open(raw_file_path, "w", encoding="utf-8") as f:
        json.dump(ham_veriler, f, ensure_ascii=False, indent=4)
    print(f"Ham veri başarıyla kaydedildi: {raw_file_path}")

    # 3. Adım: Veriyi Ön İşlemeden Geçir
    print("Veri ön işleme adımları uygulanıyor...")
    islenmis_veriler = []

    for veri in ham_veriler:
        islenmis_veri = {
            "baslik": temizle(veri["baslik"]),
            "tarih": temizle(veri["tarih"]),
            "detay": temizle(veri["detay"]),
        }
        islenmis_veriler.append(islenmis_veri)

    # 4. Adım: İşlenmiş Veriyi 'data/processed' İçine Kaydet
    with open(processed_file_path, "w", encoding="utf-8") as f:
        json.dump(islenmis_veriler, f, ensure_ascii=False, indent=4)
    print(f"İşlenmiş veri başarıyla kaydedildi: {processed_file_path}")
    print("Tüm işlemler tamamlandı!")