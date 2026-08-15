import os
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

LANGCHAIN_OLLAMA_BASE_URL = os.getenv("LANGCHAIN_OLLAMA_BASE_URL", "http://smartdata-llm-1:11434")

# SQL Ajanı için temperature 0 (Sıfır halüsinasyon, net sonuç)
llm_json = ChatOllama(model="qwen3.5:4b", temperature=0, base_url=LANGCHAIN_OLLAMA_BASE_URL)
llm_text = ChatOllama(model="qwen3.5:4b", temperature=0.1, base_url=LANGCHAIN_OLLAMA_BASE_URL)

# 🚀 YENİ TOKAT: OTONOM DÜŞÜNME KARAR MOTORU
thinking_decider_prompt = PromptTemplate(
    template="""Sen zeki bir analiz motorusun. Kullanıcının sorusunu analiz et. Soru finansal hesaplama, banka karşılaştırması, detaylı veri analizi veya karmaşık bir mantıksal yorum gerektiriyorsa true dön. Basit bir selamlaşma, kısa bilgi veya direkt bir soru ise false dön.
    
    Soru: {question}
    
    SADECE JSON FORMATINDA DÖN: {{"thinking": true}} VEYA {{"thinking": false}}
    """,
    input_variables=["question"]
)
thinking_decider_chain = thinking_decider_prompt | llm_json | StrOutputParser()

router_prompt = PromptTemplate(
    template="""Soruyu analiz et ve JSON dön: {{"intent": "CUSTOMER veya ANALYST veya OUT_OF_BOUNDS", "reason": "neden"}}
    1. OUT_OF_BOUNDS: Bankacılık dışı konular.
    2. CUSTOMER: Kredi hesaplama.
    3. ANALYST: Pazar analizi, grafik, tablo, oran, taksit, vade, ödül listeleme.
    Soru: {query}
    """,
    input_variables=["query"]
)
router_chain = router_prompt | llm_json | StrOutputParser()

mq_prompt = PromptTemplate(
    template="""Soruyu bankacılık araması için 3 farklı şekilde yaz. JSON dön: {{"queries": ["1", "2", "3"]}}
    Soru: {question}
    """,
    input_variables=["question"]
)
mq_chain = mq_prompt | llm_json | StrOutputParser()

tool_prompt = PromptTemplate(
    template="""Hesaplama varsa rakamları çıkar. JSON dön: {{"hesaplama_gerekli_mi": true, "tutar": 140000.0, "vade": 12, "kar_payi": 1.99}}
    Soru: {question}
    """,
    input_variables=["question"]
)
tool_chain = tool_prompt | llm_json | StrOutputParser()

# 🚀 NİHAİ TOKAT: OTONOM TEXT-TO-SQL AJANI!
sql_agent_prompt = PromptTemplate(
    template="""Sen kıdemli bir Veritabanı ve Veri Analizi uzmanısın. Kullanıcının sorusunu analiz et ve tablodan HANGİ sütunun çekileceğine, birimlerin ne olacağına karar ver.

    Mevcut Sütunlarımız (SADECE BUNLARI SEÇEBİLİRSİN):
    1. "kar_payi": Kâr payı, faiz, finansman oranı (Örn: %1.99)
    2. "vade": Taksit, ay, vade süreleri (Örn: 12 Ay)
    3. "odul_tl": Para ödülü, chip-para, bonus, hediye TL (Örn: 500 ₺)

    Kullanıcı Sorusu: {question}

    SADECE AŞAĞIDAKİ FORMATTA JSON DÖN, BAŞKA HİÇBİR ŞEY YAZMA:
    {{
        "hedef_sutun": "kar_payi VEYA vade VEYA odul_tl",
        "kategori": "kart VEYA taşıt VEYA konut VEYA ihtiyaç VEYA hepsi",
        "prefix": "Birim öneki (Örn: ₺, % veya boş bırak)",
        "suffix": "Birim soneki (Örn: Ay, TL veya boş bırak)",
        "title": "Grafik Başlığı (Örn: Kampanya Para Ödülleri veya Kâr Payı Analizi)"
    }}
    """,
    input_variables=["question"]
)
sql_agent_chain = sql_agent_prompt | llm_json | StrOutputParser()