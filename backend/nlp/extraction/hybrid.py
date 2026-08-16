# =============================================================================
# hybrid.py — Hibrit Çıkarım: Kural + LLM Birleşimi
# =============================================================================
import os
from typing import Any

from .llm_extractor import TUM_ALAN_SEMALARI, llm_hazir, llm_ile_cikar
from .rule_based import AlanBulgusu, kurallarla_cikar

LLM_AKTIF = os.environ.get("FINAGENT_LLM", "1") != "0"

# LLM'e sorulabilir hedef alanların listesi
SORULABILIR_ALANLAR = list(TUM_ALAN_SEMALARI.keys())

_llm_kullanilabilir: bool | None = None


def _llm_var_mi() -> bool:
    """Ollama/LLM servisinin aktif ve hazır olup olmadığını kontrol eder."""
    global _llm_kullanilabilir
    if _llm_kullanilabilir is None:
        _llm_kullanilabilir = LLM_AKTIF and llm_hazir()
        if LLM_AKTIF and not _llm_kullanilabilir:
            print(" ⚠️ UYARI: Ollama/Model erişilemez — Sadece kural tabanlı modda çalışılıyor.")
    return _llm_kullanilabilir


def hibrit_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    """
    Kural + LLM hibrit çıkarımı gerçekleştirir. Pipeline'ın tek çıkarım kapısıdır.

    Dönen AlanBulgusu nesnesindeki 'yontem' ve 'kural' alanlarından kaynağı anlaşılır:
      - yontem="regex" -> Kural katmanı (Güven: 1.0)
      - yontem="llm"   -> LLM katmanı   (Güven: 0.7 - 0.85)
    """
    tam_metin = f"{baslik or ''} . {metin or ''}".strip()
    if not tam_metin or tam_metin == ".":
        return {}

    # 1. KATMAN: KURAL TABANLI ÇIKARIM
    bulgular: dict[str, AlanBulgusu] = kurallarla_cikar(baslik, metin)

    # 2. KATMAN: EKSİK ALANLAR İÇİN LLM FİLTRESİ
    eksikler = [alan for alan in SORULABILIR_ALANLAR if alan not in bulgular]

    if not eksikler:
        return bulgular

    if _llm_var_mi():
        llm_bulgulari = llm_ile_cikar(tam_metin, eksikler)

        for alan, bulgu in llm_bulgulari.items():
            if alan not in bulgular:
                bulgular[alan] = bulgu

    return bulgular