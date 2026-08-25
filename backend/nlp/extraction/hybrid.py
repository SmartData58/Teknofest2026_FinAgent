import os
from typing import Any

from .llm_extractor import ALAN_SEMASI, llm_hazir, llm_ile_cikar
from .rule_based import AlanBulgusu, kurallarla_cikar

LLM_AKTIF = os.environ.get("FINAGENT_LLM", "1") != "0"

# Kampanya için sorulabilir tüm alanlar (mevcut davranış — DEĞİŞMEDİ)
SORULABILIR_ALANLAR_KAMPANYA = list(ALAN_SEMASI.keys()) + ["hedef_kitle"]

# Ürün için SADECE urun_kategori sorulacak
SORULABILIR_ALANLAR_URUN = ["urun_kategori"]

_llm_kullanilabilir: bool | None = None


def _llm_var_mi() -> bool:
    if not LLM_AKTIF:
        print(" ℹ️ FINAGENT_LLM=0 olduğu için LLM devre dışı.")
        return False
    hazir = llm_hazir()
    if not hazir:
        print(" ⚠️ UYARI: Ollama/Model erişilemez — Sadece kural tabanlı modda çalışılıyor.")
    return hazir


def hibrit_cikar(baslik: str, metin: str, kayit_tipi: str = "kampanya") -> dict[str, AlanBulgusu]:
    """
    Kural + LLM hibrit çıkarımı gerçekleştirir.
    kayit_tipi: "kampanya" -> tüm alanlar sorulabilir (mevcut davranış)
                "urun"     -> yalnızca urun_kategori LLM'e sorulur
    """
    tam_metin = f"{baslik or ''} . {metin or ''}".strip()
    if not tam_metin or tam_metin == ".":
        return {}

    # 1. KATMAN: KURAL TABANLI ÇIKARIM (her iki tip için de kural tabanlı çalışır)
    bulgular: dict[str, AlanBulgusu] = kurallarla_cikar(baslik, metin)

    # Kayıt tipine göre sorulabilir alan setini belirle
    sorulabilir = (
        SORULABILIR_ALANLAR_KAMPANYA if kayit_tipi == "kampanya"
        else SORULABILIR_ALANLAR_URUN
    )

    # ÜRÜN modunda: kural tabanlı bulunan diğer tüm alanları (finansman_tutari vb.)
    # LLM'e SORMA — sadece urun_kategori eksikse LLM'e sor. Ayrıca kural tabanlının
    # yanlışlıkla bulduğu alakasız alanları da (istersen) burada temizleyebilirsin.
    if kayit_tipi == "urun":
        # LLM'e sorulacak alanları urun_kategori ile sınırla
        bulgular = {k: v for k, v in bulgular.items() if k == "urun_kategori"} \
            if False else bulgular  # kural tabanlının diğer bulgularını SİLMEK istersen üstteki satırı aktif et

    # 2. KATMAN: EKSİK ALANLAR İÇİN LLM
    eksikler = []
    for alan in sorulabilir:
        if alan not in bulgular:
            eksikler.append(alan)
        else:
            obj = bulgular[alan]
            val = getattr(obj, "deger", None) if hasattr(obj, "deger") else (obj.get("deger") if isinstance(obj, dict) else obj)
            if val is None or val == "":
                eksikler.append(alan)

    print(f"\n 📊 [{kayit_tipi.upper()}] Kural ile bulunan geçerli alan: {len(sorulabilir) - len(eksikler)} | LLM'e sorulacak eksik alan: {len(eksikler)}")

    if not eksikler:
        return bulgular

    if _llm_var_mi():
        print(f" 🧠 LLM çalıştırılıyor... ({len(eksikler)} eksik alan sorgulanıyor)")
        llm_bulgulari = llm_ile_cikar(tam_metin, eksikler)

        llm_tespit_sayisi = 0
        for alan, bulgu in llm_bulgulari.items():
            val = getattr(bulgu, "deger", None) if hasattr(bulgu, "deger") else (bulgu.get("deger") if isinstance(bulgu, dict) else bulgu)
            if val is not None and val != "":
                bulgular[alan] = bulgu
                llm_tespit_sayisi += 1
                guven = getattr(bulgu, "guven", None) if hasattr(bulgu, "guven") else (bulgu.get("guven") if isinstance(bulgu, dict) else "N/A")
                print(f"    └─ 🎯 [LLM TESPİTİ] -> Alan: '{alan}' | Değer: '{val}' | Güven: {guven}")

        if llm_tespit_sayisi == 0:
            print("    └─ ⚠️ LLM sorgulanan eksik alanlar için herhangi bir veri bulamadı.")
        else:
            print(f" ✨ LLM toplam {llm_tespit_sayisi} adet eksik alanı başarıyla çıkardı.\n")

    return bulgular