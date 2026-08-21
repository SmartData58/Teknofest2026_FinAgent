import os
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

LANGCHAIN_OLLAMA_BASE_URL = os.getenv("LANGCHAIN_OLLAMA_BASE_URL", "http://llm:11434")

# SQL Ajanı için temperature 0 (Net), Üretim için 0.3
llm_json = ChatOllama(model="qwen3.5:4b", temperature=0, base_url=LANGCHAIN_OLLAMA_BASE_URL)
llm_text = ChatOllama(model="qwen3.5:4b", temperature=0.3, base_url=LANGCHAIN_OLLAMA_BASE_URL)

# 🚀 1. ROUTING (Yönlendirme / Düşünme Motoru)
thinking_decider_prompt = PromptTemplate(
    template="""Sen zeki bir analiz motorusun. Kullanıcının sorusunu analiz et. Soru finansal hesaplama, banka karşılaştırması, detaylı veri analizi veya karmaşık bir mantıksal yorum gerektiriyorsa true dön. Basit bir selamlaşma, kısa bilgi veya direkt bir soru ise false dön.
    Soru: {question}
    SADECE JSON FORMATINDA DÖN: {{"thinking": true}} VEYA {{"thinking": false}}
    """,
    input_variables=["question"]
)
thinking_decider_chain = thinking_decider_prompt | llm_json | StrOutputParser()

# 🚀 2. HyDE (Hypothetical Document Embeddings - Varsayımsal Belge)
hyde_prompt = PromptTemplate(
    template="""Lütfen aşağıdaki bankacılık veya kampanya sorusuna cevap olabilecek, sanki resmi bir banka belgesiymiş gibi kısa ve varsayımsal bir paragraf yaz. Bu metin arama motorunda benzerlerini bulmak için kullanılacaktır.
    Soru: {question}
    Varsayımsal Resmi Belge Metni:""",
    input_variables=["question"]
)
hyde_chain = hyde_prompt | llm_text | StrOutputParser()

# 🚀 3. STEP-BACK (Soyutlama / Genişletme)
step_back_prompt = PromptTemplate(
    template="""Aşağıdaki spesifik bankacılık sorusunu, arka plandaki daha genel, temel prensibi veya şartları araştıran soyut (step-back) bir soruya dönüştür.
    Spesifik Soru: {question}
    Genel ve Kapsayıcı Soru:""",
    input_variables=["question"]
)
step_back_chain = step_back_prompt | llm_text | StrOutputParser()

# 🚀 4. MULTI-Q (Çoklu Sorgu - Mevcut olan)
mq_prompt = PromptTemplate(
    template="""Soruyu bankacılık araması için 3 farklı şekilde yaz. JSON dön: {{"queries": ["1", "2", "3"]}}
    Soru: {question}
    """,
    input_variables=["question"]
)
mq_chain = mq_prompt | llm_json | StrOutputParser()

# OTONOM TEXT-TO-SQL AJANI
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

# 🚀 YENİ: CHATGPT TARZI ÖNERİ MOTORU (Suggestions)
# 🚀 YENİ: CHATGPT TARZI ÖNERİ MOTORU (ARTIK KESİN JSON ÇIKTISI VERECEK)
# 🚀 YENİ: CHATGPT TARZI ÖNERİ MOTORU (KUSURSUZ VE BASİT)
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