import json
import os
import re
from typing import Any
import requests

from .rule_based import AlanBulgusu

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
LLM_GUVEN = 0.70
ZAMAN_ASIMI = 300  # 5 dk

# --- 1. TÜM ALAN ŞEMALARI VE VERİ TİPLERİ ---
TUM_ALAN_SEMALARI: dict[str, dict[str, Any]] = {
    "kar_orani": {
        "schema": '"kar_orani": sayı|null (Finansman kâr payı veya katılma hesabı kâr paylaşım oranı, örn: 1.89)',
        "type": "float",
        "birim": "percent",
    },
    "vade": {
        "schema": '"vade": tamsayı|null (Finansman/kredi için AY cinsinden toplam vade süresi)',
        "type": "int",
        "birim": "ay",
    },
    "taksit_sayisi": {
        "schema": '"taksit_sayisi": tamsayı|null (Doğrudan uygulanan taksit sayısı)',
        "type": "int",
        "birim": "adet",
    },
    "finansman_tutari": {
        "schema": '"finansman_tutari": sayı|null (Kredi/finansman üst limiti, TL cinsinden)',
        "type": "float",
        "birim": "TL",
    },
    "odul_tutari": {
        "schema": '"odul_tutari": sayı|null (TL cinsinden hediye/bonus/iade/puan tutarı)',
        "type": "float",
        "birim": "TL",
    },
    "minimum_harcama": {
        "schema": '"minimum_harcama": sayı|null (Kampanyaya katılmak için gereken min harcama tutarı)',
        "type": "float",
        "birim": "TL",
    },
    "indirim_orani": {
        "schema": '"indirim_orani": sayı|null (Uygulanan indirim/iskonto yüzdesi, örn: 20)',
        "type": "float",
        "birim": "percent",
    },
    "ana_kategori": {
        "schema": '"ana_kategori": string|null ("Finansman", "Sektörel Ödül", "Kart Kampanyası", "Diğer")',
        "type": "string",
        "birim": "metin",
    },
    "alt_kategori": {
        "schema": '"alt_kategori": string|null ("tasit_finansmani", "konut_finansmani", "ihtiyac_finansmani", "gida_restoran", "seyahat_turizm", "egitim", "saglik", "diger")',
        "type": "string",
        "birim": "metin",
    },
    "hedef_kitle": {
        "schema": '"hedef_kitle": list|null (["yeni_musteri"], ["mevcut_musteri"], ["maas_musterisi"], ["kobi_esnaf"], ["emekli"])',
        "type": "list",
        "birim": "metin",
    },
}

_GECERLI_KITLELER = {"yeni_musteri", "mevcut_musteri", "maas_musterisi", "kobi_esnaf", "emekli"}
_SEGMENT_KANITI = re.compile(
    r"esnaf|çiftçi|kobi|şah[ıi]s\s+firma|işletme\s+sahi|emekli|öğrenci|maaş",
    re.IGNORECASE,
)


# MAVİ İLE GÖSTERİLEN KISMI BULUN:
def llm_hazir():
    try:
        # Sabit URL yerine tanımlı OLLAMA_URL değişkenini kullanın
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"DEBUG - Ollama Hatası: {e}") 
        print("⚠️ UYARI: Ollama/Model erişilemez — Sadece kural tabanlı modda çalışılıyor.")
        return False


def _tekil_prompt_kur(metin: str, istenen_alanlar: list[str]) -> str:
    """LLM için sıkı kuralları olan ve doğrudan JSON çıktısına zorlayan prompt üretir."""
    sema_satirlari = [
        TUM_ALAN_SEMALARI[a]["schema"]
        for a in istenen_alanlar
        if a in TUM_ALAN_SEMALARI
    ]
    sema_str = ",\n  ".join(sema_satirlari)

    return (
        "SADECE ve SADECE geçerli bir JSON nesnesi döndür. Açıklama, düşünce adımı veya selamlama YAZMA.\n"
        "Doğrudan { karakteri ile başla ve } karakteri ile bitir.\n"
        "KURALLAR:\n"
        "1. Metinde AÇIKÇA geçmeyen bilgiye null yaz. Kesinlikle tahmin etme.\n"
        "2. Sayısal değerleri saf sayıya dönüştür (%1,89 -> 1.89, 50 bin -> 50000).\n"
        f"Şu JSON şemasını birebir uygula:\n{{\n  {sema_str}\n}}\n\n"
        f"METİN: {metin}\n\nJSON:"
    )


def _json_temizle_ve_ayristir(ham_metin: str) -> dict | None:
    """Metin içi bozuklukları regex ile temizleyip JSON nesnesine dönüştürür."""
    if not ham_metin:
        return None

    # 1. Qwen 3.5 düşünce bloklarını (<think>...</think>) temizle
    metin = re.sub(r"<think>.*?</think>", "", ham_metin, flags=re.DOTALL).strip()

    # 2. Markdown kod bloklarını temizle (```json ... ```)
    metin = re.sub(r"^```(?:json)?\s*", "", metin, flags=re.IGNORECASE)
    metin = re.sub(r"\s*```$", "", metin)

    # 3. Sadece en dıştaki JSON süslü parantezlerini { ... } yakala
    json_match = re.search(r"\{.*\}", metin, re.DOTALL)
    if json_match:
        metin = json_match.group(0)

    # 4. Yaygın LLM sözdizimi hatalarını düzelt:
    # Trailing comma (nesne/liste sonundaki fazla virgül): {"a": 1, } -> {"a": 1}
    metin = re.sub(r",\s*([\}\]])", r"\1", metin)

    # 5. Ayrıştırmayı dene
    try:
        return json.loads(metin)
    except json.JSONDecodeError:
        print(f"    ⚠️ LLM Temizlenemeyen JSON Üretti: {metin[:120]}...")
        return None


def _ollama_json(prompt: str) -> dict | None:
    """Ollama API'sine istek atar ve temizlenmiş yanıtı döndürür."""
    try:
        cevap = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 4096,
                },
                "keep_alive": -1,
            },
            timeout=ZAMAN_ASIMI,
        )
        
        # --- TEŞHİS İÇİN EKLENEN SATIRLAR ---
        #print(f"\n[DEBUG] HTTP Status Code: {cevap.status_code}")
        #print(f"[DEBUG] Ham API Yanıtı: {cevap.text[:300]}")
        # -------------------------------------


        # DOĞRU (Olması gereken satır):
        json_data = cevap.json()
        ham_yanit = (json_data.get("response") or json_data.get("thinking") or "").strip()

        return _json_temizle_ve_ayristir(ham_yanit)
            

    except requests.RequestException as hata:
        print(f"    LLM Bağlantı Hatası ({hata.__class__.__name__}) — atlanıyor.")
        return None

def llm_ile_cikar(metin: str, istenen_alanlar: list[str]) -> dict[str, AlanBulgusu]:
    """
    Kural tabanlı sistemin çıkaramadığı eksik alanları LLM'e tek bir istekte sorar,
    doğrulama adımlarından geçenleri AlanBulgusu olarak döndürür.
    """
    if not metin or not istenen_alanlar:
        return {}

    bulgular: dict[str, AlanBulgusu] = {}
    sorgulanacaklar = [a for a in istenen_alanlar if a in TUM_ALAN_SEMALARI]

    if not sorgulanacaklar:
        return {}

    prompt = _tekil_prompt_kur(metin, sorgulanacaklar)
    ham_json = _ollama_json(prompt) or {}

    for alan in sorgulanacaklar:
        deger = ham_json.get(alan)
        if deger is None or str(deger).lower() in ("null", "none", ""):
            continue

        meta = TUM_ALAN_SEMALARI[alan]
        veri_tipi = meta["type"]
        birim = meta["birim"]

        # --- A. SAYISAL ALAN DOĞRULAMASI ---
        if veri_tipi in ("float", "int"):
            try:
                sayi = float(deger)
                if veri_tipi == "int":
                    sayi = int(sayi)
            except (TypeError, ValueError):
                continue

            # Hallucination Kontrolü: Sayı metinde gerçekten var mı?
            str_sayi = str(int(sayi)) if isinstance(sayi, int) or sayi.is_integer() else str(sayi)
            match = re.search(r"\b" + re.escape(str_sayi) + r"\b", metin)
            
            start_pos, end_pos = (match.start(), match.end()) if match else (None, None)

            bulgular[alan] = AlanBulgusu(
                deger=sayi,
                ham_metin=str(deger),
                kural="llm_extraction",
                yontem="llm",
                guven=LLM_GUVEN,
                kanit_metni=metin[max(0, (start_pos or 0) - 30): (end_pos or 0) + 30] if match else metin[:100],
                baslangic_konum=start_pos,
                bitis_konum=end_pos,
                birim=birim,
            )

        # --- B. LİSTE / HEDEF KİTLE DOĞRULAMASI ---
        elif veri_tipi == "list" and alan == "hedef_kitle":
            kitleler = [deger] if isinstance(deger, str) else deger
            gecerli_kitleler = [k for k in kitleler if k in _GECERLI_KITLELER]

            if "kobi_esnaf" in gecerli_kitleler and not _SEGMENT_KANITI.search(metin):
                print("    LLM RED (segment kanıtı yok): Metinde esnaf/KOBİ kelimesi bulunamadı.")
                continue

            if gecerli_kitleler:
                bulgular[alan] = AlanBulgusu(
                    deger=gecerli_kitleler,
                    ham_metin=json.dumps(gecerli_kitleler),
                    kural="llm_classification",
                    yontem="llm",
                    guven=LLM_GUVEN,
                    kanit_metni=metin[:120],
                    birim=birim,
                )

        # --- C. METİNSEL ALAN DOĞRULAMASI ---
        elif veri_tipi == "string":
            str_val = str(deger).strip()
            bulgular[alan] = AlanBulgusu(
                deger=str_val,
                ham_metin=str_val,
                kural="llm_extraction",
                yontem="llm",
                guven=LLM_GUVEN,
                kanit_metni=str_val,
                birim=birim,
            )

    return bulgular