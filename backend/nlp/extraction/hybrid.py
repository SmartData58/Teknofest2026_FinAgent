# =============================================================================
# hybrid.py — Hibrit Çıkarım: Kural + LLM Birleşimi
# =============================================================================
#
# STRATEJİ (mimari dokümandaki hibrit yaklaşımın kodu):
#   1. ÖNCE KURALLAR — hızlı, deterministik, güven=1.0
#   2. Kuralların BOŞ bıraktığı alanlar için LOKAL LLM — güven=0.7
#   3. Çakışmada HER ZAMAN KURAL KAZANIR (kural zaten önce doldurduğu için
#      LLM'e o alan hiç sorulmaz — çakışma tasarım gereği imkânsız)
# =============================================================================

import os 

from backend.nlp.extraction.llm_extractor import SORULABILIR_ALANLAR, llm_hazir, llm_ile_cikar
from backend.nlp.extraction.rule_based import AlanBulgusu, kurallarla_cikar

LLM_AKTIF = os.environ.get("FINAGENT_LLM", "1") != "0"
#herkampanya için ollamanın açık olup olmadığını kontrol etmek zaman kaybı 
#1 kere kontrol edilir
_llm_kullanilabilir: bool | None = None

def _llm_var_mi() -> bool:
    global _llm_kullanilabilir
    if _llm_kullanilabilir is None:
        _llm_kullanilabilir = LLM_AKTIF and llm_hazir()
        if LLM_AKTIF and not _llm_kullanilabilir:
            print("  UYARI: Ollama/model erişilemez — kural-tek modda devam ediliyor")
    return _llm_kullanilabilir


def hibrit_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    """Kural + LLM hibrit çıkarımı. Pipeline'ın tek çıkarım kapısı.

    Dönen AlanBulgusu.kural alanından kaynak anlaşılır:
      "yuzde+oran_baglami" gibi → kural katmanı (güven 1.0)
      "llm:qwen2.5:3b"          → LLM katmanı  (güven 0.7)
    """
    # 1. katman: kurallar
    bulgular = kurallarla_cikar(baslik, metin)

    # 2. katman: yalnızca eksik alanlar LLM'e sorulur
    eksikler = [a for a in SORULABILIR_ALANLAR if a not in bulgular]
    if eksikler and _llm_var_mi():
        tam_metin = f"{baslik or ''} . {metin or ''}"
        llm_bulgulari = llm_ile_cikar(tam_metin, eksikler)
        # Kural bulguları zaten sözlükte; LLM yalnızca eksikleri ekler.
        # (setdefault yerine güvenli birleşim: kural anahtarı ezilemez)
        for alan, bulgu in llm_bulgulari.items():
            bulgular.setdefault(alan, bulgu)

    return bulgular