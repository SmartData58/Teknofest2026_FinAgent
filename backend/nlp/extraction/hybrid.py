# =============================================================================
# hybrid.py — Hibrit Çıkarım: Kural + LLM Birleşimi
# =============================================================================
#
# STRATEJİ:
#   1. ÖNCE KURALLAR — hızlı, deterministik, güven=1.0 (Regex / Normalizasyon)
#   2. Kuralların BOŞ bıraktığı alanlar için LOKAL LLM — güven=0.7 (Ollama / Qwen)
#   3. Çakışmada HER ZAMAN KURAL KAZANIR (Kural verisi ezilemez).
# =============================================================================

import os
from typing import Any

from .llm_extractor import TUM_ALAN_SEMALARI, llm_hazir, llm_ile_cikar
from .rule_based import AlanBulgusu, kurallarla_cikar

LLM_AKTIF = os.environ.get("FINAGENT_LLM", "1") != "0"

# LLM'e sorulabilir hedef alanların listesi
SORULABILIR_ALANLAR = list(TUM_ALAN_SEMALARI.keys())

# Ollama bağlantısını her kampanya metninde tekrar tekrar sorgulamamak için önbellek
_llm_kullanilabilir: bool | None = None


def _llm_var_mi() -> bool:
    """Ollama/LLM servisinin aktif ve hazır olup olmadığını kontrol eder."""
    global _llm_kullanilabilir
    if _llm_kullanilabilir is None:
        _llm_kullanilabilir = LLM_AKTIF and llm_hazir()
        if LLM_AKTIF and not _llm_kullanilabilir:
            print("  ⚠️ UYARI: Ollama/Model erişilemez — Sadece kural tabanlı modda çalışılıyor.")
    return _llm_kullanilabilir


def hibrit_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    """
    Kural + LLM hibrit çıkarımı gerçekleştirir. Pipeline'ın tek çıkarım kapısıdır.

    Dönen AlanBulgusu nesnesindeki 'yontem' ve 'kural' alanlarından kaynağı anlaşılır:
      - yontem="regex" -> Kural katmanı (Güven: 1.0)
      - yontem="llm"   -> LLM katmanı   (Güven: 0.7)
    """
    tam_metin = f"{baslik or ''} . {metin or ''}".strip()
    if not tam_metin or tam_metin == ".":
        return {}

    # -------------------------------------------------------------------------
    # 1. KATMAN: KURAL TABANLI ÇIKARIM (Deterministik & Hızlı)
    # -------------------------------------------------------------------------
    bulgular: dict[str, AlanBulgusu] = kurallarla_cikar(baslik, metin)

    # -------------------------------------------------------------------------
    # 2. KATMAN: EKSİK ALANLAR İÇİN LLM FİLTRESİ
    # -------------------------------------------------------------------------
    # LLM'e sorulabilir şemalardan kuralın bulamadığı eksik alanları tespit et
    eksikler = [alan for alan in SORULABILIR_ALANLAR if alan not in bulgular]

    # Eğer eksik alan kalmadıysa LLM'i pas geç (Maksimum Hız & 0 LLM Maliyeti)
    if not eksikler:
        # print("  ✅ Tüm alanlar kural katmanında bulundu. LLM bypass edildi.")
        return bulgular

    # Eğer eksik varsa ve LLM kullanılabilir durumdaysa çağrı yap
    if _llm_var_mi():
        llm_bulgulari = llm_ile_cikar(tam_metin, eksikler)

        # Kural katmanının bulduğu veriler önceliklidir, ezilemez.
        # LLM yalnızca kuralın boş bıraktığı (eksik) alanları doldurur.
        for alan, bulgu in llm_bulgulari.items():
            if alan not in bulgular:
                bulgular[alan] = bulgu

    return bulgular