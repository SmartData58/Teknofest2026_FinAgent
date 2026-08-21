import json
import re
from pathlib import Path

# Doğrudan tam dosya yolu (Windows yol biçimi)
JSON_YOLU = Path(r"D:\Teknofest2026_FinAgent\backend\nlp\ner\datasets\label_studio_veri.json")

# "Tüm Kampanyalar ... Arşiv" arasındaki dinamik sayıları ve kategori menüsünü yakalayan Regex kalıbı
PATTERN_MENU = r"Tüm Kampanyalar\s+\d+.*?\d+\s+Giyim ve Aksesuar\s+Arşiv"

# "SAYFAYI PAYLAŞ" ve sonrasındaki HER ŞEYİ yakalayan Regex kalıbı
PATTERN_PAYLAS_VE_SONRASI = r"SAYFAYI PAYLAŞ.*$"

if JSON_YOLU.exists():
    print(f"🔍 Dosya bulundu, işleniyor: {JSON_YOLU}")
    
    with open(JSON_YOLU, "r", encoding="utf-8") as f:
        veri = json.load(f)

    degisen_sayisi = 0
    for item in veri:
        if isinstance(item, dict) and "ham_metin" in item and item["ham_metin"]:
            eski_metin = item["ham_metin"]
            
            # 1. Menü ve sayaç bloğunu temizle
            yeni_metin = re.sub(PATTERN_MENU, "", eski_metin, flags=re.IGNORECASE)
            
            # 2. Baştaki "Anasayfa Kart Kampanyaları" ifadesini temizle
            yeni_metin = re.sub(r"^Anasayfa Kart Kampanyaları\s*", "", yeni_metin, flags=re.IGNORECASE)
            
            # 3. "SAYFAYI PAYLAŞ" ve sonrasında gelen tüm metinleri sil
            yeni_metin = re.sub(PATTERN_PAYLAS_VE_SONRASI, "", yeni_metin, flags=re.IGNORECASE | re.DOTALL)
            
            # 4. Fazla boşlukları teke indirip kenar boşluklarını sil
            yeni_metin = re.sub(r"\s+", " ", yeni_metin).strip()
            
            if eski_metin != yeni_metin:
                item["ham_metin"] = yeni_metin
                degisen_sayisi += 1

    # Temizlenmiş veriyi dosyaya geri yaz
    with open(JSON_YOLU, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

    print(f"✅ İşlem başarılı! Toplam {degisen_sayisi} adet kayıttaki gereksiz metinler ve alt menüler temizlendi.")
else:
    print(f"❌ Dosya bulunamadı! Lütfen dosyanın bu konumda olduğundan emin olun:\n{JSON_YOLU}")