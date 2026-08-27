import os
import sys

# 1. ÖNCE Proje Kök Dizinini (Teknofest2026_FinAgent) yola ekliyoruz
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. IMPORT İŞLEMİNİ YOL EKLENDİKTEN SONRA YAPIYORUZ
# 🛠️ ÇİFT YOL: bu modül iki farklı kökten çalıştırılıyor — pipeline.py depo
# kökünden `backend.*` diye, backend konteyneri ise WORKDIR /app (yani
# backend/) içinden `nlp.*` diye import ediyor. Tek biçim kullanmak,
# diğerinde ModuleNotFoundError veriyor ve bu yüzden geçici bir symlink
# gerekiyordu. agents.py'deki yerleşik kalıp buraya da uygulandı.
try:
    from backend.nlp.extraction.hybrid import hibrit_cikar
except ModuleNotFoundError:
    from nlp.extraction.hybrid import hibrit_cikar


test_metin = "100.000 TL kredide 12 ay vade ve %0.99 faiz imkanı."
test_baslik = "Kredi Kampanyası"

if __name__ == "__main__":
    try:
        print("LLM / Hibrit çıkarım testi başlatılıyor...")
        sonuc = hibrit_cikar(test_baslik, test_metin)
        print("\n--- ÇIKARIM SONUCU ---")
        print(sonuc)
    except Exception as e:
        print(f"\n❌ Hata Oluştu: {e}")