# =============================================================================
# intent.py — Niyet Tespiti, Statik Yanıtlar ve RAG Prompt Yönetimi
# =============================================================================

import re
from dataclasses import dataclass, field
from typing import Sequence, Optional

# -----------------------------------------------------------------------------
# 1. LLM PROMPT VE STATİK CEVAP Mimarisi
# -----------------------------------------------------------------------------

RAG_CEVAP_PROMPTU = """Sen yetenekli bir yapay zeka finans asistanısın.
KURALLAR:
- SADECE aşağıdaki kampanya bilgilerine dayanarak cevap ver.
- Bilgi kampanya metinlerinde yoksa açıkça "elimdeki kampanya verilerinde bu bilgi yok" de. ASLA tahmin etme, sayı uydurma.
- Hangi bankanın hangi kampanyasından bahsettiğini belirt.
- Aşağıda "GEÇMİŞ KONUŞMA" varsa, konuşmanın bağlamını (hangi bankadan/kampanyadan bahsedildiğini) dikkate al.
- {dil_kurali}
- {mod_kurali}
- Sorular yatırım tavsiyesi isterse: kampanya bilgisi verdiğini, tavsiye veremeyeceğini söyle.

KAMPANYA BİLGİLERİ:
{baglam}

{gecmis}SORU: {soru}

CEVAP:"""

STATIK_CEVAP: dict[str, str] = {
    "selamlama": "Merhaba! Katılım bankacılığı kampanyaları ve finansman ürünleri hakkında nasıl yardımcı olabilirim?",
    "hal_hatir": "Teşekkür ederim, size yardımcı olmak için buradayım. Hangi kampanya veya banka hakkında bilgi almak istersiniz?",
    "tesekkur": "Rica ederim, her zaman yardımcı olmaktan mutluluk duyarım. Başka bir konuda sorunuz var mı?",
    "vedalasma": "İyi günler dilerim. Yeniden görüşmek üzere!",
    "yetenekler": "Kampanyaları bankaya göre listeleyebilir, en düşük kar payı veya en yüksek ödül gibi karşılaştırmalar yapabilir, taksit hesabı yapabilir ve kampanya detaylarını açıklayabilirim.",
    "tavsiye_red": "Ben bir yapay zeka asistanıyım ve yatırım/finansal tavsiye veremem. Ancak bankaların güncel kampanya, oran ve masraf bilgilerini sizin için karşılaştırıp listeleyebilirim.",
}

# -----------------------------------------------------------------------------
# 2. TÜRKÇE MAPPING VE BANKA TANIMLARI
# -----------------------------------------------------------------------------

TR_LOWER_MAP = str.maketrans({"İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç"})

def tr_lower(text: str) -> str:
    """Türkçe karakterleri 'İ'->'i' ve 'I'->'ı' mantığıyla doğru küçük harfe çevirir."""
    return text.translate(TR_LOWER_MAP).lower() if text else ""

BANKA_TAKMA_ADLARI: dict[str, tuple[str, ...]] = {
    "albaraka": ("albaraka",),
    "kuveytturk": ("kuveyt türk", "kuveyt turk", "kuveyttürk", "kuveytturk", "kuveyt"),
    "turkiye_finans": ("türkiye finans", "turkiye finans"),
    "vakif_katilim": ("vakıf katılım", "vakif katilim", "vakıf katilim"),
    "ziraat_katilim": ("ziraat katılım", "ziraat katilim", "ziraat"),
    "emlak_katilim": ("emlak katılım", "emlak katilim", "emlakbank", "emlak"),
    "hayat_finans": ("hayat finans", "hayatfinans"),
    "dunya_katilim": ("dünya katılım", "dunya katilim", "dünya katilim"),
    "tom_katilim": ("tom katılım", "tom katilim", "tom bank", "t.o.m"),
    "adil_katilim": ("adil katılım", "adil katilim"),
}

_BANKA_PATTERNS: list[tuple[str, re.Pattern]] = []
for kod, takmalar in BANKA_TAKMA_ADLARI.items():
    for takma in sorted(takmalar, key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(takma)}\b", re.IGNORECASE)
        _BANKA_PATTERNS.append((kod, pattern))

# -----------------------------------------------------------------------------
# 3. STATİK SOSYAL VE GÜVENLİK REGEX KALIPLARI
# -----------------------------------------------------------------------------

_STATIK_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("selamlama", re.compile(r"^\s*(merhaba|merhabalar|meraba|mrhb|selam|selamlar|slm|sa|s\.a|selamun\s+aleykum|selamün\s+aleyküm|günaydın|gunaydin|hayırlı\s+sabahlar|iyi\s+(günler|gunler|akşamlar|aksamlar|geceler))\b", re.IGNORECASE)),
    ("hal_hatir", re.compile(r"^\s*(nasılsın|nasilsin|nasilsiniz|naber|n'aber|ne\s+haber|iyi\s+misin|iyi\s+misiniz|nasıl\s+gidiyor|napıyorsun|napyosun|ne\s+yapıyorsun)\b", re.IGNORECASE)),
    ("tesekkur", re.compile(r"^\s*(teşekkür|tesekkur|teşekkürler|tesekkurler|teşekkür\s+ederim|tesekkur\s+ederim|sağol|sagol|saol|eyvallah|eyv|harikasın|supersin|süpersin)\b", re.IGNORECASE)),
    ("vedalasma", re.compile(r"^\s*(görüşürüz|gorusuruz|baybay|bye|hoşça\s+kal|hoscakal|iyi\s+çalışmalar|iyi\s+calismalar|kolay\s+gelsin|tamamdır|tamamdir|anladım|anladim)\b", re.IGNORECASE)),
    ("yetenekler", re.compile(r"^\s*(kimsin|sen\s+kimsin|ne\s+işe\s+yarıyorsun|ne\s+ise\s+yariyorsun|ne\s+yapabilirsin|yardım\s+et|yardim|nereden\s+başlamalıyım)\b", re.IGNORECASE)),
)

_TAVSIYE = re.compile(
    r"tavsiye|öner(ir|sen|in)|mal[ıi]\s*m[ıi]y[ıi]m|mal[ıi]y[ıi]m\b"
    r"|meli\s*miyim|mant[ıi]kl[ıi]\s*m[ıi]|de[ğg]er\s*mi\b|do[ğg]ru\s+olur\s+mu",
    re.IGNORECASE)

_KARSILASTIRMA_ALANLARI: tuple[tuple[str, re.Pattern], ...] = (
    ("tahsis_ucreti", re.compile(r"en\s+(düşük|az|ucuz)\s+(tahsis|masraf|ücret)|masrafsız", re.IGNORECASE)),
    ("kar_payi_orani", re.compile(r"en\s+(düşük|uygun|iyi|avantajlı|ucuz)\s+(kâr|kar|oran)|oranı?\s+en\s+düşük", re.IGNORECASE)),
    ("odul_miktari", re.compile(r"en\s+(yüksek|çok|fazla|büyük)\s+(ödül|iade|hediye|nakit|parafpara|puan)", re.IGNORECASE)),
    ("vade_ay", re.compile(r"en\s+(uzun|yüksek|fazla)\s+vade", re.IGNORECASE)),
    ("taksit_sayisi", re.compile(r"en\s+(çok|fazla|yüksek)\s+taksit", re.IGNORECASE)),
)

_KARSILASTIRMA_GENEL = re.compile(r"karşılaştır|kıyasla|hangi\s+banka\w*\s+daha|hangisi\s+daha", re.IGNORECASE)
_LISTE = re.compile(r"kampanyalar[ıi]?\b|hangi\s+kampanya|neler\s+var|listele|göster", re.IGNORECASE)
_HESAP_DILI = re.compile(r"taksit\w*\s+hesapla|taksit\w*\s+hesab|hesaplar\s*m[ıi]s[ıi]n|ayl[ıi]k\s+taksit|ayda\s+ne\s+kadar|ne\s+kadar\s+öde(rim|nir)|kaç\s+taksit", re.IGNORECASE)
_FINANSMAN_BAGLAMI = re.compile(r"finansman|kredi(?!\s*kart)", re.IGNORECASE)

# Taksit hesaplama sorularından tutar / vade / oran çıkarmak için kullanılır
# (bkz. hesaplama_parametreleri_cikar). STATİK_CEVAP["yetenekler"] "taksit hesabı
# yapabilirim" diyor ama bu çıkarım olmadan bu özellik hiçbir zaman tetiklenmiyordu.
_TUTAR_DESENI = re.compile(r'(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)\s*(?:tl|lira|₺)', re.IGNORECASE)
_VADE_DESENI = re.compile(r'(\d{1,3})\s*(?:ay|aylık|taksit)', re.IGNORECASE)
_ORAN_DESENI = re.compile(r'%\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*%')

_DEVAM = re.compile(r"^\s*(peki|pekala|o\s+zaman|ya\s+\S)|\bpeki\b|\bayn[ıi](s[ıi])?\b|\bonun\b|\bbunun\b|\bşunun\b|\b(o|bu|şu)\s+(kampanya|banka|hesap|plan|oran)|\bolsa(yd[ıi])?\b|\bolursa\b|\bbir\s+de\b", re.IGNORECASE)
_BANKA_SORGUSU = re.compile(r"hangi\s+banka|bankalar|başka\s+banka", re.IGNORECASE)
_VARLIK = re.compile(r"var\s*m[ıi]\b", re.IGNORECASE)
_YILLIK = re.compile(r"y[ıi]ll[ıi]k", re.IGNORECASE)

# -----------------------------------------------------------------------------
# 4. DATA CLASS & YARDIMCI FONKSİYONLAR
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Mesaj:
    rol: str      # "user" | "assistant"
    icerik: str

@dataclass
class Niyet:
    tur: str
    statik_cevap: Optional[str] = None
    banka_kodu: Optional[str] = None
    alan: Optional[str] = None
    ham_soru: str = field(default="", repr=False)
    tutar: Optional[float] = None
    vade: Optional[int] = None
    oran: Optional[float] = None
    oran_yillik: bool = False
    oran_gecmisten: bool = False
    baglam_soru: Optional[str] = field(default=None, repr=False)

def banka_bul(soru: str) -> Optional[str]:
    s = tr_lower(soru)
    for kod, pattern in _BANKA_PATTERNS:
        if pattern.search(s):
            return kod
    return None

def statik_yanit_bul(soru: str) -> Optional[str]:
    s = tr_lower(soru.strip())
    if len(s.split()) <= 5:
        for intent_name, pattern in _STATIK_PATTERNS:
            if pattern.search(s):
                return STATIK_CEVAP.get(intent_name)
    return None

_TR_BINLIK_DESENI = re.compile(r'^\d{1,3}(\.\d{3})+$')

def _sayi_ayikla(ham: str) -> float:
    """'10.000,50' / '100.000' / '50000.5' / '2,99' gibi TR/EN karışık sayı
    yazımlarını float'a çevirir. TEK BAŞINA nokta içeren "100.000" gibi bir
    yazım TR'de %99 ihtimalle binlik ayırıcıdır (100000), ondalık değil — bu
    yüzden üç haneli gruplara ayrılmış saf noktalı sayılar özel olarak ele alınır."""
    if not ham:
        return 0.0
    s = ham.strip()
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif _TR_BINLIK_DESENI.match(s):
        s = s.replace('.', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except Exception:
        return 0.0

def hesaplama_parametreleri_cikar(soru: str):
    """Taksit hesabı isteyen bir sorudan (tutar, vade, oran) çıkarmaya çalışır.
    Herhangi biri bulunamazsa None döner; çağıran taraf eksik alanları
    (özellikle oran) başka bir kaynaktan (örn. Mongo'daki güncel ortalama) tamamlayabilir."""
    tutar_m = _TUTAR_DESENI.search(soru)
    vade_m = _VADE_DESENI.search(soru)
    oran_m = _ORAN_DESENI.search(soru)
    tutar = _sayi_ayikla(tutar_m.group(1)) if tutar_m else None
    vade = int(_sayi_ayikla(vade_m.group(1))) if vade_m else None
    oran = None
    if oran_m:
        oran = _sayi_ayikla(oran_m.group(1) or oran_m.group(2))
    return tutar, vade, oran

# -----------------------------------------------------------------------------
# 5. ANA NIYET TESPIT MOTORU
# -----------------------------------------------------------------------------

def niyet_bul(soru: str, gecmis: Sequence[Mesaj] = ()) -> Niyet:
    s_tr = tr_lower(soru)
    banka = banka_bul(soru)

    statik_cevap = statik_yanit_bul(soru)
    if statik_cevap:
        return Niyet("statik", statik_cevap=statik_cevap, ham_soru=soru)

    if _TAVSIYE.search(s_tr):
        return Niyet("tavsiye", statik_cevap=STATIK_CEVAP["tavsiye_red"], banka_kodu=banka, ham_soru=soru)

    # 🧮 Taksit hesaplama: "hesapla/kaç taksit/ayda ne kadar" gibi dil kalıpları +
    # metinden çıkarılabilen en az tutar VE vade varsa doğrudan deterministik
    # hesaplamaya yönlendirilir (LLM'in sayı uydurmasına gerek kalmaz).
    if _HESAP_DILI.search(s_tr):
        tutar, vade, oran = hesaplama_parametreleri_cikar(soru)
        if tutar and vade:
            return Niyet("hesaplama", banka_kodu=banka, tutar=tutar, vade=vade, oran=oran, ham_soru=soru)

    devam = bool(gecmis) and bool(_DEVAM.search(soru))
    baglam_soru = None

    if devam:
        parcalar = [m.icerik for m in reversed(gecmis) if m.rol == "user"]
        baglam_soru = " ".join(reversed(parcalar[:2])) if parcalar else None
        if banka is None and not _BANKA_SORGUSU.search(soru):
            for m in reversed(gecmis):
                if m.rol == "user":
                    b = banka_bul(m.icerik)
                    if b:
                        banka = b
                        break

    for alan, desen in _KARSILASTIRMA_ALANLARI:
        if desen.search(soru):
            return Niyet("karsilastirma", banka_kodu=banka, alan=alan, ham_soru=soru, baglam_soru=baglam_soru)

    if _KARSILASTIRMA_GENEL.search(soru):
        return Niyet("karsilastirma", banka_kodu=banka, alan="kar_payi_orani", ham_soru=soru, baglam_soru=baglam_soru)

    if banka and _LISTE.search(soru):
        return Niyet("banka_listesi", banka_kodu=banka, ham_soru=soru, baglam_soru=baglam_soru)

    return Niyet("kampanya_soru", banka_kodu=banka, ham_soru=soru, baglam_soru=baglam_soru)


# -----------------------------------------------------------------------------
# 6. KONUŞMA GEÇMİŞİ FORMATLAYICI (RAG prompt'una beslemek için)
# -----------------------------------------------------------------------------

def gecmis_metni_olustur(gecmis: Sequence[Mesaj], limit: int = 6, max_uzunluk: int = 400) -> str:
    """Son konuşma geçmişini RAG_CEVAP_PROMPTU'ndaki {gecmis} yerine geçecek
    şekilde formatlar. Boşsa boş string döner (prompt formatı bozulmaz)."""
    if not gecmis:
        return ""
    son_mesajlar = list(gecmis)[-limit:]
    satirlar = []
    for m in son_mesajlar:
        icerik = (m.icerik or "").strip()
        if not icerik:
            continue
        if len(icerik) > max_uzunluk:
            icerik = icerik[:max_uzunluk] + "..."
        rol = "Kullanıcı" if m.rol == "user" else "Asistan"
        satirlar.append(f"{rol}: {icerik}")
    if not satirlar:
        return ""
    return "GEÇMİŞ KONUŞMA (bağlam için, cevabı buna göre şekillendir):\n" + "\n".join(satirlar) + "\n\n"