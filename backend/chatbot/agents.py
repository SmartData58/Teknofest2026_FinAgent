import os
import re
import json
import asyncio
from loguru import logger
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

LANGCHAIN_OLLAMA_BASE_URL = os.getenv("LANGCHAIN_OLLAMA_BASE_URL", "http://llm:11434")

# SQL/JSON çıktı gerektiren ajanlar için temperature 0 (Net), serbest üretim için 0.3
llm_json = ChatOllama(model="qwen3.5:4b", temperature=0, base_url=LANGCHAIN_OLLAMA_BASE_URL)
llm_text = ChatOllama(model="qwen3.5:4b", temperature=0.3, base_url=LANGCHAIN_OLLAMA_BASE_URL)

# =============================================================================
# 1. ROUTING (Thinking Decider) — Sorgu derin RAG (HyDE+Step-Back+Multi-Query)
#    gerektiriyor mu, yoksa basit/direkt bir arama mı yeterli, karar verir.
# =============================================================================
thinking_decider_prompt = PromptTemplate(
    template="""Sen zeki bir analiz motorusun. Kullanıcının sorusunu analiz et. Soru finansal hesaplama, banka karşılaştırması, detaylı veri analizi veya karmaşık bir mantıksal yorum gerektiriyorsa true dön. Basit bir selamlaşma, kısa bilgi veya direkt bir soru ise false dön.
    Soru: {question}
    SADECE JSON FORMATINDA DÖN: {{"thinking": true}} VEYA {{"thinking": false}}
    """,
    input_variables=["question"]
)
thinking_decider_chain = thinking_decider_prompt | llm_json | StrOutputParser()

# =============================================================================
# 2. HyDE (Hypothetical Document Embeddings — Varsayımsal Belge)
# =============================================================================
hyde_prompt = PromptTemplate(
    template="""Lütfen aşağıdaki bankacılık veya kampanya sorusuna cevap olabilecek, sanki resmi bir banka belgesiymiş gibi kısa ve varsayımsal bir paragraf yaz. Bu metin arama motorunda benzerlerini bulmak için kullanılacaktır.
    Soru: {question}
    Varsayımsal Resmi Belge Metni:""",
    input_variables=["question"]
)
hyde_chain = hyde_prompt | llm_text | StrOutputParser()

# =============================================================================
# 3. STEP-BACK (Soyutlama / Genişletme)
# =============================================================================
step_back_prompt = PromptTemplate(
    template="""Aşağıdaki spesifik bankacılık sorusunu, arka plandaki daha genel, temel prensibi veya şartları araştıran soyut (step-back) bir soruya dönüştür.
    Spesifik Soru: {question}
    Genel ve Kapsayıcı Soru:""",
    input_variables=["question"]
)
step_back_chain = step_back_prompt | llm_text | StrOutputParser()

# =============================================================================
# 4. MULTI-QUERY (Çoklu Sorgu Üretimi)
# =============================================================================
mq_prompt = PromptTemplate(
    template="""Soruyu bankacılık araması için 3 farklı şekilde yaz. JSON dön: {{"queries": ["1", "2", "3"]}}
    Soru: {question}
    """,
    input_variables=["question"]
)
mq_chain = mq_prompt | llm_json | StrOutputParser()

# =============================================================================
# OTONOM TEXT-TO-MONGO AJANI (yapılandırılmış analiz sorguları için)
# =============================================================================
sql_agent_prompt = PromptTemplate(
    template="""Sen kıdemli bir Veritabanı uzmanısın. Kullanıcının sorusunu analiz et.
    Mevcut Sütunlarımız:
    1. "kar_payi": Kâr payı, faiz, finansman oranı
    2. "vade": Taksit, ay
    3. "odul_tutari_tl": Para ödülü, hediye TL

    Soru: {question}
    SADECE AŞAĞIDAKİ FORMATTA JSON DÖN:
    {{
        "hedef_sutun": "kar_payi VEYA vade VEYA odul_tutari_tl",
        "kategori": "kart VEYA taşıt VEYA konut VEYA ihtiyaç VEYA hepsi",
        "prefix": "Birim öneki",
        "suffix": "Birim soneki",
        "title": "Grafik Başlığı"
    }}
    """,
    input_variables=["question"]
)
sql_agent_chain = sql_agent_prompt | llm_json | StrOutputParser()

# =============================================================================
# ÖNERİ MOTORU (Suggestions)
# =============================================================================
suggestion_prompt = PromptTemplate(
    template="""Aşağıdaki kullanıcı sorusuna ve yapay zekanın verdiği cevaba bakarak, kullanıcının sohbeti devam ettirmek için sorabileceği EN MANTIKLI 3 kısa soruyu üret.
    Sorular kesinlikle seçilen dile ({language}) uygun olmalıdır.

    Kullanıcı: {question}
    Yapay Zeka: {answer}

    SADECE aşağıdaki formatta 3 adet soru üret. Başka hiçbir kelime, açıklama veya numara ekleme:
    [SUGGESTION]Birinci soru önerisi[/SUGGESTION]
    [SUGGESTION]İkinci soru önerisi[/SUGGESTION]
    [SUGGESTION]Üçüncü soru önerisi[/SUGGESTION]
    """,
    input_variables=["question", "answer", "language"]
)
suggestion_chain = suggestion_prompt | llm_text | StrOutputParser()


# =============================================================================
# YARDIMCI FONKSİYONLAR — Zincirleri güvenli (timeout + hata yönetimi + parse)
# şekilde çağıran sarmalayıcılar. generate_response.py bunları kullanır.
# =============================================================================

def _guvenli_json_liste(text: str, key: str = "queries") -> list:
    """LLM'in serbest metin karıştırdığı JSON çıktısından güvenle bir liste çıkarır."""
    try:
        if not text:
            return []
        temiz = text.strip()
        if "```" in temiz:
            temiz = temiz.replace("```json", "").replace("```", "")
        match = re.search(r"\{.*\}", temiz, re.DOTALL)
        if not match:
            return []
        data = json.loads(match.group(0))
        deger = data.get(key, [])
        if isinstance(deger, list):
            return [str(v).strip() for v in deger if str(v).strip()]
    except Exception as e:
        logger.debug(f"JSON liste ayrıştırma başarısız: {e}")
    return []


def _guvenli_json_bool(text: str, key: str = "thinking") -> bool:
    try:
        if not text:
            return False
        match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
        if not match:
            return False
        data = json.loads(match.group(0))
        return bool(data.get(key, False))
    except Exception as e:
        logger.debug(f"JSON bool ayrıştırma başarısız: {_hata_metni(e)}")
        return False


def _hata_metni(e: Exception) -> str:
    """str(e) bazı istisnalarda (özellikle asyncio.TimeoutError) BOŞ STRING döner,
    bu da log satırlarını 'başarısız oldu: ' gibi anlamsız bırakır. Bu yardımcı,
    log'da her zaman okunabilir bir sebep görünmesini garanti eder."""
    if isinstance(e, asyncio.TimeoutError):
        return "zaman aşımı (timeout) — LLM/servis süresi içinde yanıt vermedi"
    msg = str(e)
    if msg:
        return msg
    return f"{type(e).__name__} (detay yok)"


# -----------------------------------------------------------------------------
# ZAMAN AŞIMI AYARLARI
#
# Yerel/CPU üzerinde çalışan Ollama'da tek bir yanıt 60-90 saniye sürebiliyor
# (ana cevap ölçümlerinde ~76sn). Önceki 15/25 saniyelik değerler bu yüzden
# neredeyse HER istekte timeout'a düşüyor, HyDE / Step-Back / Multi-Query /
# Text-to-Mongo ajanlarının hepsi sessizce devre dışı kalıyordu — loglardaki
# "zaman aşımı" uyarıları tam olarak buydu. Tablo çalışmaya devam ediyordu
# çünkü tablo MongoDB'den geliyor, LLM'den değil.
#
# Değerler artık ortam değişkeninden ayarlanabiliyor ve 0 (veya negatif)
# verilirse zaman aşımı TAMAMEN KAPATILIR (süresiz bekler):
#   AGENT_TIMEOUT_KISA=0   AGENT_TIMEOUT_UZUN=0
#
# ⚠️ Denge: zaman aşımını kapatmak ajanların tamamlanmasını garanti eder ama
# gecikmeyi de artırır. HyDE/Step-Back/Multi-Query birbirine paralel çalışır
# (asyncio.gather), dolayısıyla bu üçü toplamda değil, en yavaşları kadar sürer;
# ancak thinking-decider ve text-to-mongo bunlardan ÖNCE sırayla çalışır.
# Ollama tamamen kilitlenirse istek süresiz asılı kalabilir — bu yüzden
# varsayılan olarak kapatmak yerine cömert bir süre veriyoruz.
# -----------------------------------------------------------------------------

def _timeout_oku(env_adi: str, varsayilan: float) -> float | None:
    ham = os.getenv(env_adi)
    if ham is None:
        return varsayilan
    try:
        deger = float(ham)
    except ValueError:
        logger.warning(f"{env_adi} sayıya çevrilemedi ('{ham}'), varsayılan {varsayilan}s kullanılıyor.")
        return varsayilan
    # 0 veya negatif => zaman aşımı yok (asyncio.wait_for(timeout=None) süresiz bekler)
    return None if deger <= 0 else deger


TIMEOUT_KISA = _timeout_oku("AGENT_TIMEOUT_KISA", 120.0)  # thinking-decider, text-to-mongo
TIMEOUT_UZUN = _timeout_oku("AGENT_TIMEOUT_UZUN", 180.0)  # HyDE / Step-Back / Multi-Query
TIMEOUT_ONERI = _timeout_oku("AGENT_TIMEOUT_ONERI", 120.0)  # öneri (suggestion) motoru


async def derin_dusunme_gerekli_mi(question: str, timeout: float | None = TIMEOUT_KISA) -> bool:
    """Thinking-decider ajanını çağırır: soru derin (HyDE+Step-Back+Multi-Query)
    bir RAG akışı mı gerektiriyor yoksa basit bir arama mı yeterli, karar verir."""
    try:
        raw = await asyncio.wait_for(thinking_decider_chain.ainvoke({"question": question}), timeout=timeout)
        return _guvenli_json_bool(raw)
    except Exception as e:
        logger.warning(f"Thinking-decider ajanı başarısız oldu, basit moda düşülüyor: {_hata_metni(e)}")
        return False


async def hyde_belgesi_uret(question: str, timeout: float | None = TIMEOUT_UZUN) -> str:
    """HyDE: soruya cevap olabilecek varsayımsal bir belge üretir (embedding araması için)."""
    try:
        sonuc = await asyncio.wait_for(hyde_chain.ainvoke({"question": question}), timeout=timeout)
        return (sonuc or "").strip()
    except Exception as e:
        logger.warning(f"HyDE belgesi üretilemedi: {_hata_metni(e)}")
        return ""


async def step_back_sorgu_uret(question: str, timeout: float | None = TIMEOUT_UZUN) -> str:
    """Step-Back: spesifik soruyu daha genel/kapsayıcı bir soruya dönüştürür."""
    try:
        sonuc = await asyncio.wait_for(step_back_chain.ainvoke({"question": question}), timeout=timeout)
        return (sonuc or "").strip()
    except Exception as e:
        logger.warning(f"Step-back sorgusu üretilemedi: {_hata_metni(e)}")
        return ""


async def coklu_sorgu_uret(question: str, timeout: float | None = TIMEOUT_UZUN, limit: int = 3) -> list:
    """Multi-Query: aynı soruyu farklı ifadelerle yeniden yazar (recall'u artırmak için)."""
    try:
        raw = await asyncio.wait_for(mq_chain.ainvoke({"question": question}), timeout=timeout)
        sorgular = _guvenli_json_liste(raw, "queries")
        return sorgular[:limit]
    except Exception as e:
        logger.warning(f"Multi-query üretilemedi: {_hata_metni(e)}")
        return []


async def yapisal_analiz_parametreleri_uret(question: str, timeout: float | None = TIMEOUT_KISA) -> dict:
    """Text-to-Mongo ajanı: karşılaştırma/analiz sorularını yapılandırılmış
    (hedef_sutun, kategori, prefix, suffix, title) parametrelere çevirir."""
    try:
        raw = await asyncio.wait_for(sql_agent_chain.ainvoke({"question": question}), timeout=timeout)
        temiz = (raw or "").replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", temiz, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        logger.warning(f"Yapısal analiz ajanı başarısız: {_hata_metni(e)}")
    return {}