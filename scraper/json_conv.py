import json
import os

def jsonConv(url_linklker: list, json_dosya_adi):
    # 1. Bu fonksiyonun (json_conv.py) çalıştığı 'scraper' klasörünün yolunu bulur
    scraper_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. 'scraper' klasöründen bir üst klasöre (proje ana dizinine) çıkar
    project_root = os.path.dirname(scraper_dir)
    
    # 3. Ana dizinden nlp/preprocessing/data/raw klasörüne hedef yolu oluştururgit status
    target_dir = os.path.join(project_root, "nlp", "preprocessing", "data", "raw")
    
    # 4. Eğer raw klasörü bilgisayarda henüz oluşturulmadıysa otomatik oluşturur (hata almamak için)
    os.makedirs(target_dir, exist_ok=True)
    
    # 5. Klasör yolu ile göndereceğiniz dosya adını birleştirir
    tam_dosya_yolu = os.path.join(target_dir, json_dosya_adi)
    
    # 6. Dosyayı belirlenen tam yola kaydeder
    with open(tam_dosya_yolu, mode="w", encoding="utf-8") as f:
        json.dump(url_linklker, f, ensure_ascii=False, indent=4)