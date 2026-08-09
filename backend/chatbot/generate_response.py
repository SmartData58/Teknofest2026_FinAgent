import json
import httpx
from loguru import logger
from fastapi.responses import StreamingResponse
from intent import sabitle_yanitla, RAG_CEVAP_PROMPTU

# Ollama Chat Endpoint
OLLAMA_URL = "http://smartdata-llm-1:11434/api/chat"

# RAG MOCK/YARDIMCI FONKSİYONLAR (Kendi Qdrant/Reranker kodlarınla bağlayabilirsin)
def get_vector_store():
    # Burada Qdrant client döndürülmeli
    return None

async def rerank_documents(query: str, docs: list):
    # Reranker entegrasyonu
    return docs[:4]

async def get_chatbot_response(
    user_message: str,
    model: str = "qwen2.5:7b",
    thinking: str = "false",
    history: list = None,
    file_context: str = ""
):
    if history is None:
        history = []

    # 1. AŞAMA: STATİK CEVAP KONTROLÜ
    if not file_context:
        static_reply = sabitle_yanitla(user_message)
        if static_reply is not None:
            logger.info(f"⚡ Statik yanıt tetiklendi: '{user_message}'")
            async def static_stream():
                yield static_reply
            return StreamingResponse(static_stream(), media_type="text/plain")

    # 2. AŞAMA: RAG VE LLM SÜRECİ
    logger.info(f"🚀 RAG ve LLM süreci başlatılıyor.. Mesaj: '{user_message}'")

    ollama_messages = [
        {"role": msg.get("role", "user"), "content": msg.get("content", "")}
        for msg in history
    ]

    context_text = ""
    if user_message.strip():
        try:
            vs = get_vector_store()
            if vs:
                initial_docs = vs.similarity_search(user_message, k=10)
                if initial_docs:
                    docs = await rerank_documents(user_message, initial_docs)
                    for i, doc in enumerate(docs):
                        context_text += f"\n--- Kampanya {i+1} ---\n{doc.page_content}\n"
        except Exception as e:
            logger.error(f"Qdrant/Reranker Arama Hatası: {e}")

    final_prompt = user_message
    if file_context:
        final_prompt += file_context
    if context_text:
        final_prompt += f"\n\n[SİSTEM NOTU: Güncel kampanya bilgileri:]\n{context_text}"
    if thinking == "true":
        final_prompt += "\n(Lütfen adım adım düşün ve detaylı cevap ver.)"

    ollama_messages.append({"role": "user", "content": final_prompt})

    payload = {
        "model": model,
        "messages": ollama_messages,
        "stream": True,
        "options": {"num_ctx": 32768}
    }

    async def generate_ollama_stream():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", OLLAMA_URL, json=payload, timeout=300.0) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
            except Exception as e:
                logger.error(f"Ollama Stream Hatası: {e}")
                yield f"\n[Hata oluştu: {str(e)}]"

    return StreamingResponse(generate_ollama_stream(), media_type="text/plain")