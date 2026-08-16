import os
import sys

# Dosya konumundan (backend/nlp/extraction) proje kök dizinine (Teknofest2026_FinAgent) ulaş
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from hybrid import hibrit_cikar

test_metin = "100.000 TL kredide 12 ay vade ve %0.99 faiz imkanı."
test_baslik = "Kredi Kampanyası"

try:
    print("LLM / Hibrit çıkarım testi başlatılıyor...")
    sonuc = hibrit_cikar(test_baslik, test_metin)
    print("\n--- ÇIKARIM SONUCU ---")
    print(sonuc)
except Exception as e:
    print(f"\n❌ Hata Oluştu: {e}")