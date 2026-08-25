# =============================================================================
# llm_extractor.py — Uzak LLM API (llmfast/Teknofest Evren) ile Bilgi Çıkarımı
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

# varsayılan model (API'nizin desteklediği modeli environment üzerinden değiştirebilirsiniz)
MODEL = os.environ.get("FINAGENT_LLM_MODEL", "qwen2.5-3b-instruct")

LLM_GUVEN = 0.7          # LLM bulgularının güven skoru (kural=1.0'dan düşük)
ZAMAN_ASIMI = 60         # API isteği için üst sınır (saniye)

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


def llm_hazir() -> bool:
    """LLM API servisi erişilebilir durumda mı kontrol eder."""
    try:
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
        # OpenAI uyumlu /models uç noktası kontrolü
        url = f"{LLM_BASE_URL}/models"
        cevap = requests.get(url, headers=headers, timeout=5)
        
        if cevap.status_code == 200:
            return True
        print(f" ⚠️ LLM API yanıt verdi ancak durum kodu hatalı: {cevap.status_code}")
        return False
    except Exception as e:
        print(f" ❌ LLM API Bağlantı Hatası ({LLM_BASE_URL}): {e}")
        return False


def _prompt_kur(metin: str, istenen_alanlar: list[str]) -> str:
    """Yalnızca EKSİK sayısal alanları soran dar kapsamlı prompt üretir."""
    sema = ",\n  ".join(ALAN_SEMASI[a] for a in istenen_alanlar)
    return (
        "Türkçe katılım bankası kampanya metninden bilgi çıkarıyorsun.\n"
        "KURALLAR:\n"
        "- SADECE metinde açıkça yazan bilgileri doldur.\n"
        "- Metinde olmayan bilgiye null yaz. ASLA tahmin etme.\n"
        "- Sayıları Türkçe biçimden çevir: %1,89 → 1.89 | 50.000 TL → 50000\n"
        f"Şu JSON şemasıyla cevap ver:\n{{\n  {sema}\n}}\n\n"
        f"METİN: {metin}\n\nJSON:"
    )


def _siniflandirma_promptu(metin: str) -> str:
    return (
        "Türkçe katılım bankası kampanya metnini sınıflandır.\n"
        "Soru: Kampanya KİMLERE yönelik?\n"
        '- "yeni_musteri": bankaya yeni müşteri olacaklara özel\n'
        '- "mevcut_musteri": bankanın mevcut kart/hesap sahiplerine yönelik\n'
        '- "maas_musterisi": maaşını bankaya taşıyanlara özel\n'
        '- "segment": belirli bir gruba özel (esnaf, KOBİ, işletme, emekli, öğrenci)\n'
        "- null: metinden anlaşılmıyor\n"
        'Şu JSON ile cevap ver: {"hedef_kitle": ...}\n\n'
        f"METİN: {metin}\n\nJSON:"
    )


_SINIR_ON = r"(?<![\d.,])"
_SINIR_SON = r"(?!\d)(?![.,]\d)"


def _varyantlar(deger: float) -> set[str]:
    varyantlar = set()
    if deger == int(deger):
        tam = int(deger)
        varyantlar.add(str(tam))
        varyantlar.add(f"{tam:,}".replace(",", "."))
        if tam >= 1000 and tam % 1000 == 0:
            varyantlar.add(f"{tam // 1000} bin")
    ondalik = f"{deger:g}"
    varyantlar.add(ondalik)
    varyantlar.add(ondalik.replace(".", ","))
    return varyantlar


def sayi_konumlari(deger: float, metin: str) -> list[tuple[int, int]]:
    if deger != deger:
        return []
    konumlar = []
    for v in _varyantlar(deger):
        desen = re.compile(_SINIR_ON + re.escape(v) + _SINIR_SON)
        konumlar.extend((e.start(), e.end()) for e in desen.finditer(metin))
    return konumlar


_BAGLAM_KURALLARI: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "kar_payi_orani": (
        ("kâr pay", "kar pay", "paylaşım", "oran"),
        ("mil", "puan", "indirim", "iskonto", "bonus", "komisyon",
         "hediye", "çekiliş", "iade", "ödül"),
    ),
    "finansman_tutari": (
        ("finansman", "kredi", "limit", "destek"),
        ("açıl", "para yatırma", "para çekme", "mil", "puan", "hediye",
         "bonus", "iade", "parafpara", "kredi kart"),
    ),
    "odul_tip": (
        ("hediye", "ödül", "odul", "bonus", "puan", "mil", "çek", "kazan"),
        ("finansman", "kredi"),
    ),
    "taksit_sayisi": (("taksit",), ("ötele", "ertele", "ödemesiz")),
    "vade_ay": (("vade",), ("vade fark", "ötele", "ertele", "ödemesiz")),
}

_PENCERE_GENISLIGI = 60


def baglam_uygun_mu(alan: str, konumlar: list[tuple[int, int]], metin: str) -> bool:
    pozitifler, negatifler = _BAGLAM_KURALLARI.get(alan, ((), ()))
    if not pozitifler:
        return True
    kucuk = metin.lower()
    for bas, bit in konumlar:
        pencere = kucuk[max(0, bas - _PENCERE_GENISLIGI): bit + _PENCERE_GENISLIGI]
        if (any(p in pencere for p in pozitifler)
                and not any(n in pencere for n in negatifler)):
            return True
    return False


_GECERLI_KITLELER = {"yeni_musteri", "mevcut_musteri", "maas_musterisi", "segment"}

_SEGMENT_KANITI = re.compile(
    r"esnaf|çiftçi|kobi|şah[ıi]s\s+firma|işletme\s+sahi|işletmelere|işletmeniz"
    r"|emekli|öğrenci|maaş|genç\w*\s+özel|kadın\w*\s+özel", re.IGNORECASE)

SORULABILIR_ALANLAR = list(ALAN_SEMASI) + ["hedef_kitle"]


def _llm_api_json(prompt: str) -> dict | None:
    """OpenAI Uyumlu Chat Completions API'sine istek atıp JSON yanıtı döndürür."""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Sen yalnızca JSON formatında yanıt veren bir asistansın."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}  # JSON yanıt zorlaması
    }

    try:
        cevap = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=ZAMAN_ASIMI,
        )

        if cevap.status_code != 200:
            print(f"    LLM API Hatası Status Code: {cevap.status_code}")
            return None

        veri = cevap.json()
        raw_response = veri["choices"][0]["message"]["content"].strip()

        if not raw_response:
            return None

        # Doğrudan parse etmeyi dene
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        # Hata durumunda CoT düşünce bloklarını veya markdown formatlarını temizle
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
    """Eksik alanları LLM API'ye sorar; doğrulamadan geçenleri döndürür."""
    if not metin:
        return {}
    bulgular: dict[str, AlanBulgusu] = {}

    # --- 1. istek: sayısal çıkarım ----------------------------------------
    sayisal_alanlar = [a for a in istenen_alanlar if a in ALAN_SEMASI]
    if sayisal_alanlar:
        ham_json = _llm_api_json(_prompt_kur(metin, sayisal_alanlar)) or {}
        for alan in sayisal_alanlar:
            deger = ham_json.get(alan)
            if deger is None:
                continue
            try:
                sayi = float(deger)
            except (TypeError, ValueError):
                continue
            konumlar = sayi_konumlari(sayi, metin)
            if not konumlar:
                print(f"    LLM RED (sayı sınırı): {alan}={sayi} metinde bağımsız sayı olarak yok")
                continue
            if alan in ("vade_ay", "taksit_sayisi"):
                konumlar = [(b, s) for b, s in konumlar
                            if not re.match(r"\s*(tl\b|₺)", metin[s:s + 4], re.IGNORECASE)]
                if not konumlar:
                    print(f"    LLM RED (para değeri): {alan}={sayi} yalnız TL tutarı olarak geçiyor")
                    continue
                ust = 60 if alan == "taksit_sayisi" else 360
                if not 1 <= sayi <= ust:
                    print(f"    LLM RED (makullük): {alan}={sayi} olası aralık dışı (1-{ust})")
                    continue
            if not baglam_uygun_mu(alan, konumlar, metin):
                print(f"    LLM RED (bağlam): {alan}={sayi} çevresinde alan kanıtı yok")
                continue
            if alan in ("vade_ay", "taksit_sayisi"):
                sayi = int(sayi)
            bulgular[alan] = AlanBulgusu(sayi, f"LLM cikarimi (metinde dogrulandi): {deger}",
                                         f"llm:{MODEL}")

    # --- 2. istek: hedef kitle sınıflandırması -----------------------------
    if "hedef_kitle" in istenen_alanlar:
        ham_json = _llm_api_json(_siniflandirma_promptu(metin)) or {}
        deger = ham_json.get("hedef_kitle")
        if deger in _GECERLI_KITLELER:
            if deger == "segment" and not _SEGMENT_KANITI.search(metin):
                print("    LLM RED (segment kanıtı): metinde segment kelimesi yok")
            else:
                bulgular["hedef_kitle"] = AlanBulgusu(
                    deger, f"LLM siniflandirmasi: {deger}", f"llm:{MODEL}")

    return bulgular