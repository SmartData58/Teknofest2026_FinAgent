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
    """Ollama/LLM servisinin aktif ve hazır olup olmadığını anlık kontrol eder."""
    if not LLM_AKTIF:
        print(" ℹ️ FINAGENT_LLM=0 olduğu için LLM devre dışı.")
        return False
    
    hazir = llm_hazir()
    if not hazir:
        print(" ⚠️ UYARI: Ollama/Model erişilemez — Sadece kural tabanlı modda çalışılıyor.")
    return hazir


#def hibrit_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
#    """
#    Kural + LLM hibrit çıkarımı gerçekleştirir. Pipeline'ın tek çıkarım kapısıdır.
#    """
#    tam_metin = f"{baslik or ''} . {metin or ''}".strip()
#    if not tam_metin or tam_metin == ".":
#        return {}
#
#    # 1. KATMAN: KURAL TABANLI ÇIKARIM
#    bulgular: dict[str, AlanBulgusu] = kurallarla_cikar(baslik, metin)
#
#    # 2. KATMAN: EKSİK VEYA NONE DEĞERLİ ALANLAR İÇİN LLM FİLTRESİ
#    eksikler = []
#    for alan in SORULABILIR_ALANLAR:
#        if alan not in bulgular:
#          eksikler.append(alan)
#        else:
#            obj = bulgular[alan]
#            # AlanBulgusu nesnesi veya dict içindeki 'deger' kontrolü
#            val = getattr(obj, "deger", None) if hasattr(obj, "deger") else (obj.get("deger") if isinstance(obj, dict) else obj)
#            if val is None or val == "":
#                eksikler.append(alan)

    # Debug Log: Durumu terminalde görmek için
#    print(f" 📊 Kural ile bulunan geçerli alan: {len(SORULABILIR_ALANLAR) - len(eksikler)} | LLM'e sorulacak eksik alan: {len(eksikler)}")

#    if not eksikler:
#        return bulgular

#    if _llm_var_mi():
#        print(f" 🧠 LLM çalıştırılıyor... ({len(eksikler)} eksik alan aranıyor)")
#        llm_bulgulari = llm_ile_cikar(tam_metin, eksikler)

#        for alan, bulgu in llm_bulgulari.items():
#            val = getattr(bulgu, "deger", None) if hasattr(bulgu, "deger") else (bulgu.get("deger") if isinstance(bulgu, dict) else bulgu)
            # LLM geçerli bir değer bulduysa kuraldaki None/boş değerin üzerine yaz
#            if val is not None and val != "":
#                bulgular[alan] = bulgu

#    return bulgular

def hibrit_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    """
    Kural + LLM hibrit çıkarımı gerçekleştirir. Pipeline'ın tek çıkarım kapısıdır.
    """
    tam_metin = f"{baslik or ''} . {metin or ''}".strip()
    if not tam_metin or tam_metin == ".":
        return {}

    # 1. KATMAN: KURAL TABANLI ÇIKARIM
    bulgular: dict[str, AlanBulgusu] = kurallarla_cikar(baslik, metin)

    # 2. KATMAN: EKSİK VEYA NONE DEĞERLİ ALANLAR İÇİN LLM FİLTRESİ
    eksikler = []
    for alan in SORULABILIR_ALANLAR:
        if alan not in bulgular:
            eksikler.append(alan)
        else:
            obj = bulgular[alan]
            # AlanBulgusu nesnesi veya dict içindeki 'deger' kontrolü
            val = getattr(obj, "deger", None) if hasattr(obj, "deger") else (obj.get("deger") if isinstance(obj, dict) else obj)
            if val is None or val == "":
                eksikler.append(alan)

    # Durum Özeti Logu
    gecerli_kural_sayisi = len(SORULABILIR_ALANLAR) - len(eksikler)
    print(f"\n 📊 Kural ile bulunan geçerli alan: {gecerli_kural_sayisi} | LLM'e sorulacak eksik alan: {len(eksikler)}")

    if not eksikler:
        return bulgular

    if _llm_var_mi():
        print(f" 🧠 LLM çalıştırılıyor... ({len(eksikler)} eksik alan sorgulanıyor)")
        llm_bulgulari = llm_ile_cikar(tam_metin, eksikler)

        llm_tespit_sayisi = 0
        for alan, bulgu in llm_bulgulari.items():
            # Değeri çek
            val = getattr(bulgu, "deger", None) if hasattr(bulgu, "deger") else (bulgu.get("deger") if isinstance(bulgu, dict) else bulgu)
            
            # LLM geçerli bir değer bulduysa ekle ve terminale yazdır
            if val is not None and val != "":
                bulgular[alan] = bulgu
                llm_tespit_sayisi += 1
                
                # Ekstra metadata çekimi (Güven skoru, ham metin vb.)
                guven = getattr(bulgu, "guven", None) if hasattr(bulgu, "guven") else (bulgu.get("guven") if isinstance(bulgu, dict) else "N/A")
                print(f"    └─ 🎯 [LLM TESPİTİ] -> Alan: '{alan}' | Değer: '{val}' | Güven: {guven}")

        if llm_tespit_sayisi == 0:
            print("    └─ ⚠️ LLM sorgulanan eksik alanlar için herhangi bir veri bulamadı.")
        else:
            print(f" ✨ LLM toplam {llm_tespit_sayisi} adet eksik alanı başarıyla çıkardı.\n")

    return bulgular