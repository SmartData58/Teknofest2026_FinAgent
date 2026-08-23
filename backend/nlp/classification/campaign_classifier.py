import re
from dataclasses import dataclass

# EKSİK OLAN SINIFI BURAYA EKLEDİK (Dışarıdan import etmesine gerek kalmadı)
@dataclass
class AlanBulgusu:
    deger: str
    ham: str
    kural: str

GECERLI_TURLER = {
    "ihtiyac_finansmani",
    "konut_finansmani",
    "tasit_finansmani",
    "finansman_diger",
    "yeni_musteri",
    "mgm_kampanyasi",
    "yatirim_urunu",
    "alisveris_puani",
    "kart_kampanyasi",
}

_R = re.IGNORECASE
_ERKEN_KARAKTER = 250

import re


_KURALLAR: tuple[tuple[str, str, re.Pattern], ...] = (
    # --- FİNANSMAN KAMPANYALARI ---
    (
        "ihtiyac_finansmani",
        "hepsi",
        re.compile(r"ihtiya[çc]\s+(finansman|kart|kredi)", _R),
    ),
    (
        "konut_finansmani",
        "hepsi",
        re.compile(r"(konut|ev)\s+(finansman|kredi)|mortgage", _R),
    ),
    (
        "tasit_finansmani",
        "hepsi",
        re.compile(r"(ta[şs][ıi]t|ara[çc]|oto)\s+(finansman|kredi)", _R),
    ),
    (
        "finansman_diger",
        "hepsi",
        re.compile(
            r"\b(?!(?:ihtiya[çc]|konut|ev|ta[şs][ıi]t|ara[çc]|oto)\b)\w+\s+finansman\b|\bfinansman\b(?<!ihtiyaç finansman)(?<!konut finansman)",
            _R,
        ),
    ),
    # --- KAZANIM & BAĞLILIK KAMPANYALARI ---
    (
        "mgm_kampanyasi",
        "hepsi",
        re.compile(
            r"arkada[şs][ıi]n[ıi]\s+(?:davet\s+et|getir)"
            r"|arkada[şs][ıi]n[ıi]z[ıi]\s+(?:davet\s+edin|getirin)"
            r"|arkada[şs]\w*\s+getir\w*"
            r"|arkada[şs]\w*\s+davet\s+et\w*"
            r"|yak[ıi]n[ıi]n[ıi]\s+davet\s+et\w*"
            r"|yak[ıi]n[ıi]n[ıi]z[ıi]\s+davet\s+edin"
            r"|davet\s+et(?:tiğin|tiğiniz)?\s+arkada[şs]"
            r"|referans\s+(?:kod|link|bağlant)"
            r"|referans[ıi]n\w*\s+ile"
            r"|getir\s+kazan",
            _R,
        ),
    ),
    (
        "yeni_musteri",
        "baslik",
        re.compile(
            r"mü[şs]teri(si|miz)?\s+ol|yeni\s+.*mü[şs]teri"
            r"|ho[şs]\s*geldin|gelenlere|(türklü|finanslı|katılımlı)\s+ol",
            _R,
        ),
    ),
    # --- YATIRIM & TASARRUF ---
    ("yatirim_urunu", "baslik", re.compile(r"günlük\s+hesap", _R)),
    (
        "yatirim_urunu",
        "erken",
        re.compile(
            r"kat[ıi]l[ıi]?ma?\s+hesab|yat[ıi]r[ıi]m\s+hesab"
            r"|\bbes\b|emeklilik\s+plan|döviz|\bfx\b"
            r"|k[ıi]ymetli\s+maden|gümü[şs]|alt[ıi]n\s+hesab"
            r"|getiri\s+oran|payla[şs][ıi]m\s+oran|kur\s+f[ıi]rsat"
            r"|benzersiz\s+kur|dar\s+makas",
            _R,
        ),
    ),
    # --- HARCAMA & KART KAMPANYALARI ---
    (
        "alisveris_puani",
        "erken",
        re.compile(
            r"parafpara|worldpuan|puan|\bmil\b|mil'e|\biade\b|bonus"
            r"|kazand[ıi]ran|(harcad[ıi]k[çc]a|yapt[ıi]k[çc]a)\s+kazan",
            _R,
        ),
    ),
    
    (
        "kart_kampanyasi",
        "hepsi",
        re.compile(
            r"^(?!.*(?:mü[şs]teri\s+ol|ho[şs]\s*geldin|davet|referans)).*"
            r"(?:taksit|indirim|\bkartl?a?\b|kredi\s+kart|debit|troy|mastercard|visa"
            r"|qr\s+öde|harcama|biz\s+kart|sağlam\s+kart|happy\s+card|albaraka\s+world|vkard|berekett?card)",
            _R,
        ),
    ),
)

_SORU_TURLERI = ("ihtiyac_finansmani", "konut_finansmani", "tasit_finansmani")

def urun_turu_sorusu(soru: str) -> str | None:
    for tur, _, desen in _KURALLAR:
        if tur in _SORU_TURLERI and desen.search(soru or ""):
            return tur
    return None

def kuralla_siniflandir(baslik: str, metin: str) -> AlanBulgusu | None:
    for tur, kapsam, desen in _KURALLAR:
        hedef = baslik or ""
        if kapsam == "erken":
            hedef = f"{baslik or ''} . {(metin or '')[:_ERKEN_KARAKTER]}"
        elif kapsam == "hepsi":
            hedef = f"{baslik or ''} . {metin or ''}"
        e = desen.search(hedef)
        if e:
            cevre = hedef[max(0, e.start() - 30): e.end() + 30].strip()
            return AlanBulgusu(tur, f"...{cevre}...", f"tur_kurali:{tur}")
    return None

def llm_ile_siniflandir(baslik: str, metin: str) -> AlanBulgusu | None:
    # Test ortamı için LLM kapalı varsayıyoruz. 
    # Gerçek entegrasyonda burası Qwen vb. bir modele istek atacaktır.
    return None

def siniflandir(baslik: str, metin: str, llm_aktif: bool = True) -> AlanBulgusu | None:
    bulgu = kuralla_siniflandir(baslik, metin)
    if bulgu is None and llm_aktif:
        bulgu = llm_ile_siniflandir(baslik, metin)
    return bulgu