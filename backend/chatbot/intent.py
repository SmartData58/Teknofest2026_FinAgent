# =============================================================================
# intent.py — Niyet Tespiti, Statik Yanıtlar ve RAG Prompt Yönetimi
#
# 🛠️ BU SÜRÜMDE ÇÖZÜLEN 3 SORUN (ekran kaydından):
#
# 1) "LİSTE İSTEDİĞİMDE LİSTE VERMİYOR"
#    Kök neden: bu dosyadaki (ve generate_response.py'deki) niyet kalıplarının
#    NEREDEYSE HEPSİ `\bkelime\b` biçimindeydi. Türkçe sondan eklemeli bir dil
#    olduğu için "liste" kökü "listeLER misin", "ödül" kökü "ödülÜ", "kampanya"
#    kökü "kampanyaLARI" olduğunda kelimenin SONUNDAKİ \b sınırı HİÇ OLUŞMUYOR
#    ve regex eşleşmiyordu. "bana para ödülü olan tüm kampanyaları listeler
#    misin" cümlesinde eşleşen TEK BİR kalıp bile yoktu — bu yüzden Mongo
#    tablosu hiç üretilmedi, cevap sadece vektör aramadan gelen serbest metin
#    oldu. Artık tüm kökler `kök\w*` biçiminde yazılıyor (bkz. _kok()).
#
# 2) "İNGİLİZCE İSTEDİĞİMDE ANLAMIYOR"
#    Kök neden: niyet kalıplarının tamamı yalnızca Türkçeydi. Arayüz `language`
#    alanını (tr/en) zaten backend'e POST ediyor ama niyet motoru bu alandan
#    habersizdi: "can you list me interest rate of the banks" hiçbir kalıba
#    uymuyor, selamlama/liste/karşılaştırma/hesaplama niyetlerinin hiçbiri
#    tetiklenmiyordu. Artık her kalıbın İngilizce karşılığı var ve `dil`
#    parametresi statik cevapların dilini belirliyor.
#
# 3) "KAMPANYA HAKKINDA BİLGİ İSTİYORUM, GRAFİK VERİYOR (üstelik kâr payı
#    grafiği)"
#    Kök neden: "…kıyaslandığında hangi segmentlerde daha yüksek getiri
#    sağlıyor?" cümlesindeki "kıyasla" _KARSILASTIRMA_GENEL'e takılıyor,
#    niyet "karsilastirma" + alan="kar_payi_orani" oluyor ve generate_response
#    KOŞULSUZ bir kâr payı grafiği çiziyordu — oysa bu bir YORUM sorusu.
#    Artık görselleştirme kararı ayrı ve açık: AÇIKLAYICI/YORUM soruları grafik
#    ÜRETMEZ; grafik yalnızca açıkça istendiğinde, tablo ise açıkça istendiğinde
#    ya da sıralama/veri sorularında (özet olarak 3 satır) üretilir.
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

# 🛠️ Statik cevaplar artık İKİ DİLLİ. Önceden yalnızca Türkçe vardı; arayüzde
# İngilizce seçiliyken "hello" yazan kullanıcı Türkçe bir selamlama alıyordu
# (aslında hiç eşleşmediği için doğrudan RAG'a düşüyor, kampanya arıyordu).
#
# ⚠️ GERİYE DÖNÜK UYUMLULUK: `STATIK_CEVAP` eskiden düz bir dict[str, str]'di ve
# başka modüller `STATIK_CEVAP["selamlama"]` şeklinde okuyor olabilir. Bu yüzden
# TÜRKÇE sözlük aynı isimde ve aynı biçimde bırakıldı; İngilizcesi ayrı bir
# sözlükte ve seçim `statik_metin()` yardımcısıyla yapılıyor.
STATIK_CEVAP: dict[str, str] = {
    "selamlama": "Merhaba! Katılım bankacılığı kampanyaları ve finansman ürünleri hakkında nasıl yardımcı olabilirim?",
    "hal_hatir": "Teşekkür ederim, size yardımcı olmak için buradayım. Hangi kampanya veya banka hakkında bilgi almak istersiniz?",
    "tesekkur": "Rica ederim, her zaman yardımcı olmaktan mutluluk duyarım. Başka bir konuda sorunuz var mı?",
    "vedalasma": "İyi günler dilerim. Yeniden görüşmek üzere!",
    "yetenekler": "Kampanyaları bankaya göre listeleyebilir, en düşük kâr payı veya en yüksek ödül gibi karşılaştırmalar yapabilir, taksit hesabı yapabilir ve kampanya detaylarını açıklayabilirim.",
    "tavsiye_red": "Ben bir yapay zeka asistanıyım ve yatırım/finansal tavsiye veremem. Ancak bankaların güncel kampanya, oran ve masraf bilgilerini sizin için karşılaştırıp listeleyebilirim.",
}

# 🌍 İNGİLİZCE PROMPT İSKELETİ
# 🛠️ HATA DÜZELTMESİ (canlı testte yakalandı): İngilizce seçiliyken cevap bazen
# Türkçe dönüyordu ("draw a chart of the highest rewards" -> Türkçe cevap).
# Sebep: prompt'un TAMAMI Türkçeydi; İngilizce isteği yalnızca tek bir satır
# ("Write your answer ONLY in English.") taşıyordu. 4B'lik bir model, promptun
# baskın diline uyar — bu yüzden karar kararsızdı: aynı ayarla bazen İngilizce
# bazen Türkçe cevap geliyordu. Artık dil seçiliyse iskeletin TAMAMI o dilde.
RAG_CEVAP_PROMPTU_EN = """You are a capable AI finance assistant.
RULES:
- Answer ONLY based on the campaign information below.
- If the information is not present in the campaign texts, say clearly "this information is not in my campaign data". NEVER guess or invent numbers.
- State which bank's campaign you are referring to.
- If a "CONVERSATION HISTORY" section appears below, take its context into account (which bank/campaign was being discussed).
- {dil_kurali}
- {mod_kurali}
- If the user asks for investment advice: say that you provide campaign information but cannot give advice.

CAMPAIGN INFORMATION:
{baglam}

{gecmis}QUESTION: {soru}

ANSWER:"""


def rag_promptu(dil: str = "tr") -> str:
    """Seçili dile göre RAG prompt iskeletini döner."""
    return RAG_CEVAP_PROMPTU_EN if dil_normalize(dil) == "en" else RAG_CEVAP_PROMPTU


STATIK_CEVAP_EN: dict[str, str] = {
    "selamlama": "Hello! How can I help you with participation banking campaigns and financing products?",
    "hal_hatir": "Thank you, I'm here to help. Which campaign or bank would you like to know about?",
    "tesekkur": "You're welcome, happy to help anytime. Is there anything else you'd like to ask?",
    "vedalasma": "Have a good day. See you again!",
    "yetenekler": "I can list campaigns by bank, compare them (lowest profit rate, highest reward and so on), calculate installments and explain campaign details.",
    "tavsiye_red": "I'm an AI assistant and I can't give investment or financial advice. I can, however, compare and list the banks' current campaigns, rates and fees for you.",
}


def statik_metin(ad: str, dil: str = "tr") -> Optional[str]:
    """Statik cevabı seçili dilde döner (bilinmeyen dil -> Türkçe)."""
    kaynak = STATIK_CEVAP_EN if (dil or "tr").lower().startswith("en") else STATIK_CEVAP
    return kaynak.get(ad) or STATIK_CEVAP.get(ad)

# -----------------------------------------------------------------------------
# 2. TÜRKÇE MAPPING VE BANKA TANIMLARI
# -----------------------------------------------------------------------------

TR_LOWER_MAP = str.maketrans({"İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç"})

def tr_lower(text: str) -> str:
    """Türkçe karakterleri 'İ'->'i' ve 'I'->'ı' mantığıyla doğru küçük harfe çevirir."""
    return text.translate(TR_LOWER_MAP).lower() if text else ""


def dil_normalize(dil: Optional[str]) -> str:
    """Arayüzden gelen `language` alanını ("tr", "en", "en-US", None...) iki
    desteklenen değerden birine indirger. Bilinmeyen/boş değer Türkçe sayılır."""
    d = (dil or "tr").strip().lower()
    return "en" if d.startswith("en") else "tr"


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

# 🛠️ Banka adlarında da aynı ek sorunu vardı: "Kuveyt Türk'ün", "Albaraka'nın",
# "Ziraat Katılım'ın" yazımlarında kelimenin sonundaki \b, kesme işareti ve ek
# yüzünden kayıyordu. Sona `[\w']*` eklenerek ek almış hâller de yakalanıyor.
_BANKA_PATTERNS: list[tuple[str, re.Pattern]] = []
for kod, takmalar in BANKA_TAKMA_ADLARI.items():
    for takma in sorted(takmalar, key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(takma)}[\w']*", re.IGNORECASE)
        _BANKA_PATTERNS.append((kod, pattern))

# 🆕 KISALTMALAR — takma ad listesinden AYRI tutuluyor.
#
# 500'lük koşuda üç senaryo aynı sebepten düştü:
#     "KT'nin kampanyalarını listele" / "kt kampanyalari nelerdir" /
#     "show KT campaigns"
# Hiçbirinde banka tespit EDİLEMEDİ; banka filtresi hiç uygulanmadı ve
# kullanıcı Kuveyt Türk isterken 311 kaydın tamamından 50 satırlık bir tablo
# aldı (tabloda Albaraka Türk de vardı).
#
# Neden yukarıdaki listeye eklenemez: orada her takma ad `\b{ad}[\w']*`
# kalıbına çevriliyor. "kt" için bu `\bkt[\w']*` olurdu ve "kt" ile BAŞLAYAN
# her kelimeye yapışırdı. Kısaltmalar TAM TOKEN olarak eşleşmeli; ek gelirse
# yalnızca kesme işaretiyle gelir ("KT'nin", "KT'ye").
_BANKA_KISALTMALARI: dict[str, tuple[str, ...]] = {
    "kuveytturk": ("kt", "kvt"),
    "turkiye_finans": ("tf",),
}
for _kod, _kisaltmalar in _BANKA_KISALTMALARI.items():
    for _kisa in _kisaltmalar:
        _BANKA_PATTERNS.append((
            _kod,
            re.compile(rf"\b{re.escape(_kisa)}(?:['’]\w+)?\b", re.IGNORECASE),
        ))

# -----------------------------------------------------------------------------
# 3. KALIP YARDIMCILARI
# -----------------------------------------------------------------------------

def _kok(*kokler: str) -> str:
    """Verilen kökleri "ek almış hâlleri de yakalayan" bir regex alternatifine çevirir.

    Türkçe'de `\\bliste\\b` "listeler misin" içindeki "liste"yi YAKALAYAMAZ (kelime
    ekle devam ettiği için sondaki sınır oluşmaz). Bu yüzden kökün SONUNA `\\w*`
    ekliyoruz: `\\bliste\\w*` -> liste, listele, listeler, listesi, listeleyebilir...
    Aynı yardımcı İngilizce için de doğru çalışır (list -> lists, listing).
    """
    return "|".join(rf"\b{k}\w*" for k in kokler)


def _derle(*parcalar: str) -> re.Pattern:
    return re.compile("|".join(p for p in parcalar if p), re.IGNORECASE)


# -----------------------------------------------------------------------------
# 4. STATİK SOSYAL VE GÜVENLİK REGEX KALIPLARI (TR + EN)
# -----------------------------------------------------------------------------

_STATIK_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("selamlama", re.compile(
        r"^\s*(merhaba\w*|meraba|mrhb|selam\w*|slm|sa|s\.a|selamun\s+aleykum|selamün\s+aleyküm"
        r"|günaydın|gunaydin|hayırlı\s+sabahlar|iyi\s+(günler|gunler|akşamlar|aksamlar|geceler)"
        r"|hello|hi|hey|good\s+(morning|afternoon|evening)|greetings)\b", re.IGNORECASE)),
    ("hal_hatir", re.compile(
        r"^\s*(nasılsın|nasilsin|nasilsiniz|naber|n'aber|ne\s+haber|iyi\s+misin|iyi\s+misiniz"
        r"|nasıl\s+gidiyor|napıyorsun|napyosun|ne\s+yapıyorsun"
        r"|how\s+are\s+you|how'?s\s+it\s+going|what'?s\s+up)\b", re.IGNORECASE)),
    ("tesekkur", re.compile(
        r"^\s*(teşekkür\w*|tesekkur\w*|sağol\w*|sagol\w*|saol|eyvallah|eyv|harikasın|supersin|süpersin"
        r"|thanks|thank\s+you|thx|appreciate\s+it|awesome|great\s+job)\b", re.IGNORECASE)),
    ("vedalasma", re.compile(
        r"^\s*(görüşürüz|gorusuruz|baybay|bye|goodbye|see\s+you|hoşça\s+kal|hoscakal"
        r"|iyi\s+çalışmalar|iyi\s+calismalar|kolay\s+gelsin|tamamdır|tamamdir|anladım|anladim"
        r"|got\s+it|understood|ok\s+thanks)\b", re.IGNORECASE)),
    ("yetenekler", re.compile(
        r"^\s*(kimsin|sen\s+kimsin|ne\s+işe\s+yarıyorsun|ne\s+ise\s+yariyorsun|ne\s+yapabilirsin"
        r"|yardım\s+et|yardim|nereden\s+başlamalıyım"
        r"|who\s+are\s+you|what\s+can\s+you\s+do|what\s+do\s+you\s+do|help\s+me|how\s+can\s+you\s+help)\b",
        re.IGNORECASE)),
)

_TAVSIYE = re.compile(
    r"tavsiye|öner(ir|sen|in)|mal[ıi]\s*m[ıi]y[ıi]m|mal[ıi]y[ıi]m\b"
    r"|meli\s*miyim|mant[ıi]kl[ıi]\s*m[ıi]|de[ğg]er\s*mi\b|do[ğg]ru\s+olur\s+mu"
    # EN
    r"|should\s+i\b|is\s+it\s+worth|do\s+you\s+recommend|what\s+do\s+you\s+advise"
    r"|would\s+you\s+recommend|is\s+it\s+a\s+good\s+idea",
    re.IGNORECASE)

# -----------------------------------------------------------------------------
# 5. GÖRSELLEŞTİRME / LİSTELEME / SIRALAMA KALIPLARI  (TEK GERÇEK KAYNAK)
#
# ⚠️ Bu kalıplar generate_response.py tarafından da kullanılır. Önceden AYNI
# mantık iki dosyada AYRI AYRI (ve birbirinden farklı) yazılmıştı; biri
# güncellenip diğeri unutulduğu için "grafik istedim tablo geldi" / "liste
# istedim hiçbir şey gelmedi" gibi tutarsızlıklar çıkıyordu.
# -----------------------------------------------------------------------------

# Açık GRAFİK isteği (pasta/çubuk/görsel).
GRAFIK_ISTEGI = re.compile(
    r"\bgrafi[kğq]\w*"                      # grafik, grafiği, grafikle, grafiq (yazım hatası)
    r"|" + _kok("pasta", "diyagram", "diagram", "chart", "graph", "plot",
                "visuali", "görsel", "gorsel") +
    # 🛠️ HATA DÜZELTMESİ: Burada eskiden `\b[şs]ekil\w*` vardı ve Türkçenin en sık
    # bağlaçlarından birini — "...şekilDE" — grafik isteği sanıyordu. Yani
    # "ödül tutarı en yüksekten başlayacak ŞEKİLDE listeler misin" cümlesi
    # TABLO yerine GRAFİK üretiyordu. "şekil" ancak açıkça bir görsel istendiğinde
    # ("şekil olarak", "şekil çiz") grafik sayılır.
    # Aynı şekilde `[çc]iz\w*` "çizelge"yi (= tablo!) yakalıyordu; o da dışlandı.
    r"|\b[şs]ekil\s+(olarak|halinde|hâlinde|[çc]iz\w*)"
    r"|\b[çc]iz(?!elge)\w*|\b(pie|donut|doughnut|bar)\b",
    re.IGNORECASE,
)

# Açık TABLO/LİSTE isteği.
# 🛠️ "listeler misin", "kampanyaları göster", "tümünü dök" gibi EK ALMIŞ hâller
# eskiden hiç yakalanmıyordu (bkz. dosya başındaki 1. madde).
TABLO_ISTEGI = re.compile(
    _kok("tablo", "liste", "listele", "sırala", "sirala", "döküm", "dokum",
         "detaylandır", "detaylandir", "göster", "goster",
         "table", "list", "rank", "sort", "enumerate", "breakdown", "display") +
    r"|\bshow\s+(me|all|the)\b|\bhepsini\b|\bt[üu]m[üu]n[üu]\b",
    re.IGNORECASE,
)

# Sıralama/üstünlük (superlative) — "en düşük kâr payı", "highest reward".
SIRALAMA_ISTEGI = re.compile(
    r"\ben\s+(" + "|".join([
        r"d[üu][şs][üu]k\w*", r"az", r"ucuz\w*", r"uygun\w*", r"iyi", r"avantajl[ıi]\w*",
        r"y[üu]ksek\w*", r"[çc]ok", r"fazla\w*", r"b[üu]y[üu]k\w*", r"uzun\w*", r"k[ıi]sa\w*",
    ]) + r")"
    r"|" + _kok("lowest", "highest", "cheapest", "best", "largest", "longest",
                "shortest", "maximum", "minimum", "top", "most") +
    r"|\bhangisi\s+daha\b|\bhangi\s+banka\w*\s+daha\b",
    re.IGNORECASE,
)

KARSILASTIRMA_ISTEGI = re.compile(
    _kok("karşılaştır", "karsilastir", "kıyasla", "kiyasla", "compare", "comparison") +
    r"|\bversus\b|\bvs\.?\b|\bhangisi\s+daha\b|\bhangi\s+banka\w*\s+daha\b",
    re.IGNORECASE,
)

# AÇIKLAYICI / YORUM sorusu — grafik ya da tablo ÜRETMEZ.
# 🛠️ Ekran kaydındaki "…kıyaslandığında hangi segmentlerde daha yüksek getiri
# sağlıyor?" sorusu tam olarak buraya girer: içinde "kıyasla" ve "daha yüksek"
# geçtiği için eski kod bunu bir SIRALAMA sorusu sanıp kâr payı grafiği
# çiziyordu. Oysa kullanıcı bir YORUM istiyor.
ACIKLAYICI_SORU = re.compile(
    _kok("koşul", "kosul", "şart", "sart", "segment", "avantaj", "dezavantaj",
         "açıkla", "acikla", "anlat", "yorumla", "özetle", "ozetle", "değerlendir",
         "explain", "describe", "summar", "interpret", "advantage", "disadvantage",
         "condition", "requirement", "eligib", "benefit", "differ") +
    r"|\bnas[ıi]l\b|\bneden\b|\bni[çc]in\b|\bniye\b|\bne\s+zaman\b|\bne\s+demek\b"
    r"|\bkimler\w*|\bkime\b|\bkimin\b|\balabilir\s+m[iı]\w*|\bge[çc]erli\s+m[iı]\w*"
    r"|\buygulan[ıi]r\s+m[iı]\w*|\bdahil\s+m[iı]\w*|\bfark[ıi]\s+ne\b"
    r"|\bhangi\s+\w+lerde\b|\bhangi\s+\w+larda\b"
    r"|\bwhy\b|\bhow\s+(do|does|can|is|are|long)\b|\bwho\s+(can|is|are)\b"
    r"|\bwhen\s+(is|are|does|do)\b|\bwhich\s+segment\w*|\bis\s+it\s+valid\b"
    # 🛠️ 500'lük koşuda EKLENDİ. Aşağıdaki altı soru tablo üretiyordu; hepsi
    # TANIM ya da GÖRÜŞ sorusu, hiçbiri veri listesi istemiyor:
    #     "vade ne anlama geliyor"            -> tanım
    #     "kâr payı ile faiz arasındaki fark nedir" -> tanım
    #     "bu kampanyalar hakkında genel yorumun ne" -> görüş
    #     "sence bu kampanyalar cazip mi"     -> görüş
    #     "benim için hangisi daha mantıklı olur sence" -> görüş/tavsiye
    #     "kampanya bitince ne oluyor"        -> süreç
    # "ne demek" zaten vardı ama "ne anlama geliyor" / "nedir" / "sence"
    # kalıpları yoktu.
    r"|\bne\s+anlama\s+gel\w*|\bne\s+demektir\b"
    r"|\bnedir\b|\bne\s+ifade\s+ed\w*"
    r"|\bsence\b|\bsizce\b|\bg[öo]r[üu][şs][üu]n\w*|\byorumun\w*"
    r"|\bcazip\s+m[iı]\w*|\bmant[ıi]kl[ıi]\s+m[iı]\w*|\bde[ğg]er\s+m[iı]\w*"
    r"|\btavsiye\s+ed\w*|\b[öo]ner(?:ir|isin|iyor)\w*"
    r"|\bbitince\b|\bbitti[ğg]inde\b|\bsonra\s+ne\s+ol\w*"
    r"|\bfark[ıi]\s+nedir\b|\baras[ıi]ndaki\s+fark\w*"
    r"|\bwhat\s+(is|are|does)\s+\w+\s+mean\b|\bwhat\s+do\s+you\s+mean\b"
    r"|\bin\s+your\s+opinion\b|\bdo\s+you\s+think\b|\bwhat\s+is\s+the\s+difference\b"
    # 🛠️ 500'lük koşuda EKLENDİ — İNGİLİZCE TANIM SORUSU.
    #     "what is profit rate in participation banking"
    # Türkçesi ("kâr payı nedir") \bnedir\b ile zaten yakalanıyordu, İngilizcesi
    # HİÇBİR kalıba uymuyordu: soru VERI_SORUSU'na ("rate", "profit") düşüp
    # tablo üretiyordu. Kullanıcı bir TANIM istedi, veri listesi değil.
    #
    # "what is/are ..." tek başına alınamaz: "what is the highest reward" da aynı
    # kalıba uyar ama o bir VERİ sorusudur. Ayrım, cümlede üstünlük/agrega
    # kelimesi olup olmaması; negatif ileri-bakış onları dışarıda bırakıyor.
    r"|\bwhat\s+(?:is|are)\s+"
    r"(?![^?.!]*\b(?:highest|lowest|best|worst|cheapest|top|most|least|largest|"
    r"longest|shortest|biggest|maximum|minimum|total|average|sum|count)\b)",
    re.IGNORECASE,
)

# Yazılım/kod yazma isteği — kampanya tablosu ÜRETİLMEZ.
KOD_YAZMA_ISTEGI = re.compile(
    r"\b(python\w*|javascript|typescript|fonksiyon\w*|script\w*|algoritma\w*|kütüphane\w*"
    r"|function|library|regex|sql\s+query"
    r"|kod\s*(yaz\w*|örne[ğk]i\w*|parças[ıi]\w*)|nas[ıi]l\s+(yazar[ıi]m|kodlar[ıi]m|programlar[ıi]m)"
    r"|write\s+(a\s+)?(code|function|script))\b",
    re.IGNORECASE,
)

# Veri/metrik içeren "normal" soru — açıkça istenmese de kısa (3 satırlık)
# özet tablo göstermeye değer.
VERI_SORUSU = re.compile(
    r"\bk[âa]r\s*pay\w*"
    r"|" + _kok("oran", "faiz", "ödül", "odul", "hediye", "iade", "vade", "taksit",
                "kampanya", "promosyon", "limit", "getiri", "finansman",
                "rate", "interest", "profit", "reward", "cashback", "bonus",
                "campaign", "promotion", "maturity", "installment", "term") +
    r"|\bnakit\b|\btl\b|\btry\b",
    re.IGNORECASE,
)

# 🛠️ HATA DÜZELTMESİ (senaryo testinde yakalandı): "50000 tl 24 ay 3.5 oranla
# HESAPLA" hesaplama olarak tanınmıyordu. Eski desen "hesapla"yı yalnızca
# "taksit" kelimesiyle BİRLİKTE arıyordu (`taksit\w*\s+hesapla\w*`); kullanıcı
# "taksit" demeden sadece "hesapla" yazdığında niyet kaçıyor, deterministik
# hesap yerine LLM'e düşülüyordu (yani sayı uydurma riski geri geliyordu).
# Artık "hesapla/hesabı/calculate/compute" tek başına da tetikliyor — yanlış
# tetikleme riski YOK, çünkü niyet_bul bu daldan yalnızca metinden TUTAR VE VADE
# birlikte çıkarılabildiğinde hesaplamaya yönlendiriyor; çıkaramazsa normal
# akışa devam ediyor (ör. "kampanya hesaplama fonksiyonu nasıl yazılır" sorusu
# tutar/vade içermediği için etkilenmez).
_HESAP_DILI = re.compile(
    r"\bhesapla\w*|\bhesab[ıi]\w*|hesaplar\s*m[ıi]s[ıi]n|ayl[ıi]k\s+taksit"
    r"|ayda\s+ne\s+kadar|ne\s+kadar\s+öde(rim|nir)|kaç\s+taksit"
    r"|\bcalculate\w*|\bcompute\w*|monthly\s+payment"
    r"|how\s+much\s+(would|will|do)\s+i\s+pay|payment\s+plan",
    re.IGNORECASE)

# 🏦 ÜRÜN VERİSİ NİYETLERİ — kampanya dışı iki koleksiyon.
#
# Bunlar `hesaplama` niyetinin YERİNE geçti. Eski davranış iki ayrı hataya yol
# açıyordu:
#   1) `_HESAP_DILI` içindeki `hesab[ıi]\w*` kalıbı, "katılım HESABI kâr payı
#      getirisi" cümlesindeki İSMİ, "hesapla" FİİLİ sanıyordu. Tutar ve vade de
#      çıkarılabildiği için soru kredi taksit hesaplayıcısına düşüyor ve bir
#      MEVDUAT ürünü için "Aylık Taksit: 125.990 TL" yazıyordu — müşteri para
#      yatırıp kâr payı kazanırken, sanki kredi geri ödüyormuş gibi.
#   2) Hesaplayıcı, kullanıcının cümlesindeki oranı her hâlükârda AYLIK kredi
#      oranı kabul ediyordu; %25,99 yıllık net mevduat getirisi bu yüzden
#      100.000 TL'yi bir ayda 125.990 TL'ye çıkarmıştı.
#
# Artık hesaplama yapılmıyor: her iki ürün de MongoDB'deki gerçek kayıtlarla
# (bankaların yayımladığı taksit/getiri tutarlarıyla) cevaplanıyor.

# Yalnızca MEVDUAT anlamını yakalar. Sadece "katılım" YETMEZ — "katılım
# bankalarının kampanyaları" sorusu bir kampanya sorusudur, mevduat sorusu değil.
_KATILIM_URUNU = re.compile(
    r"kat[ıi]l[ıi]m\s+hesab\w*|kat[ıi]lma\s+hesab\w*"
    r"|vadeli\s+(?:hesap\w*|mevduat\w*)|\bmevduat\w*"
    r"|birikim\s+hesab\w*|tasarruf\s+hesab\w*"
    r"|net\s+getiri\w*|br[üu]t\s+getiri\w*"
    r"|k[âa]r\s+pay[ıi]\s+getiri\w*"
    r"|yat[ıi]r[ıi]lan\s+tutar\w*"
    r"|deposit\s+account|savings\s+account|participation\s+account",
    re.IGNORECASE)

# Finansman/kredi ÜRÜNÜ. "taksit" tek başına yetmez: kart kampanyalarının çoğu
# ("12 taksit fırsatı") aynı kelimeyi kullanıyor ve onlar kampanya sorusudur.
_FINANSMAN_URUNU = re.compile(
    r"(?:konut|ta[şs][ıi]t|ara[çc]|iht[ıi]ya[çc]|t[üu]ketici)\s*"
    r"(?:finansman\w*|kredi\w*)"
    r"|finansman\s+(?:tutar\w*|[üu]r[üu]n\w*|se[çc]enek\w*|teklif\w*)"
    r"|ayl[ıi]k\s+taksit\w*|geri\s+[öo]deme\w*|geri\s+[öo]denecek"
    r"|tahsis\s+[üu]cret\w*"
    r"|housing\s+financ\w*|vehicle\s+financ\w*|personal\s+(?:loan|financ\w*)"
    r"|\bmortgage\w*|monthly\s+installment",
    re.IGNORECASE)


# 🛠️ "İKİ KOPUK DÜNYA" — ürün metriği soran kıyaslar finansman verisini
# göremiyordu.
#
# Ölçüldü: "En uzun vade seçeneği sunan finansman hangisi?" sorusuna sistem
# "9 ay" cevabı veriyordu — çünkü soru kampanya akışına düşüyor ve orada yalnızca
# kart taksit vadeleri var. Oysa `finansman_urun`'da 120 aylık konut
# finansmanları duruyor. Aynı kök, "avantajlı kâr payı fırsatı" sorusunda
# "oran verisi olan tek banka Kuveyt Türk" cevabına yol açıyordu (dört bankanın
# finansman oranı kayıtlı olmasına rağmen). İkisi de şartname 5.7'de sayılan
# karşılaştırma ölçütleri.
#
# Ayrım kuralı: cümlede "kampanya" geçiyorsa KAMPANYA sorusudur (taksonomide
# `finansman_kampanyasi` diye bir kampanya türü var, onu çalmamalıyız).
# Geçmiyorsa ve finansman/kredi bir ÜRÜN METRİĞİ ile birlikte anılıyorsa,
# cevap ürün tablosundan gelmelidir.
_KAMPANYA_KELIMESI = re.compile(r"\bkampanya\w*", re.IGNORECASE)
_FINANSMAN_KELIMESI = re.compile(r"\b(?:finansman|kredi)\w*", re.IGNORECASE)
_URUN_METRIGI = re.compile(
    r"\ben\s+(?:uzun|k[ıi]sa|d[üu][şs][üu]k|y[üu]ksek|az|[çc]ok|iyi|avantajl[ıi]|ucuz)\w*"
    r"|\bvade\w*|\bk[âa]r\s*pay\w*|\boran\w*|\btaksit\w*|\bmasraf\w*"
    r"|\btahsis\w*|\bmaliyet\w*|\bgeri\s+[öo]deme\w*"
    r"|\blongest\b|\blowest\b|\bcheapest\b|\bbest\b|\bmaturity\b|\bterm\b",
    re.IGNORECASE)


_KARSILASTIRMA_ALANLARI: tuple[tuple[str, re.Pattern], ...] = (
    ("tahsis_ucreti", re.compile(
        r"en\s+(düşük\w*|az|ucuz\w*)\s+(tahsis\w*|masraf\w*|ücret\w*)|masrafs[ıi]z"
        r"|(lowest|cheapest)\s+(fee|cost|charge)s?|no\s+fee", re.IGNORECASE)),
    ("kar_payi_orani", re.compile(
        r"en\s+(düşük\w*|uygun\w*|iyi|avantajl[ıi]\w*|ucuz\w*)\s+(kâr\w*|kar\w*|oran\w*|faiz\w*)"
        r"|oran[ıi]?\s+en\s+düşük\w*"
        r"|(lowest|best|cheapest)\s+(profit\s+)?(rate|interest|margin)s?", re.IGNORECASE)),
    ("odul_miktari", re.compile(
        r"en\s+(yüksek\w*|çok|fazla\w*|büyük\w*)\s+(ödül\w*|iade\w*|hediye\w*|nakit|parafpara|puan\w*|kazan[çc]\w*)"
        r"|(highest|biggest|largest|most)\s+(reward|cashback|bonus|gift|prize|earning)s?", re.IGNORECASE)),
    ("vade_ay", re.compile(
        r"en\s+(uzun\w*|yüksek\w*|fazla\w*)\s+vade\w*"
        r"|(longest|highest)\s+(maturity|term|tenor)s?", re.IGNORECASE)),
    ("taksit_sayisi", re.compile(
        r"en\s+(çok|fazla\w*|yüksek\w*)\s+taksit\w*"
        r"|(most|highest)\s+installments?", re.IGNORECASE)),
)

# 🛠️ "Dünya Katılım'da hangi FIRSATLAR var" 500'lük koşuda hiç tablo almadı:
# kalıp yalnızca "hangi KAMPANYA" diyordu. Kullanıcı aynı şeyi "fırsat",
# "seçenek", "imkân" diye de soruyor. Genel "hangi <şey> var" kalıbı eklendi.
_LISTE = re.compile(
    _kok("kampanyalar", "listele", "liste", "göster", "goster", "campaign", "list", "show") +
    r"|hangi\s+kampanya\w*|neler\s+var|nelerdir\b|hangi\s+\w+\s+var\b"
    r"|\bf[ıi]rsat\w*|\bse[çc]enek\w*|\bimk[âa]n\w*"
    r"|what\s+campaigns?|which\s+campaigns?|what.{0,12}available",
    re.IGNORECASE)

# Taksit hesaplama sorularından tutar / vade / oran çıkarmak için kullanılır.
_TUTAR_DESENI = re.compile(
    r'(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)', re.IGNORECASE)
_VADE_DESENI = re.compile(
    r'(\d{1,3})\s*(?:ay|aylık|taksit|month|months|installments?)', re.IGNORECASE)
# 🛠️ "3.5 oranla" gibi YÜZDE İŞARETSİZ yazımlar da yakalanıyor. Eskiden yalnızca
# "%2,99" / "2,99%" biçimleri tanınıyordu; kullanıcı "24 ay 3.5 oranla hesapla"
# dediğinde oran None kalıyor ve hesaplama, kullanıcının verdiği oran yerine
# Mongo'daki ORTALAMA oranla yapılıyordu (sonuç sessizce yanlış çıkıyordu).
_ORAN_DESENI = re.compile(
    r'%\s*(\d+(?:[.,]\d+)?)'
    r'|(\d+(?:[.,]\d+)?)\s*%'
    r'|(\d+(?:[.,]\d+)?)\s*(?:oran\w*|k[âa]r\s*pay\w*|faiz\w*|\brate\b)'
)

_DEVAM = re.compile(
    # 🛠️ EK SORUNU — `\bayn[ıi](s[ıi])?\b` "aynısıNI" kelimesini KAÇIRIYORDU:
    # kök "aynısı" eşleşse bile sonundaki \b, ek yüzünden hiç oluşmuyor.
    # Bildirilen etki: "Albaraka Türk için de AYNISINI yap" bir takip sorusu
    # sayılmıyor, önceki turda çizilen tablo devralınmıyor ve kullanıcı hiç
    # tablo göremiyordu. Kök artık `\w*` ile serbest bırakıldı.
    r"^\s*(peki|pekala|o\s+zaman|ya\s+\S)|\bpeki\b|\bayn[ıi]\w*|\bonun\b|\bbunun\b|\bşunun\b"
    r"|\b(o|bu|şu)\s+(kampanya\w*|banka\w*|hesap\w*|plan\w*|oran\w*)|\bolsa(yd[ıi])?\b|\bolursa\b"
    r"|\bbir\s+de\b"
    r"|^\s*(and|what\s+about|how\s+about|then)\b|\bthat\s+(campaign|bank|offer)\b|\bthe\s+same\b",
    re.IGNORECASE)
# 🆕 "ŞUNU DA EKLE" KALIBI — banka kümesini GENİŞLETİR (değiştirmez).
#
# 500'lük koşuda bulundu:
#     1) "Kuveyt Türk kampanyalarını listele"  -> tablo geldi
#     2) "Albaraka'yı da ekle"                 -> HİÇ tablo gelmedi
# Kullanıcı iki bankayı YAN YANA görmek istiyor. Eski davranışta ikinci mesaj
# ne devam sayılıyordu (çünkü _DEVAM'a uymuyor) ne de kendi başına bir liste
# isteğiydi; sonuçta ne tablo çizildi ne de Kuveyt Türk korundu.
_EKLEME = re.compile(
    r"\b(?:de|da|ayr[ıi]ca|bir\s+de)\s+ekle\w*|\bekle\w*\s*[.!]?\s*$"
    r"|\byan[ıi]na\s+ekle\w*|\bkat\s*$"
    r"|\balso\s+(?:add|include)\b|\badd\s+\w+\s+(?:too|as\s+well)\b",
    re.IGNORECASE)

# 🆕 BANKA DÜZEYİNDE KIYAS SORUSU — yorum/açıklama filtresini EZER.
#
# 500'lük koşuda `kiyas` kategorisinde beş senaryo hiç tablo alamadı:
#     "hangi bankanın kampanyaları daha avantajlı"
#     "hangi banka en az avantaj sunuyor"
#     "Albaraka Türk sektörde nerede duruyor"
#     "kendi bankamız Emlak Katılım, rakiplere göre nasıl"
# Hepsi ACIKLAYICI_SORU'ya takılıyor ("avantaj", "nasıl") ve gorsel=None
# oluyor. Ama bunlar yorum sorusu DEĞİL: cevabı ancak bankaların verisini yan
# yana koyarak verilebilir. Yorum çerçevesi veriyi gereksiz kılmaz.
#
# ⚠️ Kalıp BİLEREK dar: "rakiplerle kıyaslandığında hangi segmentlerde daha
# yüksek getiri sağlıyor?" gibi gerçek yorum soruları DIŞARIDA kalmalı — o
# yüzden "rakiplerle" değil yalnızca "rakiplere göre" eşleşiyor.
BANKA_KIYAS_SORUSU = re.compile(
    r"\bhangi\s+banka\w*"
    # 🛠️ Araya kelime girebilir: "bankaları ÖDÜL TUTARINA GÖRE kıyasla".
    # Bitişik yazım şartı, gerçek bir kıyas sorusunu 3 satırlık özete
    # düşürüyordu (bkz. generate_response._BANKA_DUZEYINDE_KIYAS notu).
    r"|\bbankalar[ıi]\s+(?:\S+\s+){0,4}(?:k[ıi]yasla|kar[şs][ıi]la[şs]t[ıi]r|s[ıi]rala)\w*"
    r"|\bbankalar\s+aras[ıi]\w*|\bbankalara\s+g[öo]re\b"
    r"|\bbankalar[ıi]n\s+\w*(?:da[ğg][ıi]l[ıi]m|kar[şs][ıi]la[şs]t[ıi]rma|tablo)"
    r"|\bsekt[öo]rde\s+nerede\b|\bsekt[öo]rdeki\s+(?:yer|konum)\w*"
    r"|\brakip\w*\s+g[öo]re\b|\brekabet\w*|\bkim\s+(?:daha\s+iyi|[öo]nde)\b"
    # 🏦 BANKA ÇALIŞANININ KONUMLANMA/BOŞLUK/AKSİYON SORULARI.
    #
    # 100'lük persona testinde ölçüldü: "TOM Katılım'ın pazar konumunu
    # değerlendir" sorusuna cevap
    #     "pazar konumu, piyasa payı ... bilgisi BULUNMAMAKTADIR"
    #     "piyasa konumu değerlendirmesi YAPAMAM"
    # oluyordu. Oysa pazar payı ve kategori boşluğu KODDA hesaplanıyor.
    # Sebep: cümledeki "değerlendir"/"öner" ACIKLAYICI_SORU'ya takılıyor,
    # görsel kararı None kalıyor, Mongo yolu HİÇ çalışmıyor ve piyasa
    # fotoğrafı bağlama eklenmiyor — cevap yalnızca vektör aramasından
    # geliyor. Asistan elindeki veriyi "yok" diye sunuyordu.
    #
    # Bu kalıplar bir müşterinin sormayacağı, tanım gereği analist
    # sorularıdır; tabloyu ve piyasa bağlamını zorunlu kılıyorlar.
    r"|\bpazar\s+konum\w*|\bpiyasa\s+konum\w*|\bportf[öo]y\s+a[çç][ıi][ğg]\w*"
    r"|\bhangi\s+kategori\w*\s+(?:eksi|geri|zay[ıi]f)\w*|\bnerede\s+eksi\w*"
    r"|\bg[üu][çç]l[üu]\s+ve\s+zay[ıi]f|\bzay[ıi]f\s+y[öo]n\w*|\bg[üu][çç]l[üu]\s+y[öo]n\w*"
    r"|\baksiyon\w*\s+[öo]ner|\bhangi\s+(?:kategori|alan|segment)\w*\s+kampanya"
    r"|\bnerede\s+b[üu]y[üu]\w*|\bb[üu]y[üu]yebil\w*|\bb[üu]y[üu]me\s+(?:f[ıi]rsat|alan)\w*"
    r"|\bwhich\s+bank\w*|\bpeer\s+comparison\b|\bcompare\s+(?:the\s+)?banks?\b",
    re.IGNORECASE)

# 🛠️ "RAKİPLERLE KIYASLA" KALIBI — banka filtresini KAPATIR.
# Analist "Ben Kuveyt Türk'te çalışıyorum, rakiplerimizin ödüllerini bizimkiyle
# kıyasla" dediğinde eski kod banka filtresini 'kuveytturk'e kilitliyor ve
# rakipleri TAMAMEN dışarıda bırakıyordu — yani sorulanın tam tersini yapıyordu.
# Bu kalıp eşleştiğinde filtre uygulanmaz, tüm bankalar havuzda kalır.
RAKIP_KIYAS = re.compile(
    # 🛠️ "diğer KATILIM bankalarıyla" kaçıyordu: kalıp "diğer"in hemen ardından
    # "banka" bekliyordu. Araya tek bir niteleyici (katılım/kamu/özel…) girmesi
    # kıyas niyetini değiştirmiyor, o yüzden opsiyonel bir kelimeye izin verildi.
    r"\brakip\w*|\bdi[ğg]er\s+(?:\w+\s+)?banka\w*|\bba[şs]ka\s+(?:\w+\s+)?banka\w*"
    r"|\bt[üu]m\s+banka\w*"
    r"|\bbankalar\s+aras[ıi]\w*|\bsekt[öo]r\w*|\bpiyasa\w*|\bemsal\w*|\bbizimki\w*"
    r"|\bcompetitor\w*|\bother\s+banks?\b|\ball\s+banks?\b|\bacross\s+banks?\b"
    r"|\bmarket\s+(wide|average)\b|\bpeer\w*",
    re.IGNORECASE,
)

_BANKA_SORGUSU = re.compile(
    r"hangi\s+banka\w*|bankalar\w*|başka\s+banka\w*"
    r"|which\s+banks?|what\s+banks?|other\s+banks?|all\s+(the\s+)?banks?|of\s+the\s+banks?",
    re.IGNORECASE)

# "Tümü" istekleri (limit = eşleşen tüm kayıtlar).
TUMU_ISTEGI = re.compile(
    r"\bt[üu]m\w*|\bb[üu]t[üu]n\w*|\bhepsi\w*|\bhepsini\b|\btamam[ıi]n[ıi]\b"
    r"|\ball\b|\bevery\b|\bentire\b|\bcomplete\s+list\b|\bfull\s+list\b",
    re.IGNORECASE)

# -----------------------------------------------------------------------------
# 6. DATA CLASS & YARDIMCI FONKSİYONLAR
# -----------------------------------------------------------------------------

# Açıkça bir liste istenmediğinde gösterilecek "özet tablo" satır sayısı.
OZET_SATIR_SAYISI = 3
# Açıkça liste/tablo istendiğinde (ama sayı belirtilmediğinde) üst sınır.
VARSAYILAN_LISTE_LIMITI = 10
VARSAYILAN_LISTE_LIMITI_ANALIST = 50
# 🆕 Birden fazla banka adı geçen KIYASLAMA sorularında banka BAŞINA en az
# kaç satır gösterileceği. Gerekçe: "A ve B'yi kıyasla" sorusu 3 satırlık
# özete kırpıldığında üç satırın da aynı bankadan gelmesi mümkün oluyordu;
# model de ekranda göremediği bankayı "verisi yok" diye raporluyordu
# (bkz. generate_response.py'deki BANKA DENGELİ DİLİM notu).
KIYAS_BANKA_BASI_SATIR = 5


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
    # 🆕 Görselleştirme kararı — generate_response.py bunu OLDUĞU GİBİ uygular:
    #   "grafik" -> pasta/çubuk grafik + tablo
    #   "tablo"  -> yalnızca tablo görünümü
    #   None     -> hiçbir şey çizilme (yorum/açıklama sorusu, kod sorusu, sohbet)
    gorsel: Optional[str] = None
    # Kaç satır gösterilsin: pozitif sayı, "tümü" için -1, karar yoksa None.
    limit_istegi: Optional[int] = None
    # Soru bir yorum/açıklama sorusu mu (yeni tablo üretmek yerine önceki
    # bağlamı yeniden kullanmak için generate_response bunu kullanır).
    aciklayici: bool = False
    # Metinde geçen TÜM bankalar (çok bankalı kıyaslama için). `banka_kodu`
    # geriye dönük uyumluluk için ilk bankayı taşımaya devam eder.
    banka_kodlari: list = field(default_factory=list)
    # "rakiplerle / diğer bankalarla kıyasla" -> banka filtresi UYGULANMAMALI.
    kiyas_genis: bool = False
    # Yazılım/kod yazma sorusu mu (kampanya tablosu üretilmemeli).
    kod_sorusu: bool = False
    # Kararı kim verdi: "regex" (deterministik) veya "llm" (melez ajan).
    # Sadece loglama/teşhis için — davranışı etkilemez.
    gorsel_kaynagi: str = "regex"
    dil: str = "tr"


def banka_bul(soru: str) -> Optional[str]:
    """Metinde geçen İLK bankanın kodunu döner (geriye dönük uyumluluk)."""
    kodlar = bankalari_bul(soru)
    return kodlar[0] if kodlar else None


def bankalari_bul(soru: str) -> list:
    """Metinde geçen TÜM bankaların kodlarını, METİNDEKİ GEÇİŞ SIRASIYLA döner.

    🛠️ HATA DÜZELTMESİ (banka çalışanı senaryosunda yakalandı): Eski `banka_bul`
    yalnızca TEK bir kod döndürüyordu ve bunu BANKA_TAKMA_ADLARI sözlüğünün
    tanım sırasına göre seçiyordu — metindeki sıraya göre değil. Sonuç:
    "Kuveyt Türk ile Albaraka'yı kıyasla" sorusunda kod 'albaraka' dönüyor
    (çünkü sözlükte albaraka daha önce tanımlı), tablo/grafik SADECE Albaraka
    kampanyalarıyla doluyor ve kullanıcının istediği KIYASLAMA sessizce tek
    bankalı bir listeye dönüşüyordu. Analist görünümünün ana kullanım senaryosu
    tam olarak buydu.
    """
    s = tr_lower(soru)
    bulunanlar = []
    for kod, pattern in _BANKA_PATTERNS:
        m = pattern.search(s)
        if m and kod not in [k for k, _ in bulunanlar]:
            bulunanlar.append((kod, m.start()))
    bulunanlar.sort(key=lambda x: x[1])          # metindeki geçiş sırası
    return [kod for kod, _ in bulunanlar]


# 🛠️ HATA DÜZELTMESİ: Kullanıcıya gösterilen banka adları ya HAM KOD/ASCII
# hâliyle ("Kuveytturk", "Turkiye Finans") ya da "Bilinmeyen Banka" olarak
# çıkıyordu. Artık tek bir yerde tanımlı bu eşleme üzerinden düzgün ad üretiliyor.
BANKA_GORUNEN_ADLARI: dict[str, str] = {
    "albaraka": "Albaraka Türk",
    "kuveytturk": "Kuveyt Türk",
    "turkiye_finans": "Türkiye Finans",
    "vakif_katilim": "Vakıf Katılım",
    "ziraat_katilim": "Ziraat Katılım",
    "emlak_katilim": "Emlak Katılım",
    "hayat_finans": "Hayat Finans",
    "dunya_katilim": "Dünya Katılım",
    "tom_katilim": "TOM Katılım",
    "adil_katilim": "Adil Katılım",
}

_ANLAMSIZ_BANKA_ADLARI = {
    "", "-", "none", "null", "bilinmiyor", "bilinmeyen", "bilinmeyen banka",
    "banka", "kurum", "n/a", "na",
}


def banka_kodu_normalize(ham) -> Optional[str]:
    """Elindeki ham değerden (kod, ad, varyant) tanınan bir banka kodu üretir.

    `genel_bilgi.banka_id` -> "kuveytturk" gibi zaten geçerli bir kod olabilir;
    "Kuveyt Türk" / "KUVEYTTURK" gibi bir ad da olabilir. İkisini de çözer.
    """
    if not ham:
        return None
    s = str(ham).strip()
    if s in BANKA_GORUNEN_ADLARI:
        return s
    kod = banka_bul(s)
    if kod:
        return kod
    # "kuveyt_turk" gibi alt çizgili varyantlar
    bosluklu = s.replace("_", " ").strip()
    return banka_bul(bosluklu) if bosluklu != s else None


def banka_kodu_coz(doc: dict) -> Optional[str]:
    """Bir MongoDB kampanya kaydından banka kodunu çıkarır.

    🛠️ HATA DÜZELTMESİ (gerçek veriyle doğrulandı — mongo_kontrol.py çıktısı):
    Kod şimdiye kadar ÜST SEVİYE `banka_kodu` alanına bakıyordu ama
    `smartdata.islenmis_kampanyalar` koleksiyonunda 344 kaydın HİÇBİRİNDE bu alan
    YOK (indeksi var, alanı yok). Gerçek değer `genel_bilgi.banka_id` içinde ve
    tam olarak beklenen kodlarla yazılmış: albaraka, kuveytturk, turkiye_finans,
    emlak_katilim, hayat_finans, dunya_katilim, tom_katilim.

    Sonuçları: (a) sohbet tarafındaki banka filtresi HİÇ eşleşmiyor, "Kuveyt
    Türk'ün kampanyaları" sorusuna tüm bankalardan sonuç dönüyordu; (b)
    indexing.py Qdrant'a "Banka: Bilinmeyen Banka" yazıyor, vektör aramada
    banka filtresi de çalışmıyordu.

    Öncelik: üst seviye banka_kodu -> genel_bilgi.banka_id -> banka_adi/banka
    -> _id öneki ("kamp_kuveytturk_6a87..." gibi).
    """
    if not isinstance(doc, dict):
        return None
    genel = doc.get("genel_bilgi") or {}

    for aday in (doc.get("banka_kodu"), genel.get("banka_id"),
                 genel.get("banka_kodu"), doc.get("banka_adi"), doc.get("banka")):
        if isinstance(aday, dict):
            aday = aday.get("kisa_ad") or aday.get("ad")
        kod = banka_kodu_normalize(aday)
        if kod:
            return kod

    # Son çare: _id "kamp_<banka_kodu>_<hash>" biçiminde olabiliyor.
    ham_id = str(doc.get("_id") or "")
    if ham_id:
        govde = ham_id[5:] if ham_id.startswith("kamp_") else ham_id
        for kod in BANKA_GORUNEN_ADLARI:
            if govde.startswith(kod):
                return kod
    return None


def banka_adi_getir(banka_kodu: Optional[str] = None, ham_ad=None) -> str:
    """Bir kampanya kaydı için kullanıcıya GÖSTERİLECEK banka adını üretir."""
    kod = banka_kodu if banka_kodu in BANKA_GORUNEN_ADLARI else None

    ham_metin = "" if ham_ad is None else str(ham_ad).strip()
    if not kod and ham_metin:
        kod = banka_bul(ham_metin)

    if not kod and banka_kodu:
        kod = banka_bul(str(banka_kodu))

    if kod and kod in BANKA_GORUNEN_ADLARI:
        return BANKA_GORUNEN_ADLARI[kod]

    if ham_metin and tr_lower(ham_metin) not in _ANLAMSIZ_BANKA_ADLARI:
        return ham_metin

    return "Bilinmeyen Banka"


def statik_yanit_bul(soru: str, dil: str = "tr") -> Optional[str]:
    s = tr_lower(soru.strip())
    if len(s.split()) <= 5:
        for intent_name, pattern in _STATIK_PATTERNS:
            if pattern.search(s):
                return statik_metin(intent_name, dil_normalize(dil))
    return None


_TR_BINLIK_DESENI = re.compile(r'^\d{1,3}(\.\d{3})+$')


def _sayi_ayikla(ham: str) -> float:
    """'10.000,50' / '100.000' / '50000.5' / '2,99' gibi TR/EN karışık sayı
    yazımlarını float'a çevirir."""
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
    """Taksit hesabı isteyen bir sorudan (tutar, vade, oran) çıkarmaya çalışır."""
    tutar_m = _TUTAR_DESENI.search(soru)
    vade_m = _VADE_DESENI.search(soru)
    oran_m = _ORAN_DESENI.search(soru)
    tutar = _sayi_ayikla(tutar_m.group(1)) if tutar_m else None
    vade = int(_sayi_ayikla(vade_m.group(1))) if vade_m else None
    oran = None
    if oran_m:
        oran = _sayi_ayikla(oran_m.group(1) or oran_m.group(2) or oran_m.group(3))
    return tutar, vade, oran


# -----------------------------------------------------------------------------
# 7. GÖRSELLEŞTİRME KARARI
# -----------------------------------------------------------------------------

# 🛠️ Eski kod limiti düz `\b(\d+)\b` ile arıyordu: "%2,99 oranla" sorusunda 2'yi,
# "100.000 TL" sorusunda 100'ü limit sanıp tabloyu 2 ya da 100 satıra kırpıyordu.
# Artık yüzdelerin, ondalıkların, para tutarlarının ve ay/yıl gibi birimlerin
# parçası olan sayılar limit olarak KABUL EDİLMİYOR.
# 🛠️ "BANKA" SAYISI, SATIR SAYISI DEĞİLDİR.
# Dashboard'dan gelen "Seçili 4 bankanın her birini ele al" ifadesinde 4,
# kaç satır gösterileceğini değil kaç banka seçildiğini anlatıyor; eski
# kalıp bunu limit sanıp 4 bankalık kıyası 4 SATIRA kırpıyordu. Aynı tuzak
# kullanıcının kendi yazdığı "3 bankayı karşılaştır" cümlesinde de vardı.
# (Aynı gerekçeyle "tüm bankalar" da kapsam sayılıyor — bkz.
# _TUMU_BANKA_KAPSAMI.)
_LIMIT_SAYI_DESENI = re.compile(
    r'(?<![%\d.,])\b(\d{1,4})\b'
    r'(?![.,]?\d)'
    r'(?!\s*(?:%|ay\w*|y[ıi]l\w*|month|year|tl|try|lira|₺'
    r'|banka\w*|bank\w*|adet\s+banka))',
    re.IGNORECASE,
)


# 🛠️ "TÜMÜ" NEYİ KAPSIYOR — satırları mı, bankaları mı?
#
# 500'lük koşuda ölçüldü: "peki tüm bankalarda durum ne" sorusuna 311 SATIRLIK
# bir tablo geldi. Sebep: TUMU_ISTEGI cümledeki "tüm" kelimesini görüp
# istenen_limit'i -1 ("hepsini listele") yapıyor. Oysa kullanıcı satır sayısı
# değil KAPSAM belirtti: "tüm bankalar" = filtre yok demek, "her kampanyayı tek
# tek göster" demek değil. Aradaki fark ekranda 311 satır ile 40 satır farkı.
#
# Bu kalıp yalnızca niceleyicinin BANKA'yı nitelediği hâlleri temizliyor;
# "tüm kampanyaları listele" -1 olmaya devam ediyor.
_TUMU_BANKA_KAPSAMI = re.compile(
    r"\b(?:t[üu]m|b[üu]t[üu]n|her|hepsi)\s*(?:bir\s+)?banka\w*"
    r"|\ball\s+(?:the\s+)?banks?\b|\bevery\s+bank\b|\bacross\s+(?:all\s+)?banks?\b",
    re.IGNORECASE)


def istenen_limit(soru: str) -> Optional[int]:
    """Kullanıcının açıkça istediği satır sayısını çıkarır.
    "150 tanesini göster" -> 150 | "tüm kampanyalar" -> -1 (tümü) | yoksa None.
    """
    # "tüm BANKALAR" bir kapsam ifadesidir, satır sayısı isteği değil.
    if TUMU_ISTEGI.search(_TUMU_BANKA_KAPSAMI.sub(" ", soru or "")):
        return -1
    for m in _LIMIT_SAYI_DESENI.finditer(soru):
        deger = int(m.group(1))
        if 1 <= deger <= 500:
            return deger
    return None


# =============================================================================
# 🚨 GÖRSEL REDDİ — "tablo verme", "grafik istemiyorum"
#
# 200 promptluk testte bulundu. En kötü örnek:
#     "tablo ya da grafik verme, sadece anlat: kampanya koşulları neler"
#     -> DOUGHNUT GRAFİK geldi.
# Sebep: GRAFIK_ISTEGI deseni cümledeki "grafik" kelimesini görüp isteğe
# çeviriyordu; olumsuzluk eki hiç incelenmiyordu. Aynısı "kısaca özetler
# misin, tablo istemiyorum" -> 10 satırlık tablo.
#
# Kullanıcının açık talimatını tersine çevirmek, hiç görsel vermemekten çok
# daha kötü: sistem "seni dinlemiyorum" mesajı veriyor.
#
# Desen, olumsuzluğu görselden SONRA arıyor ("grafik VERME") — Türkçede olağan
# sıra bu. Ayrıca "tablo/grafik OLMADAN", "sadece anlat/yazıyla" gibi
# kalıpları da yakalıyor.
GORSEL_REDDI = re.compile(
    r"(?:tablo|grafi[kğ]\w*|[çc]izelge|liste\w*|g[öo]rsel\w*|chart|table|graph)"
    r"(?:\s+(?:ya\s+da|veya|ve|,)\s*(?:tablo|grafi[kğ]\w*|liste\w*|g[öo]rsel\w*))*"
    r"\s*"
    r"(?:verme|isteme|istemiyorum|istemem|olmadan|olmasın|gerekmiyor|gerek\s*yok|"
    r"[çc]izme|g[öo]sterme|koyma|ekleme|yok|hay[ıi]r)"
    r"|(?:sadece|yaln[ıi]zca|sade[cn]e)\s+(?:anlat|yaz[ıi]yla|metin|c[üu]mle|a[çc][ıi]kla|s[öo]zel)"
    r"|\bno\s+(?:table|chart|graph|visual)\b"
    r"|\b(?:without|don'?t\s+(?:show|give|include))\s+(?:a\s+)?(?:table|chart|graph|visual)\b"
    r"|\bjust\s+(?:explain|tell|describe)\b",
    re.IGNORECASE,
)


def gorsel_reddedildi(soru: str) -> bool:
    """Kullanıcı açıkça 'tablo/grafik verme' dediyse True."""
    return bool(GORSEL_REDDI.search(soru or ""))


# 🛠️ ŞARTNAMENİN KENDİ ÖRNEK SORUSU TABLO ÜRETMİYORDU.
#
# Şartname s.13, Senaryo 2 birebir şöyle yazıyor:
#     "A Bankası mı daha avantajlı, C Bankası mı?"
# Jürinin belgeden kopyalayıp deneyeceği ilk cümle bu. Eski davranışta:
#   • KARSILASTIRMA_ISTEGI bu yazımı tanımıyordu ("karşılaştır"/"kıyasla"/
#     "hangisi daha" bekliyordu; burada ikisi de yok),
#   • buna karşılık ACIKLAYICI_SORU "avantaj" kökünü yakalıyordu.
# Sonuç: soru bir YORUM sorusu sayılıp `gorsel=None` oluyor, Mongo tablo yolu
# hiç çalışmıyor ve cevap yalnızca vektör aramasından geliyordu. Ölçüldü:
# "Albaraka mı daha avantajlı, Dünya Katılım mı?" -> "Dünya Katılım bankasına
# ait kayıt bulunmamaktadır" (oysa 45 kampanyası var), aynı soru
# "Albaraka ve Dünya Katılım kampanyalarını karşılaştır" diye sorulduğunda
# iki bankalı 10 satırlık tablo geliyordu.
#
# Kural metinden değil, ADI GEÇEN BANKA SAYISINDAN türetiliyor: iki farklı
# banka anıldıysa ve cümlede bir kıyas belirteci varsa, bu tanım gereği bir
# karşılaştırmadır — yorum çerçevesi veriyi gereksiz kılmaz.
_KIYAS_BELIRTECI = re.compile(
    r"\bm[ıiuü]\b|\bdaha\b|\bhangisi\b|\bavantajl[ıi]\w*|\büst[üu]n\w*"
    r"|\biyi\b|\buygun\w*|\bfarkl[ıi]l[ıi]k\w*|\bkar[şs][ıi]la[şs]t[ıi]r\w*"
    r"|\bbetter\b|\bwhich\s+one\b|\bmore\s+advantageous\b|\bvs\.?\b",
    re.IGNORECASE)


def iki_banka_kiyasi(soru: str) -> bool:
    """Cümlede İKİ+ farklı banka anılıyor ve bir kıyas belirteci var mı?

    Doğruysa soru, nasıl yazılmış olursa olsun bir karşılaştırmadır ve tablo
    üretilmelidir (bkz. yukarıdaki not — şartname Senaryo 2).
    """
    if len(bankalari_bul(soru)) < 2:
        return False
    return bool(_KIYAS_BELIRTECI.search(soru))


def gorsel_karari(soru: str, aciklayici: bool = False, kod_sorusu: bool = False) -> Optional[str]:
    """Bu soru için ne çizilmeli: "grafik", "tablo" veya None (hiçbir şey).

    ÖNCELİK SIRASI (kullanıcının istediği davranış):
      1. Açık GRAFİK isteği  -> her şeyi ezer, grafik çizilir.
      2. Açık TABLO/LİSTE isteği -> tablo.
      3. Kod yazma sorusu -> hiçbir şey.
      4. Açıklayıcı/yorum sorusu -> hiçbir şey (metin cevabı verilir).
      5. Sıralama/karşılaştırma sorusu -> tablo (kısa özet).
      6. Metrik/veri içeren normal soru -> tablo (kısa özet).
      7. Diğer -> hiçbir şey.
    """
    # 0. AÇIK RET her şeyi ezer — kullanıcı "verme" dediyse verilmez.
    #    Bu kontrol GRAFIK_ISTEGI'nden ÖNCE olmak zorunda: "grafik verme"
    #    cümlesinde "grafik" kelimesi zaten geçtiği için, sonra bakılırsa
    #    istek sanılıp çizilir (testte tam olarak bu oldu).
    if gorsel_reddedildi(soru):
        return None
    if GRAFIK_ISTEGI.search(soru):
        return "grafik"
    if TABLO_ISTEGI.search(soru):
        return "tablo"
    if kod_sorusu:
        return None
    # 🆕 BANKA DÜZEYİNDE KIYAS — açıklayıcı kontrolünden ÖNCE.
    #
    # 500'lük koşuda bu soru sınıfı İKİ ayrı yoldan tablosuz kalıyordu:
    #   • "hangi bankanın kampanyaları daha avantajlı" -> ACIKLAYICI_SORU'ya
    #     ("avantaj") takılıp None dönüyordu;
    #   • "Albaraka Türk sektörde nerede duruyor"      -> hiçbir kalıba
    #     uymadığı için None kalıp melez LLM katmanına düşüyordu, o da
    #     çoğunlukla "görsel gerekmiyor" diyordu.
    # İkisinin de cevabı tanım gereği bir KIYAS TABLOSUDUR; yorum metni zaten
    # tablonun yanında üretiliyor. Bu yüzden kontrol ortak bir adım.
    #
    # ⚠️ Kalıp BİLEREK dar tutuldu: "rakiplerle kıyaslandığında hangi
    # segmentlerde daha yüksek getiri sağlıyor?" gibi GERÇEK yorum soruları
    # dışarıda kalmalı (bkz. BANKA_KIYAS_SORUSU notu).
    # İki banka adı + kıyas belirteci: yazım ne olursa olsun tablo (şartname
    # Senaryo 2). `aciklayici` kontrolünden ÖNCE olmalı — "avantajlı" kelimesi
    # tam da bu soruları yorum sorusu sanmaya yol açıyordu.
    if BANKA_KIYAS_SORUSU.search(soru) or iki_banka_kiyasi(soru):
        return "tablo"
    if aciklayici:
        return None
    if SIRALAMA_ISTEGI.search(soru) or KARSILASTIRMA_ISTEGI.search(soru):
        return "tablo"
    if VERI_SORUSU.search(soru):
        return "tablo"
    # Son deterministik şans: ağır yazım hatası olan liste/grafik isteği
    # (bkz. bulanik_gorsel_istegi notu). Bu da tutmazsa melez LLM katmanına kalır.
    return bulanik_gorsel_istegi(soru)


# =============================================================================
# BULANIK (FUZZY) KÖK EŞLEŞTİRME — ağır imla hataları için
#
# 🛠️ Canlı testte tek başarısız senaryo şuydu: "bana kmpanyalri lsitele".
# Hiçbir regex kalıbına uymuyor (harfler düşmüş), melez LLM katmanı da 3 saniyede
# "görsel gerekmiyor" dedi — yani kullanıcı liste istedi, hiç liste alamadı.
#
# Regex'i gevşetmek çözüm DEĞİL: `\bl.*e\w*` gibi bir kalıp yüzlerce yanlış
# eşleşme üretir. Bunun yerine kelime kelime BENZERLİK ölçüyoruz (difflib):
# "lsitele" ile "listele" %86 benzer, "kmpanyalri" ile "kampanyalari" %82.
# Sadece 5 harften uzun kelimelere ve dar bir anahtar kök listesine bakıyoruz,
# eşik yüksek (0.82) — yani "kimlere" gibi masum kelimeler eşleşmez.
#
# Bu katman regex'ten SONRA, LLM'den ÖNCE çalışır: deterministik, ~0 maliyetli
# ve test edilebilir. LLM'e yalnızca bu da tutmazsa gidilir.
# =============================================================================
_BULANIK_KOKLER: dict[str, str] = {
    # kök -> hangi görsel türüne işaret ediyor
    "listele": "tablo", "liste": "tablo", "tablo": "tablo", "sirala": "tablo",
    "sırala": "tablo", "goster": "tablo", "göster": "tablo", "dokum": "tablo",
    "döküm": "tablo", "detaylandir": "tablo", "detaylandır": "tablo",
    "grafik": "grafik", "grafigi": "grafik", "grafik": "grafik", "pasta": "grafik",
    "chart": "grafik", "diyagram": "grafik",
}
_BULANIK_ESIK = 0.82
_BULANIK_MIN_UZUNLUK = 5


def bulanik_gorsel_istegi(soru: str) -> Optional[str]:
    """Yazım hatalı bir liste/grafik isteği mi? ("lsitele" -> tablo)

    Döner: "tablo" | "grafik" | None
    """
    if not soru:
        return None
    from difflib import SequenceMatcher

    for kelime in re.findall(r"\w+", tr_lower(soru)):
        if len(kelime) < _BULANIK_MIN_UZUNLUK:
            continue
        for kok, tur in _BULANIK_KOKLER.items():
            if abs(len(kelime) - len(kok)) > 3:
                continue
            if SequenceMatcher(None, kelime, kok).ratio() >= _BULANIK_ESIK:
                return tur
    return None


def gorsel_karari_tam(soru: str) -> Optional[str]:
    """`gorsel_karari`'nın kendi kendine yeten hâli: açıklayıcı/kod sorusu
    tespitini de kendisi yapar.

    niyet_bul() çağrılmadan (ör. generate_response içindeki yedek dallarda ya da
    testlerde) karar vermek gerektiğinde kullanılır — böylece "yorum sorusuna
    grafik çizme" kuralı, çağıran taraf unutsa bile geçerli kalır.
    """
    # 🛠️ AÇIK RET, "açık görsel isteği" sayılmamalı.
    # 500'lük koşuda bulundu: "liste verme, cümleyle anlat" cümlesinde
    # TABLO_ISTEGI deseni "liste" kelimesini görüp acik_gorsel_istegi=True
    # yapıyordu. Bu da aciklayici'yi False'a çeviriyor, o da melez LLM
    # katmanının kapısını açıyordu (llm_gorsel_sorulmali: aciklayici ise
    # SORMA). LLM'e "görsel gerekli mi" diye sorulunca "evet" diyor ve
    # kullanıcının AÇIK REDDİ üç adım sonra sessizce çiğneniyordu.
    _ret = gorsel_reddedildi(soru)
    acik_gorsel_istegi = (not _ret) and bool(
        GRAFIK_ISTEGI.search(soru) or TABLO_ISTEGI.search(soru))
    aciklayici = _ret or (bool(ACIKLAYICI_SORU.search(soru)) and not acik_gorsel_istegi)
    return gorsel_karari(soru, aciklayici=aciklayici,
                         kod_sorusu=bool(KOD_YAZMA_ISTEGI.search(soru)))


# =============================================================================
# METRİK TESPİTİ — hangi sütun sorgulanıyor?
#
# 🛠️ HATA DÜZELTMESİ (canlı testte 6/6 koşuda yakalandı): Genel karşılaştırma
# dalı metriği SABİT "kar_payi_orani" olarak işaretliyordu. Yani "Kuveyt Türk
# ile Albaraka'nın ÖDÜLLERİNİ kıyasla" sorusunda bile tablo KÂR PAYI sütununu
# gösteriyordu. Gerçek veride kâr payı yalnızca 3 kayıtta dolu (hepsi Kuveyt
# Türk) olduğu için iki bankalı kıyaslama sessizce TEK BANKALI 3 satıra
# çöküyordu — analist görünümünün ana işlevi buydu ve tamamen bozuktu.
# =============================================================================
_METRIK_ALANLARI: tuple = (
    ("odul_miktari", re.compile(
        # 🛠️ "kazanç" EKLENDİ: "en yüksek KAZANÇ sağlayan kampanyalar" sorusunda
        # metrik hiç tespit edilemiyor, tablo "Değer" sütununu birimsiz
        # gösteriyordu (500'lük koşuda YANLIŞ METRİK olarak yakalandı).
        # "getiri" BİLEREK yok: kâr payı oranı anlamında da kullanılıyor,
        # eklemek onu ödül sütununa çekerdi.
        r"\b[öo]d[üu]l\w*|\bhediye\w*|\biade\w*|\bnakit\b|\bpuan\w*|\bikramiye\w*"
        r"|\bkazan[çc]\w*|\bkazan[ıi]m\w*"
        r"|\breward\w*|\bcashback\b|\bbonus\w*|\bprize\w*|\bgift\w*"
        r"|\bearning\w*|\bpayout\w*", re.IGNORECASE)),
    ("vade_ay", re.compile(
        r"\bvade\w*|\btaksit\w*|\bs[üu]re\w*|\bmaturity\w*|\bterm\w*|\binstallment\w*",
        re.IGNORECASE)),
    ("kar_payi_orani", re.compile(
        r"k[âa]r\s*pay\w*|\boran\w*|\bfaiz\w*|\bprofit\w*|\binterest\w*|\brate\w*|\bmargin\w*",
        re.IGNORECASE)),
)


def metrik_bul(soru: str):
    """Soruda hangi metrik isteniyor? -> "odul_miktari" | "vade_ay" | "kar_payi_orani" | None

    None dönerse çağıran taraf kendi tespitini yapar (zorlama yapılmaz) — bu,
    "hangi banka daha iyi" gibi metrik belirtmeyen sorularda yanlış bir sütunu
    dayatmamak için bilinçli.
    """
    for alan, desen in _METRIK_ALANLARI:
        if desen.search(soru or ""):
            return alan
    return None


# =============================================================================
# 🏦 ANALİST VERİ SORUSU — banka çalışanına "veri yok" dememek için.
#
# 535 promptluk persona koşusunda ölçüldü. Analist görünümünde şu sorular
# tabloya HİÇ ulaşmıyordu:
#     "bankaların ortalama vadeleri nasıl"      -> "ortalama vade bilgisi YOK"
#     "emekli segmentinde bankalar nasıl konumlanıyor" -> tablo yok
#     "kobi segmentinde pazar dağılımı"         -> "pazar dağılımı bilgisi YOK"
#     "sektörde pazar payları nasıl dağılıyor"  -> "pazar payı bilgisi YOK"
# Hepsinin cevabı elimizde: medyan vade, kategori dağılımı, pazar payı hepsi
# kodda hesaplanıyor. Sorun, sorunun Mongo yoluna hiç girmemesiydi.
#
# İki ayrı kalıp aynı işi yapmaya çalışırken AYRIŞMIŞTI:
#   intent.BANKA_KIYAS_SORUSU        -> tablo çizilsin mi
#   generate_response._BANKA_DUZEYINDE_KIYAS -> kıyas kümesi ne olsun
# Biri "pazar payı"nı tanıyor, diğeri tanımıyordu. Bu projede daha önce tam
# olarak böyle bir kopya ayrışması yaşandı (bkz. intent.py başındaki not).
#
# Bu fonksiyon üçüncü bir kopya DEĞİL: yalnızca ANALİST görünümünde ve yalnızca
# deterministik katman "görsel yok" dediğinde çalışan bir emniyet ağı.
# Müşteri görünümünü hiç etkilemez.
#
# ⚠️ TANIM SORULARI DIŞARIDA: analist de "murabaha nedir" diye sorabilir ve
# ona tablo çizmek yanlış olur.
# =============================================================================
_ANALIST_VERI_ALANI = re.compile(
    r"\bbanka\w*|\bsekt[öo]r\w*|\bpiyasa\w*|\bpazar\w*|\brekabet\w*|\brakip\w*"
    r"|\bsegment\w*|\bkategori\w*|\bportf[öo]y\w*|\bkampanya\w*|\bpay\w*"
    r"|\bhedef\s+kitle\w*|\b[üu]r[üu]n\s+grub\w*|\baksiyon\w*"
    r"|\bbench|\bpeer\w*|\bmarket\b|\bcompetit\w*|\bcategor\w*|\bcampaign\w*"
    r"|\baction\w*|\bstrateg\w*",
    re.IGNORECASE)

_TANIM_SORUSU = re.compile(
    r"\bnedir\b|\bne\s+demek\b|\bne\s+anlama\s+gel\w*|\bne\s+demektir\b"
    r"|\bnas[ıi]l\s+[çc]al[ıi][şs]\w*|\btan[ıi]m[ıi]\b"
    r"|\bwhat\s+(?:is|are|does)\b.{0,24}\bmean\b|\bdefine\b",
    re.IGNORECASE)

# Analist de "nasıl başvurulur", "koşullar neler" diye sorabilir; bunlar SÜREÇ
# sorusudur, veri sorusu değil. Tablo çizmek cevabı iyileştirmez.
_SUREC_SORUSU = re.compile(
    r"\bba[şs]vur\w*|\bko[şs]ul\w*|\b[şs]art\w*|\bgerekli\s+belge|\bbelge\w*\s+neler"
    r"|\bs[üu]re[çc]\w*|\bnas[ıi]l\s+yararlan\w*|\bkimler\s+yararlan\w*"
    r"|\bapply\b|\bcondition\w*|\brequirement\w*|\beligib\w*|\bhow\s+do\s+i\b",
    re.IGNORECASE)

# "…ile KIYASLANDIĞINDA hangi segmentte daha yüksek getiri sağlıyor?" —
# `-dığında/-diğinde` bir ÇERÇEVELEME cümleciğidir, istek değil. "X'i kıyasla"
# ise istektir. Bu ayrım olmadan, projede özellikle not düşülmüş bir yorum
# sorusu tekrar tablo üretmeye başlıyordu.
_CERCEVELEME = re.compile(
    r"k[ıi]yasland[ıi][ğg][ıi]nda|kar[şs][ıi]la[şs]t[ıi]r[ıi]ld[ıi][ğg][ıi]nda"
    r"|de[ğg]erlendirildi[ğg]inde|bak[ıi]ld[ıi][ğg][ıi]nda",
    re.IGNORECASE)

# Veri/agrega ipucu: soru gerçekten bir SAYIYA mı dayanıyor?
_AGREGA_IPUCU = re.compile(
    r"\bda[ğg][ıi]l[ıi]m\w*|\bpay\w*|\bortalama\w*|\bmedyan\w*|\bs[ıi]ra\w*|\bkonum\w*"
    r"|\bka[çç]\b|\bsay[ıi]s[ıi]\w*|\boran\w*|\btablo\w*|\bliste\w*|\banaliz\w*"
    r"|\bk[ıi]yas\w*|\bkar[şs][ıi]la[şs]t[ıi]r\w*|\brekabet\w*|\blider\w*|\ba[çç][ıi][ğg]\w*"
    r"|\beksi\w*|\bbo[şs]luk\w*|\bg[üu][çç]l[üu]\w*|\bzay[ıi]f\w*|\baksiyon\w*|\b[öo]ner\w*"
    r"|\ben\s+(?:y[üu]ksek|d[üu][şs][üu]k|[çç]ok|az|uzun|k[ıi]sa|iyi)"
    r"|\bshare\b|\brank\w*|\bdistribut\w*|\baverage\b|\bmedian\b|\bcompar\w*"
    r"|\bposition\w*|\bgap\w*|\bleader\w*|\bhighest\b|\blowest\b|\bbenchmark\b"
    r"|\bmissing\b|\bsuggest\w*|\banalys\w*|\banalyz\w*|\bconcrete\b",
    re.IGNORECASE)


def analist_veri_sorusu(soru: str) -> bool:
    """Analist görünümünde bu soru veri/tablo gerektiriyor mu?

    Yalnızca `niyet.gorsel is None` kaldığında, son çare olarak sorulur.
    """
    metin = soru or ""
    if (_TANIM_SORUSU.search(metin) or _SUREC_SORUSU.search(metin)
            or _CERCEVELEME.search(metin) or KOD_YAZMA_ISTEGI.search(metin)):
        return False
    if gorsel_reddedildi(metin):          # "tablo verme" dendiyse çizme
        return False
    if anlamsiz_soru(metin) and not bankalari_bul(metin):
        return False
    # Hem VERİ ALANINA değmeli hem de bir AGREGA/karar ipucu taşımalı.
    return bool(_ANALIST_VERI_ALANI.search(metin)
                and _AGREGA_IPUCU.search(metin))


_ANLAMLI_HARF = re.compile(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]")


def anlamsiz_soru(soru: str) -> bool:
    """Girdi bir soru sayılamayacak kadar boş mu? ("a", "?", "...", "🏦", "1234")

    🚨 CANLI EKRANDA GÖRÜLDÜ: kullanıcı tek harf ("a") yazdı; sistem önce
    "böyle bir kampanya bulunmamaktadır" dedi, ARDINDAN 3 satırlık tablo ve
    tam bir piyasa analizi bastı. Kimsenin sormadığı bir rapor üretmek,
    cevap vermemekten daha kötü görünüyor: kullanıcı sistemin kendisini
    dinlemediğini düşünüyor.
    #
    Sebep: deterministik katman doğru karar veriyor (görsel yok), ama melez
    LLM katmanına düşülüyor ve o katman cevap veremeyince "temkinli
    varsayılan" 3 satırlık tabloyu çiziyordu. Anlamsız girdide o kapıya hiç
    gidilmemeli.

    ⚠️ Banka kısaltmaları ("KT") bu fonksiyona TAKILMAZ: çağıran taraf önce
    bankanın tespit edilip edilmediğine bakıyor.
    """
    metin = (soru or "").strip()
    if not metin:
        return True
    harfler = _ANLAMLI_HARF.findall(metin)
    # 3 harften az: "a", "?", "...", "🏦", "1234567890", "??!"
    return len(harfler) < 3


def llm_gorsel_sorulmali(niyet: "Niyet") -> bool:
    """MELEZ KAPI: deterministik karar yetersiz kaldı mı, LLM'e sorulsun mu?

    Sorulur  -> regex hiçbir görsel gerekçesi bulamadı ama soru kampanya
                verisiyle ilgili olabilir (kalıp dışı ifade ihtimali):
                "bunların bir dökümünü çıkarabilir misin", "hepsini yan yana koy".
    SORULMAZ -> (her biri bilinçli, gecikmeyi boşa harcamamak için)
      • regex zaten karar verdiyse (grafik/tablo)          -> LLM'e gerek yok
      • soru açıkça YORUM/AÇIKLAMA sorusuysa               -> kullanıcı zaten
        "sadece istendiğinde görsel" davranışını istedi; burada LLM'e sormak
        yorum sorularına tablo geri gelmesi riskini doğurur
      • kod yazma sorusuysa                                -> veri sorusu değil
      • statik/tavsiye/hesaplama niyetiyse                 -> bu dallar zaten
        LLM'e hiç girmeden anında cevaplanıyor
    """
    if niyet.gorsel is not None:
        return False
    if niyet.aciklayici or niyet.kod_sorusu:
        return False
    # Bu niyetler kendi çıktısını (statik metin ya da kendi ürün tablosunu)
    # üretiyor; LLM'e ayrıca "grafik çizeyim mi" diye sormanın anlamı yok.
    if niyet.tur in ("statik", "tavsiye", "finansman", "katilim"):
        return False
    # 🚨 ANLAMSIZ GİRDİDE MELEZ KATMANA HİÇ GİTME (bkz. anlamsiz_soru).
    # Banka kısaltması tespit edildiyse girdi anlamlıdır ("KT").
    if not niyet.banka_kodlari and anlamsiz_soru(niyet.ham_soru):
        return False
    return True


def gorsel_limiti(
    soru: str,
    gorsel: Optional[str],
    view_mode: str = "musteri",
    acik_istek_zorla: bool = False,
) -> int:
    """Görselde kaç satır gösterileceğini belirler.

    Kullanıcının tarif ettiği davranış: normal sorularda KISA (3 satır) bir özet
    tablo; kullanıcı açıkça liste/tablo/grafik istediğinde daha geniş bir liste;
    "tümü" veya bir sayı verdiyse tam olarak o kadar.

    `acik_istek_zorla`: kararı MELEZ katman (LLM ajanı) verdiyse True geçilir.
    Çünkü o durumda kullanıcı listeyi kalıp DIŞI bir ifadeyle istemiştir
    ("bunların dökümünü çıkar") — regex "açık istek yok" der ama aslında vardır;
    3 satırlık özete kırpmak kullanıcının istediğini vermemek olur.
    """
    acik_limit = istenen_limit(soru)
    if acik_limit == -1:
        return 10 ** 6  # pratikte "tümü" (üst sınırı Mongo çekim limiti belirler)
    if acik_limit:
        return acik_limit
    if gorsel is None:
        return OZET_SATIR_SAYISI
    # Açık liste/tablo/grafik isteği var mı?
    # 🛠️ Bulanık eşleşme de AÇIK istek sayılır: "lsitele" yazan kullanıcı da
    # listeyi açıkça istemiştir, 3 satırlık özete kırpmak yanlış olur.
    acik_istek = (
        acik_istek_zorla
        or bool(GRAFIK_ISTEGI.search(soru) or TABLO_ISTEGI.search(soru))
        or bulanik_gorsel_istegi(soru) is not None
    )
    if not acik_istek:
        return OZET_SATIR_SAYISI
    return VARSAYILAN_LISTE_LIMITI_ANALIST if view_mode != "musteri" else VARSAYILAN_LISTE_LIMITI


# -----------------------------------------------------------------------------
# 8. ANA NIYET TESPIT MOTORU
# -----------------------------------------------------------------------------

def niyet_bul(soru: str, gecmis: Sequence[Mesaj] = (), dil: str = "tr") -> Niyet:
    dil = dil_normalize(dil)
    s_tr = tr_lower(soru)
    banka_kodlari = bankalari_bul(soru)
    banka = banka_kodlari[0] if banka_kodlari else None

    statik_cevap = statik_yanit_bul(soru, dil)
    if statik_cevap:
        return Niyet("statik", statik_cevap=statik_cevap, ham_soru=soru, dil=dil)

    if _TAVSIYE.search(s_tr):
        return Niyet(
            "tavsiye", statik_cevap=statik_metin("tavsiye_red", dil),
            banka_kodu=banka, ham_soru=soru, dil=dil,
        )

    # 🏦 ÜRÜN VERİSİ — hesaplama YOK, doğrudan veritabanı kayıtları.
    #
    # Sıra önemli: katılım (mevduat) ÖNCE bakılıyor. "katılım hesabı ... aylık
    # taksit" gibi karışık bir cümlede ürün mevduattır; finansman kalıbının
    # önce eşleşmesi, eski hatanın (mevduatı krediye çevirme) tekrarı olurdu.
    # `kiyas_genis` bu daldan da çıkmalı: "diğer katılım bankalarıyla ve sektör
    # ortalamasıyla karşılaştır" diyen bir soruda banka filtresi uygulanırsa
    # geriye tek banka kalır ve kıyas diye bir şey kalmaz. (Aşağıdaki kampanya
    # akışı bunu zaten hesaplıyordu; ürün dalları oraya varmadan döndüğü için
    # burada ayrıca hesaplanıyor.)
    _urun_kiyas = bool(RAKIP_KIYAS.search(soru))
    _urun_bankalari = bankalari_bul(soru)
    # "kampanya" geçen cümleler kampanya akışına ait (bkz. _URUN_METRIGI notu).
    _kampanya_sorusu = bool(_KAMPANYA_KELIMESI.search(s_tr))

    if _KATILIM_URUNU.search(s_tr) and not _kampanya_sorusu:
        tutar, vade, oran = hesaplama_parametreleri_cikar(soru)
        return Niyet("katilim", banka_kodu=banka, tutar=tutar, vade=vade,
                     oran=oran, ham_soru=soru, dil=dil,
                     banka_kodlari=_urun_bankalari, kiyas_genis=_urun_kiyas)

    # Açık ürün ifadesi ("konut finansmanı") YA DA finansman/kredi + ürün
    # metriği ("en uzun VADE sunan FİNANSMAN"). İkisi de "kampanya" geçmemesi
    # koşuluna bağlı.
    _finansman_urunu = not _kampanya_sorusu and (
        bool(_FINANSMAN_URUNU.search(s_tr))
        or bool(_FINANSMAN_KELIMESI.search(s_tr) and _URUN_METRIGI.search(s_tr))
    )
    if _finansman_urunu:
        tutar, vade, oran = hesaplama_parametreleri_cikar(soru)
        return Niyet("finansman", banka_kodu=banka, tutar=tutar, vade=vade,
                     oran=oran, ham_soru=soru, dil=dil,
                     banka_kodlari=_urun_bankalari, kiyas_genis=_urun_kiyas)

    # Eski `hesaplama` niyetinin tetikleyicisi ("50.000 TL 24 ay ... hesapla").
    # Artık hesap YAPILMIYOR; aynı soru finansman kayıtlarına yönlendiriliyor.
    # Katılım kontrolü yukarıda yapıldığı için mevduat soruları buraya düşmez.
    if _HESAP_DILI.search(s_tr):
        tutar, vade, oran = hesaplama_parametreleri_cikar(soru)
        if tutar and vade:
            return Niyet("finansman", banka_kodu=banka, tutar=tutar, vade=vade,
                         oran=oran, ham_soru=soru, dil=dil,
                         banka_kodlari=_urun_bankalari, kiyas_genis=_urun_kiyas)

    devam = bool(gecmis) and bool(_DEVAM.search(soru))
    baglam_soru = None

    if devam:
        parcalar = [m.icerik for m in reversed(gecmis) if m.rol == "user"]
        baglam_soru = " ".join(reversed(parcalar[:2])) if parcalar else None

    # Banka mirası: sohbette geçmiş varsa ve mevcut mesaj kendi başına farklı/yeni
    # bir banka belirtmiyorsa (ve açıkça "hangi banka(lar)" diye SORMUYORSA) en son
    # bahsedilen banka otomatik devralınır.
    # "rakiplerle kıyasla" -> filtre kapalı (bkz. RAKIP_KIYAS notu). Bankanın adı
    # yine de tespit ediliyor (cevapta odak bankası olarak anılabilsin diye), ama
    # aşağıdaki filtreleme bu bayrağa bakarak devre dışı kalıyor.
    kiyas_genis = bool(RAKIP_KIYAS.search(soru))

    # 🚨 ADI GEÇEN KÜME, "rakip/sektör" KELİMESİNDEN ÜSTÜNDÜR.
    #
    # `kiyas_genis` banka filtresini TAMAMEN kapatıyor. Amacı "biz Kuveyt
    # Türk'üz, RAKİPLERLE kıyasla" durumu: tek banka adı geçer, kıyas için
    # diğerleri de gerekir. Ama kullanıcı İKİ YA DA DAHA FAZLA bankayı ADIYLA
    # saydıysa kıyas kümesini zaten kendisi tanımlamıştır; cümlede "sektör"
    # ya da "rakip" geçmesi bu seçimi silmemeli.
    #
    # Ölçülen etki: dashboard'dan 2 banka seçilip gelen istekte cümlenin
    # sonundaki "...sektördeki konumlarını yorumla" ifadesi filtreyi kapatıyor,
    # tabloya 5 banka geliyordu — kullanıcı 2 banka işaretlemişken.
    if kiyas_genis and len(banka_kodlari) > 1:
        kiyas_genis = False

    if banka is None and bool(gecmis) and not _BANKA_SORGUSU.search(soru) and not kiyas_genis:
        for m in reversed(gecmis):
            if m.rol == "user":
                # 🚨 HATA DÜZELTMESİ: burada banka_bul() (TEKİL) kullanılıyordu.
                #
                # Bildirilen hata: kullanıcı önce "albaraka ile kuveyt türkü
                # karşılaştır" dedi (çalıştı), ardından "iki bankanın tüm
                # kampanyalarını karşılaştır" dedi. İkinci mesajda banka ADI
                # geçmediği için geçmişten devralınıyor — ama banka_bul() yalnızca
                # İLK bankayı döndürdüğü için Kuveyt Türk sessizce kayboluyordu.
                # Sonuç zinciri: banka_kodlari=['albaraka'] -> çok bankalı kıyas
                # koşulu sağlanmıyor -> ajanın metrik tahmini iptal edilmiyor ->
                # havuz kar_payi>0 filtresiyle 0 kayda düşüyor -> hiç tablo
                # üretilemiyor -> sistem vektör aramaya düşüyor ve model
                # "Kuveyt Türk'e ait veri yok" diyordu.
                #
                # Kıyaslama sorusunda geçmişten TEK banka devralmak, kıyaslamayı
                # tanım gereği imkânsız kılar; bahsedilen bankaların HEPSİ alınmalı.
                kodlar_gecmis = bankalari_bul(m.icerik)
                if kodlar_gecmis:
                    banka_kodlari = kodlar_gecmis
                    banka = kodlar_gecmis[0]
                    break

    kod_sorusu = bool(KOD_YAZMA_ISTEGI.search(soru))
    # Açık bir grafik/tablo isteği, açıklayıcı kalıpları EZER: "bu kampanyanın
    # koşullarını tablo hâlinde göster" hem açıklayıcı hem de açık tablo isteğidir.
    # 🛠️ AÇIK RET, "açık görsel isteği" sayılmamalı.
    # 500'lük koşuda bulundu: "liste verme, cümleyle anlat" cümlesinde
    # TABLO_ISTEGI deseni "liste" kelimesini görüp acik_gorsel_istegi=True
    # yapıyordu. Bu da aciklayici'yi False'a çeviriyor, o da melez LLM
    # katmanının kapısını açıyordu (llm_gorsel_sorulmali: aciklayici ise
    # SORMA). LLM'e "görsel gerekli mi" diye sorulunca "evet" diyor ve
    # kullanıcının AÇIK REDDİ üç adım sonra sessizce çiğneniyordu.
    _ret = gorsel_reddedildi(soru)
    acik_gorsel_istegi = (not _ret) and bool(
        GRAFIK_ISTEGI.search(soru) or TABLO_ISTEGI.search(soru))
    aciklayici = _ret or (bool(ACIKLAYICI_SORU.search(soru)) and not acik_gorsel_istegi)

    # 🆕 BANKA EKLEME — "Albaraka'yı da ekle" kümeyi GENİŞLETİR.
    # Yukarıdaki banka mirası yalnızca mevcut mesajda HİÇ banka geçmediğinde
    # çalışıyor. "Albaraka'yı da ekle" cümlesinde banka GEÇİYOR, dolayısıyla
    # miras devreye girmiyor ve önceki bankayı (Kuveyt Türk) sessizce
    # düşürüyorduk — oysa kullanıcı "ekle" dedi, "değiştir" değil.
    if banka_kodlari and gecmis and _EKLEME.search(soru) and not kiyas_genis:
        for _m in reversed(gecmis):
            if _m.rol != "user":
                continue
            _onceki = bankalari_bul(_m.icerik)
            if _onceki:
                _birlesik = list(dict.fromkeys(_onceki + banka_kodlari))
                if len(_birlesik) > len(banka_kodlari):
                    banka_kodlari = _birlesik
                    banka = banka_kodlari[0]
                break

    gorsel = gorsel_karari(soru, aciklayici=aciklayici, kod_sorusu=kod_sorusu)

    # 🆕 GÖRSEL MİRASI — takip sorularında.
    #
    # 500'lük koşuda üç senaryo aynı sebepten hiç tablo alamadı:
    #     "Albaraka Türk için de aynısını yap"
    #     "Albaraka'yı da ekle"
    #     "yanlış anladın, Albaraka demek istedim"
    # Üçünde de önceki turda tablo çizilmişti. Bu mesajlarda "listele/tablo/
    # göster" gibi bir kelime YOK; deterministik katman haklı olarak karar
    # veremiyor, melez LLM ajanı da (geçmişi görmediği için) "görsel
    # gerekmiyor" diyor. Oysa kullanıcı EKRANDA AZ ÖNCE GÖRDÜĞÜ şeyi
    # kastediyor ve yalnızca odağı değiştiriyor.
    #
    # Kural: mesaj kendi başına karar üretmiyorsa ve (a) bir devam/ekleme
    # ifadesiyse ya da (b) bir banka adı geçiriyorsa, geçmişte gerçekten
    # görsel ÜRETMİŞ en son kullanıcı mesajının kararı devralınır.
    # Yorum ve kod sorularında devralma YAPILMAZ — "peki bunu açıklar mısın"
    # dendiğinde aynı tabloyu tekrar basmak kullanıcıyı boğar.
    _gorsel_kaynagi = "regex"
    if (gorsel is None and gecmis and not aciklayici and not kod_sorusu
            and (_DEVAM.search(soru) or _EKLEME.search(soru) or bankalari_bul(soru))):
        for _m in reversed(gecmis):
            if _m.rol != "user":
                continue
            _miras = gorsel_karari_tam(_m.icerik or "")
            if _miras:
                gorsel = _miras
                # Kaynağı işaretle: generate_response satır limitini buna göre
                # seçiyor. Devralınan görsel AÇIK bir liste isteğinden geliyorsa
                # 3 satırlık özete kırpmak yanlış olur (bkz. gorsel_kaynagi).
                _gorsel_kaynagi = "miras"
                break

    limit = istenen_limit(soru)

    ortak = dict(
        banka_kodu=banka, banka_kodlari=banka_kodlari, kiyas_genis=kiyas_genis,
        ham_soru=soru, baglam_soru=baglam_soru,
        gorsel=gorsel, limit_istegi=limit, aciklayici=aciklayici,
        kod_sorusu=kod_sorusu, dil=dil, gorsel_kaynagi=_gorsel_kaynagi,
    )

    # 🛠️ Karşılaştırma alanı (kar_payi/odul/vade) YALNIZCA gerçekten bir
    # sıralama/karşılaştırma isteniyorsa atanır. Eskiden "…kıyaslandığında hangi
    # segmentte daha yüksek getiri sağlıyor?" gibi bir YORUM sorusu da buraya
    # düşüyor, alan="kar_payi_orani" olarak işaretleniyor ve kâr payı grafiği
    # zorlanıyordu (bildirilen 3. sorun).
    if not aciklayici and not kod_sorusu:
        for alan, desen in _KARSILASTIRMA_ALANLARI:
            if desen.search(soru):
                return Niyet("karsilastirma", alan=alan, **ortak)

        if KARSILASTIRMA_ISTEGI.search(soru):
            # 🛠️ Metrik artık SORUDAN okunuyor (eskiden sabit "kar_payi_orani"ydı).
            # Soruda metrik geçmiyorsa alan=None bırakılıyor; bu durumda
            # generate_response kendi tespitini yapar, yanlış sütun dayatılmaz.
            return Niyet("karsilastirma", alan=metrik_bul(soru), **ortak)

    # 🚨 İKİ BANKA ADI GEÇİYORSA TABLO ŞART.
    #
    # 535'lik koşuda ölçüldü:
    #     soru  : "Albaraka Türk ve Hayat Finans'tan hangisi"
    #     cevap : "Hayat Finans'a ait herhangi bir kampanya kaydı MEVCUT
    #              DEĞİLDİR; iki bankayı karşılaştırmam mümkün değil"
    #     veri  : Hayat Finans'ın 10 kampanyası VAR
    # Cümlede "karşılaştır/kıyasla" fiili geçmediği için görsel kararı None
    # kaldı, Mongo yolu çalışmadı ve model yalnızca vektör aramasından gelen
    # Albaraka parçalarını gördü — göremediği bankayı "yok" saydı.
    #
    # Kullanıcı iki bankayı YAN YANA ANDIYSA kıyas istiyordur; fiil aramaya
    # gerek yok. Bu, "kıyaslamada eksik banka" hatalarının kökündeki desendi.
    if ortak["gorsel"] is None and len(banka_kodlari) > 1 and not aciklayici:
        ortak["gorsel"] = "tablo"

    if banka and _LISTE.search(soru):
        # 🛠️ "Türkiye Finans'ta neler var" niyeti banka_listesi olarak DOĞRU
        # sınıflandırılıyordu ama gorsel=None kalıyordu: cümlede "listele/
        # tablo" geçmiyor, VERI_SORUSU kalıbına da uymuyor. Sonuç: bir LİSTE
        # niyeti tespit edilmiş olmasına rağmen ekrana hiçbir liste gelmiyordu.
        # Niyetin adı "banka_listesi" ise görselin tablo olması gerekir.
        if ortak["gorsel"] is None:
            ortak["gorsel"] = "tablo"
        return Niyet("banka_listesi", **ortak)

    return Niyet("kampanya_soru", **ortak)


# -----------------------------------------------------------------------------
# 9. KONUŞMA GEÇMİŞİ FORMATLAYICI (RAG prompt'una beslemek için)
# -----------------------------------------------------------------------------

def gecmis_metni_olustur(gecmis: Sequence[Mesaj], limit: int = 6, max_uzunluk: int = 400,
                         dil: str = "tr") -> str:
    """Son konuşma geçmişini prompt'taki {gecmis} yerine geçecek şekilde formatlar.

    🌍 `dil` eklendi: İngilizce modda başlık ve rol etiketleri de İngilizce
    üretiliyor. Aksi hâlde promptun içinde "GEÇMİŞ KONUŞMA / Kullanıcı: ..."
    diye Türkçe bir blok kalıyor ve modeli Türkçe cevaba çekiyordu."""
    if not gecmis:
        return ""
    ingilizce = dil_normalize(dil) == "en"
    son_mesajlar = list(gecmis)[-limit:]
    satirlar = []
    for m in son_mesajlar:
        icerik = (m.icerik or "").strip()
        if not icerik:
            continue
        if len(icerik) > max_uzunluk:
            icerik = icerik[:max_uzunluk] + "..."
        if ingilizce:
            rol = "User" if m.rol == "user" else "Assistant"
        else:
            rol = "Kullanıcı" if m.rol == "user" else "Asistan"
        satirlar.append(f"{rol}: {icerik}")
    if not satirlar:
        return ""
    baslik = ("CONVERSATION HISTORY (for context — shape your answer accordingly):"
              if ingilizce else
              "GEÇMİŞ KONUŞMA (bağlam için, cevabı buna göre şekillendir):")
    return baslik + "\n" + "\n".join(satirlar) + "\n\n"