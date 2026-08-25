# =============================================================================
# llm_extractor.py — Uzak LLM API ile SADECE Ürün Kategorisi Çıkarımı
# =============================================================================

import json
import os
import re

import requests

from backend.nlp.extraction.rule_based import AlanBulgusu

# Tablodan alınan güncel API, URL ve Model yapılandırmaları
LLM_API_KEY = os.environ.get(
    "FINAGENT_LLM_API_KEY", "sk-evren-team28-d46aaaa9a44a3e3ddf81a1252e26fa20"
)
LLM_BASE_URL = os.environ.get(
    "FINAGENT_LLM_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1"
).rstrip("/")

# Varsayılan model
MODEL = os.environ.get("FINAGENT_LLM_MODEL", "qwen2.5-3b-instruct")

LLM_GUVEN = 0.7          # LLM bulgularının güven skoru
ZAMAN_ASIMI = 60         # API isteği için üst sınır (saniye)

# Diğer modüllerin ImportError almaması için geriye dönük uyumluluk şeması
ALAN_SEMASI = {
    "kar_payi_orani": (
        '"kar_payi_orani": sayı|null  '
        "(finansman kâr payı veya katılma hesabı kâr paylaşım oranı, örn 1.89. "
        "DİKKAT: mil/puan kazanım oranı, indirim oranı ve komisyon oranı "
        "kâr payı DEĞİLDİR — bunlar için null yaz)"
    ),
    "vade_ay": '"vade_ay": tamsayı|null  (AY cinsinden vade; yıl verilmişse 12 ile çarp)',
    "taksit_sayisi": (
        '"taksit_sayisi": tamsayı|null  '
        "(yalnızca metinde \"taksit\" kelimesiyle geçen sayı)"
    ),
    "finansman_tutari": (
        '"finansman_tutari": sayı|null  '
        "(TL, kredi/finansman üst limiti. DİKKAT: minimum hesap açılış tutarı, "
        "ATM para yatırma/çekme limiti ve ödül tutarı finansman DEĞİLDİR)"
    ),
    "odul_tutari_tl": (
        '"odul_tutari_tl": sayı|null  '
        "(TL cinsinden hediye/çek/bonus/puan ödülü. DİKKAT: finansman veya "
        "taksit desteği ödül DEĞİLDİR)"
    ),
}

_GECERLI_URUN_KATEGORILERI = {
    "dijital_aninda_alisveris",
    "bireysel_ihtiyac",
    "konut_gayrimenkul",
    "tasit_finansmani",
    "ticari_kurumsal",
    "diger",
}

SORULABILIR_ALANLAR = list(ALAN_SEMASI) + ["hedef_kitle", "urun_kategori"]


def llm_hazir() -> bool:
    """LLM API servisi erişilebilir durumda mı kontrol eder."""
    try:
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
        url = f"{LLM_BASE_URL}/models"
        cevap = requests.get(url, headers=headers, timeout=5)
        
        if cevap.status_code == 200:
            return True
        print(f" ⚠️ LLM API yanıt verdi ancak durum kodu hatalı: {cevap.status_code}")
        return False
    except Exception as e:
        print(f" ❌ LLM API Bağlantı Hatası ({LLM_BASE_URL}): {e}")
        return False


def _urun_kategori_promptu(metin: str) -> str:
    """Sadece ürün kategorisini sınıflandıran prompt."""
    return (
        "Türkçe katılım bankası ürün metnini sınıflandır.\n"
        "Soru: Bu ürün hangi KATEGORİye ait?\n"
        '- "dijital_aninda_alisveris": mağazada/dijitalde anında alışveriş finansmanı, hızlı finansman\n'
        '- "bireysel_ihtiyac": eğitim, okul, sağlık, tatil, teknoloji, doğalgaz vb. ihtiyaç finansmanları\n'
        '- "konut_gayrimenkul": ev, konut, arsa, işyeri, kentsel dönüşüm, prefabrik finansmanı\n'
        '- "tasit_finansmani": otomobil, araç, motosiklet, Togg, tekne, elektrikli araç finansmanı\n'
        '- "ticari_kurumsal": KOBİ, ticari, işletme sermayesi, tarım, GES/yeşil enerji, leasing, dış ticaret\n'
        '- "diger": yukarıdaki kategorilere girmeyen ürünler\n'
        "- Metinden anlaşılmıyorsa null yaz.\n"
        'Şu JSON ile cevap ver: {"urun_kategori": ...}\n\n'
        f"METİN: {metin[:1500]}\n\nJSON:"
    )


def _llm_api_json(prompt: str) -> dict | None:
    """OpenAI Uyumlu Chat Completions API'sine istek atıp JSON yanıtı döndürür."""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 100,
        "response_format": {"type": "json_object"}
    }

    try:
        cevap = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=ZAMAN_ASIMI,
        )

        if cevap.status_code != 200:
            print(f" ⚠️ LLM API Hatası [{cevap.status_code}]: {cevap.text}")
            return None

        veri = cevap.json()

        # Token kullanım bilgisi
        usage = veri.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        print(f" 📊 Token Kullanımı -> Girdi: {prompt_tokens} | Çıktı: {completion_tokens} | Toplam: {total_tokens}")

        raw_response = veri["choices"][0]["message"]["content"].strip()

        if not raw_response:
            return None

        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        temiz_metin = re.sub(r"<think>[\s\S]*?</think>", "", raw_response).strip()
        temiz_metin = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", temiz_metin).strip()

        json_match = re.search(r"\{[\s\S]*\}", temiz_metin)
        if json_match:
            return json.loads(json_match.group(0))

        raise json.JSONDecodeError("Geçerli bir JSON objesi bulunamadı", raw_response, 0)

    except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError) as hata:
        print(f"    LLM atlandı ({hata.__class__.__name__}) — kural bulgularıyla devam")
        return None


def llm_ile_cikar(metin: str, istenen_alanlar: list[str]) -> dict[str, AlanBulgusu]:
    """Ürün metinleri için SADECE ürün kategorisi çıkarımı yapacak şekilde filtrelenmiştir."""
    if not metin:
        return {}
    
    bulgular: dict[str, AlanBulgusu] = {}

    if "urun_kategori" in istenen_alanlar:
        ham_json = _llm_api_json(_urun_kategori_promptu(metin)) or {}
        deger = ham_json.get("urun_kategori")
        
        if deger in _GECERLI_URUN_KATEGORILERI:
            bulgular["urun_kategori"] = AlanBulgusu(
                deger, f"LLM siniflandirmasi: {deger}", f"llm:{MODEL}"
            )
            print(f" └─ 🎯 [LLM TESPİTİ] -> Kategori: '{deger}'")
        else:
            print(f" └─ ⚠️ LLM kategoriyi belirleyemedi veya geçersiz kategori döndü: {deger}")

    return bulgular