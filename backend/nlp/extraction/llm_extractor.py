# =============================================================================
# llm_extractor.py — Uzak LLM API ile SADECE Ürün Kategorisi Çıkarımı
# =============================================================================

import json
import os
import re

import requests

# 🛠️ GÖRECELİ IMPORT (eskiden `from backend.nlp.extraction.rule_based import`).
# Mutlak yol yalnızca REPO KÖKÜNDEN çalıştırıldığında çözülüyordu; konteynerde
# WORKDIR `/app` ve bu klasörün kendisi backend olduğu için `backend` diye bir
# paket YOK — modül `ModuleNotFoundError: No module named 'backend'` ile
# patlıyordu. Kardeş modüller (hybrid.py, extractor.py) zaten göreceli import
# kullanıyor; tek istisna buydu.
from .rule_based import AlanBulgusu


# =============================================================================
# 🚨 .env YÜKLEME — BOŞ DOSYA GERÇEĞİNİ GÖLGELİYORDU.
#
# Eskiden düz `load_dotenv()` çağrılıyordu. python-dotenv, çağıran dosyanın
# klasöründen YUKARI doğru yürüyüp bulduğu İLK `.env`'i yükler ve durur.
# Bu depoda iki tane var:
#     backend/.env   ->      0 bayt   (konteyner bind-mount'unun tutamağı)
#     .env           -> 12.012 bayt   (gerçek yapılandırma)
# Arama backend/.env'i önce buluyor, onu yüklüyor (hiçbir şey) ve duruyordu.
# Sonuç: EVREN_API_KEY boş -> API 401 -> llm_hazir() False -> LLM çıkarımı
# ÜRETİMDE HİÇ ÇALIŞMIYOR, ama hata da vermiyordu: hybrid.py "Model erişilemez"
# deyip kural tabanlı moda düşüyor ve boru hattı "başarılı" görünüyordu.
#
# Sessizce devre dışı kalan bir özellik, çöken bir özellikten daha pahalıdır.
# Artık BOŞ .env dosyaları atlanıyor; ilk DOLU olan yükleniyor.
# =============================================================================
def _env_yukle() -> str:
    """Yukarı doğru yürüyüp ilk DOLU .env dosyasını yükler; yolunu döner."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return ""
    dizin = os.path.dirname(os.path.abspath(__file__))
    while True:
        aday = os.path.join(dizin, ".env")
        if os.path.isfile(aday) and os.path.getsize(aday) > 0:
            load_dotenv(aday, override=False)
            return aday
        ust = os.path.dirname(dizin)
        if ust == dizin:            # kök dizine ulaşıldı
            return ""
        dizin = ust


ENV_DOSYASI = _env_yukle()

LLM_API_KEY = os.environ.get("EVREN_API_KEY") or os.environ.get("FINAGENT_LLM_API_KEY", "")
LLM_BASE_URL = (os.environ.get("EVREN_BASE_URL") or os.environ.get("FINAGENT_LLM_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1")).rstrip("/")

# Varsayılan model
MODEL = os.environ.get("EVREN_MODEL_HIZLI") or os.environ.get("FINAGENT_LLM_MODEL", "llm-fast")

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

# =============================================================================
# 🚨 DEĞER UZAYI BİRLİĞİ — AYNI ALAN, İKİ FARKLI BİÇİM.
#
# Kural tabanlı çıkarıcı (rule_based.KATEGORI_KURALLARI) `urun_kategori` alanına
# İNSAN OKUNUR ETİKET yazıyor:  "Konut / Gayrimenkul Finansmanları"
# Bu modülün prompt'u ise KOD döndürüyor:                "konut_gayrimenkul"
#
# İkisi aynı alana yazıyor. Mongo'daki 95 üründe bugün yalnızca etiket biçimi
# var — çünkü LLM katmanı (boş API anahtarı yüzünden) hiç çalışmamıştı. Anahtar
# düzeltilir düzeltilmez aynı alan iki ayrı biçimde dolmaya başlayacaktı ve
# gösterge paneli/sohbet tarafında kategori sayımları sessizce ikiye bölünecekti.
#
# Sınıflandırıcıya KOD sordurmaya devam ediyoruz (dar ve kararlı bir küme),
# ama kaydetmeden ÖNCE kural tabanlının kanonik etiketine çeviriyoruz.
# ⚠️ Etiketler rule_based.py'deki KATEGORI_KURALLARI ile AYNEN eşleşmeli;
#    orada değişirse burası da güncellenmeli.
# =============================================================================
_KOD_TO_ETIKET = {
    "dijital_aninda_alisveris": "Dijital / Anında Alışveriş Finansmanları",
    "bireysel_ihtiyac": "Bireysel / İhtiyaç Finansmanları",
    "konut_gayrimenkul": "Konut / Gayrimenkul Finansmanları",
    "tasit_finansmani": "Taşıt Finansmanları",
    "ticari_kurumsal": "Ticari & Kurumsal Finansmanlar",
    "diger": "Diğer",
}

SORULABILIR_ALANLAR = list(ALAN_SEMASI) + ["hedef_kitle", "urun_kategori"]


def _kategori_normalize(ham) -> str | None:
    """LLM'in döndürdüğü kodu geçerli kategoriye eşler; yakın yazımları kurtarır.

    🚨 GERÇEK ÖRNEK: model "İş Yeri Finansmanı" için `dijital_anima_alisveris`
    üretti — `aninda` yerine `anima`. Katı küme kontrolü bunu reddetti ve alan
    boş kaldı; oysa modelin ne demek istediği tartışmasızdı. Sınıflandırmayı
    tek harf yüzünden çöpe atmak, veriyi olduğundan eksik gösterir.

    Katılığı korumak için eşik YÜKSEK (0.85) ve aday kümesi altı elemanlı —
    yani "gerçekten yakın olmayan" bir çıktı yine reddedilir. Aynı teknik
    chatbot/intent.py::bulanik_gorsel_istegi'nde de kullanılıyor.
    """
    if not ham:
        return None
    kod = re.sub(r"[^a-z0-9_]", "", str(ham).strip().lower().replace(" ", "_").replace("-", "_"))
    if kod in _GECERLI_URUN_KATEGORILERI:
        return kod
    from difflib import SequenceMatcher
    en_iyi, en_iyi_oran = None, 0.0
    for aday in _GECERLI_URUN_KATEGORILERI:
        oran = SequenceMatcher(None, kod, aday).ratio()
        if oran > en_iyi_oran:
            en_iyi, en_iyi_oran = aday, oran
    if en_iyi_oran >= 0.85:
        print(f" └─ ℹ️ LLM kodu '{ham}' -> '{en_iyi}' olarak düzeltildi "
              f"(benzerlik {en_iyi_oran:.2f})")
        return en_iyi
    return None


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
        ham_deger = ham_json.get("urun_kategori")
        # Yakın yazım hatalarını kurtarır, uzak olanı yine reddeder.
        deger = _kategori_normalize(ham_deger)

        if deger in _GECERLI_URUN_KATEGORILERI:
            # Kanonik etikete çevir (bkz. _KOD_TO_ETIKET notu): kural tabanlı
            # çıkarıcıyla AYNI değer uzayında kalmak zorundayız.
            etiket = _KOD_TO_ETIKET.get(deger, deger)
            # 🛠️ `yontem` ve `guven` AÇIKÇA VERİLİYOR.
            # AlanBulgusu'nun varsayılanları `yontem="regex", guven=1.0`.
            # Üç konumlu argümanla çağrıldığında LLM'in TAHMİNİ, kayda
            # "regex ile bulundu, güven 1.0" diye giriyordu — yani bir dil
            # modelinin çıkarımı deterministik bir eşleşmeyle aynı ağırlığa
            # sahip oluyordu. Dosyada tanımlı LLM_GUVEN (0.7) ise hiçbir yerde
            # kullanılmıyordu. Aşağı akıştaki denetim/ayıklama bu ayrımı
            # görebilmeli.
            bulgular["urun_kategori"] = AlanBulgusu(
                etiket, f"LLM siniflandirmasi: {deger}", f"llm:{MODEL}",
                yontem="llm", guven=LLM_GUVEN,
            )
            print(f" └─ 🎯 [LLM TESPİTİ] -> Kategori: '{etiket}' (kod: {deger})")
        else:
            print(" └─ ⚠️ LLM kategoriyi belirleyemedi veya geçersiz kategori "
                  f"döndü: {ham_deger!r}")

    return bulgular