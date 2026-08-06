import json
import os
import re

import requests

from backend.nlp.extraction.rule_based import AlanBulgusu

OLLAMA_URL = os.environ.get("FINAGENT_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("FINAGENT_LLM_MODEL", "qwen2.5:7b")
LLM_GUVEN = 0.7
ZAMAN_ASIMI = 300 # 5dk

ALAN_SEMASI = {
    "kar_payi_orani": (
        '"kar_payi_orani": sayı|null  '
        "(finansman kâr payı veya katılma hesabı kâr paylaşım oranı, örn 1.89. "
        "DİKKAT: mil/puan kazanım oranı, indirim oranı ve komisyon oranı "
        "kâr payı DEĞİLDİR — bunlar için null yaz)"
    ),
    "vade_ay": (
    '"vade_ay": tamsayı|null  '
    '(Finansman/kredi için AY cinsinden toplam vade süresi. Yıl verilmişse 12 ile çarp. '
    'DİKKAT: Ödemesiz dönem süresi, öteleme/erteleme ay sayısı vade DEĞİLDİR)'
    ),
    "taksit_sayisi": (
    '"taksit_sayisi": tamsayı|null  '
    '(Yalnızca metinde doğrudan uygulanan taksit sayısı. '
    'DİKKAT: Erteleme/öteleme ay sayısı, kampanya süresi veya ek taksit sayısı '
    'asıl taksit sayısı DEĞİLDİR)'
    ),
    "finansman_tutari": (
        '"finansman_tutari": sayı|null  '
        "(Bankanın sağladığı kredi/finansman üst limiti. "
        "DİKKAT: Minimum harcama/sepet tutarı, hesap açılış alt limiti, "
        "ATM çekim/yatırma limiti ve hediye tutarları finansman DEĞİLDİR)"
    ),
    "odul_miktari": (
    '"odul_miktari": sayı|null  '
    "(TL cinsinden hediye/çek/bonus/iade/puan tutarı. Örn: 500. "
    "DİKKAT: Mil adedi, gram altın miktarı veya yüzde oranları ödül miktarı DEĞİLDİR. "
    "Finansman tutarı veya taksit öteleme tutarı ödül DEĞİLDİR)"
    ),
}


def llm_hazir() -> bool:
    """Ollama ve modelin yüklü değilse sistem çökmez, sorunu söyler"""
    try:
        cevap = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return any(m["name"].startswith(MODEL.split(":")[0])
                   for m in cevap.json().get("models", []))
    except requests.RequestException:
        return False
    
def _prompt_kur(metin: str, istenen_alanlar: list[str]) -> str:
    """Yalnızca EKSİK sayısal alanları soran dar kapsamlı prompt üretir.

    Neden dar kapsam? (1) Kısa çıktı = CPU'da hız, (2) modelin işi ne kadar
    dar tanımlanırsa doğruluk o kadar yüksek, (3) kuralın bulduğu alanı
    LLM'e tekrar sormak gereksiz risk.
    """
    sema = ",\n  ".join(ALAN_SEMASI[a] for a in istenen_alanlar)
    return (
        "Türkçe katılım bankası kampanya metninden bilgi çıkarıyorsun.\n"
        "KURALLAR:\n"
        "- SADECE metinde açıkça yazan bilgileri doldur.\n"
        "- Metinde olmayan bilgiye null yaz. ASLA tahmin etme.\n"
        "- Sayıları Türkçe biçimden çevir: %1,89 → 1.89 | 50.000 TL → 50000 | 3 bin -> 3000 \n"
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
    """Bir sayının metinde geçebilecek Türkçe/İngilizce yazımları.

      1.89   → "1.89" | "1,89"
      50000  → "50000" | "50.000" | "50 bin"
    """
    varyantlar = set()
    if deger == int(deger):
        tam = int(deger)
        varyantlar.add(str(tam))                                  # 50000
        varyantlar.add(f"{tam:,}".replace(",", "."))              # 50.000
        if tam >= 1000 and tam % 1000 == 0:
            varyantlar.add(f"{tam // 1000} bin")                  # 50 bin
    ondalik = f"{deger:g}"                                        # 1.89
    varyantlar.add(ondalik)
    varyantlar.add(ondalik.replace(".", ","))                     # 1,89
    return varyantlar


def sayi_konumlari(deger: float, metin: str) -> list[tuple[int, int]]:
    """Halüsinasyon kalkanı 1. basamak: değerin metindeki SINIR-DOĞRU
    eşleşme konumlarını döndürür. Boş liste = değer metinde bağımsız bir
    sayı olarak YOK → uydurma kabul edilir.

    Konumlar döndürülür (bool değil) çünkü 2. basamak (bağlam doğrulaması)
    aynı konumların çevresine bakacak — iki kez arama yapılmaz.
    """
    if deger != deger:  # NaN koruması
        return []
    konumlar = []
    for v in _varyantlar(deger):
        desen = re.compile(_SINIR_ON + re.escape(v) + _SINIR_SON)
        konumlar.extend((e.start(), e.end()) for e in desen.finditer(metin))
    return konumlar


# Listeler 15. adım ölçümündeki 19 gerçek hatadan türetildi:
#   "%5 ekstra mil"        → kâr payı sanılmıştı  → "mil" negatif
#   "650 TL BES bonusu"    → kâr payı sanılmıştı  → "bonus" negatif
#   "hesap açılış tutarı"  → finansman sanılmıştı → "açıl" negatif
#   "para yatırma limiti"  → finansman sanılmıştı → "para yatırma" negatif
_BAGLAM_KURALLARI: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "kar_payi_orani": (
        ("kâr pay", "kar pay", "paylaşım", "oran", "maliyet oranı", "kar oranı"),
        ("mil", "puan", "indirim", "iskonto", "bonus", "komisyon",
         "hediye", "çekiliş", "iade", "ödül"),
    ),
    "finansman_tutari": (
        ("finansman", "kredi", "limit", "destek"),
        ("açıl", "para yatırma", "para çekme", "mil", "puan", "hediye",
         "bonus", "iade", "parafpara", "kredi kart", "harcama", "sepet"),
    ),
    "odul_miktari": (
        ("hediye", "ödül", "odul", "bonus", "puan", "mil", "çek", "kazan"),
        ("finansman", "kredi"),
    ),
    "taksit_sayisi": (("taksit",), ("ötele", "ertele", "ödemesiz")),
    "vade_ay": (("vade",), ("vade fark", "ötele", "ertele", "ödemesiz")),
}

_PENCERE_GENISLIGI = 60


def baglam_uygun_mu(alan: str, konumlar: list[tuple[int, int]], metin: str) -> bool:
    """Konumlardan en az biri alanın bağlam kurallarını sağlıyor mu?"""
    pozitifler, negatifler = _BAGLAM_KURALLARI.get(alan, ((), ()))
    if not pozitifler:  # bağlam kuralı tanımsız alan → yalnız 1. basamak yeter
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


def _ollama_json(prompt: str) -> dict | None:
    """Ollama'ya tek istek atar, JSON cevabı döndürür (hata → None)."""
    try:
        cevap = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",                    # geçerli JSON zorunlu
                "options": {"temperature": 0,        # uydurma kapalı
                            "num_ctx": 4096},
                "keep_alive": "30m",                 # batch boyunca modeli RAM'de tut
            },
            timeout=ZAMAN_ASIMI,
        )
        return json.loads(cevap.json()["response"])
    except (requests.RequestException, json.JSONDecodeError, KeyError) as hata:
        print(f"    LLM atlandı ({hata.__class__.__name__}) — kural bulgularıyla devam")
        return None


def llm_ile_cikar(metin: str, istenen_alanlar: list[str]) -> dict[str, AlanBulgusu]:
    """Eksik alanları lokal LLM'e sorar; doğrulamadan geçenleri döndürür.

    İki ayrı görev, iki ayrı istek (gerekçe: _siniflandirma_promptu notu):
      1. sayısal ÇIKARIM (ALAN_SEMASI alanları) → iki basamaklı kalkan
      2. hedef_kitle SINIFLANDIRMASI → kapalı liste doğrulaması

    Ollama'ya ulaşılamazsa/parse hatasında BOŞ sözlük döner — pipeline
    kural bulgularıyla yoluna devam eder (zarif geri düşüş / graceful
    degradation: LLM bir zenginleştirme katmanı, tek hata noktası değil).
    """
    if not metin:
        return {}
    bulgular: dict[str, AlanBulgusu] = {}

    # --- 1. istek: sayısal çıkarım ----------------------------------------
    sayisal_alanlar = [a for a in istenen_alanlar if a in ALAN_SEMASI]
    if sayisal_alanlar:
        ham_json = _ollama_json(_prompt_kur(metin, sayisal_alanlar)) or {}
        for alan in sayisal_alanlar:
            deger = ham_json.get(alan)
            if deger is None:
                continue  # model "metinde yok" dedi — doğru davranış, alan boş kalır
            # Tip zorlama + iki basamaklı halüsinasyon kalkanı
            try:
                sayi = float(deger)
            except (TypeError, ValueError):
                continue
            konumlar = sayi_konumlari(sayi, metin)
            if not konumlar:
                print(f"    LLM RED (sayı sınırı): {alan}={sayi} metinde bağımsız sayı olarak yok")
                continue
            if alan in ("vade_ay", "taksit_sayisi"):
                # PARA değeri adet/süre olamaz (k36 denetim bulgusu, 2026-07-17):
                # "toplam 2.000 TL bonus ... taksitli harcamalar dahildir"
                # cümlesinde pencereye giren "taksit" kelimesi kalkanı delmiş,
                # taksit_sayisi=2000 yazılmıştı. Eşleşmenin hemen ardında
                # TL/₺ varsa o konum tutar demektir, aday listeden düşer.
                konumlar = [(b, s) for b, s in konumlar
                            if not re.match(r"\s*(tl\b|₺)", metin[s:s + 4],
                                            re.IGNORECASE)]
                if not konumlar:
                    print(f"    LLM RED (para değeri): {alan}={sayi} yalnız TL tutarı olarak geçiyor")
                    continue
                # Makullük sınırı (ikinci kemer): taksit/vade alanları için
                # alan bilgisi — 60 taksit / 360 ay üstü değer gerçek dünyada
                # kampanya değil, çıkarım hatasıdır.
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
        ham_json = _ollama_json(_siniflandirma_promptu(metin)) or {}
        deger = ham_json.get("hedef_kitle")
        # Kapalı liste doğrulaması: 4 etiket dışındaki her şey çöp
        if deger in _GECERLI_KITLELER:
            if deger == "segment" and not _SEGMENT_KANITI.search(metin):
                print("    LLM RED (segment kanıtı): metinde segment kelimesi yok")
            else:
                bulgular["hedef_kitle"] = AlanBulgusu(
                    deger, f"LLM siniflandirmasi: {deger}", f"llm:{MODEL}")

    return bulgular
