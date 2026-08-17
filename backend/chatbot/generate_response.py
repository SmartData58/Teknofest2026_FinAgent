# =============================================================================
# generate_response.py — Yapay Zeka Yanıt Üretim Motoru (HYBRID RAG + REDIS)
# =============================================================================

import os
import json
import shutil
import asyncio
import httpx
import requests
import re
from typing import List, AsyncGenerator
from loguru import logger
from fastapi.responses import StreamingResponse

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from chatbot.intent import niyet_bul, Mesaj, Niyet, RAG_CEVAP_PROMPTU
from chatbot.tools import safe_json_parse, grafigi_hazirla_mongo_dinamik
# 🚀 YENİ KARAR MOTORUMUZU İÇERİ ALIYORUZ
from chatbot.agents import sql_agent_chain, thinking_decider_chain

# 🚀 REDIS MOTORUNU İÇERİ ALIYORUZ
from chatbot.redis_cache import get_cached_db_params, set_cached_db_params

TEMP_DIR = "./temp"
os.makedirs(TEMP_DIR, exist_ok=True)

QDRANT_URL = os.getenv("QDRANT_HOST", "http://qdrant:6333")
EMBEDDING_API_URL = os.getenv("EMBEDDING_URL", "http://embedding:8001/api/embed")
RERANKER_API_URL = os.getenv("RERANKER_URL", "http://reranker:8002/api/rerank")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434/api/chat")


class OzelQwenEmbedder(Embeddings):
    def __init__(self, api_url: str):
        self.api_url = api_url

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            response = requests.post(self.api_url, json={"input": texts})
            response.raise_for_status()
            return response.json().get("embeddings", [])
        except Exception as e:
            logger.error(f"Embedding API Hatası: {e}")
            return []

    def embed_query(self, text: str) -> List[float]:
        res = self.embed_documents([text])
        return res[0] if res else []

embeddings = OzelQwenEmbedder(api_url=EMBEDDING_API_URL)
_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        logger.info("Qdrant ve Embedding servisine ilk bağlantı kuruluyor...")
        qdrant_client = QdrantClient(url=QDRANT_URL)
        _vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name="banka_kampanyalari",
            embedding=embeddings,
            content_payload_key="belge",
        )
    return _vector_store

async def rerank_documents(query: str, docs: List) -> List:
    if not docs: return []
    texts = [doc.page_content for doc in docs]
    payload = {"query": query, "texts": texts}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(RERANKER_API_URL, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            if isinstance(result, list):
                ranked_indices = [item["index"] for item in result if "index" in item]
            elif isinstance(result, dict) and "indices" in result:
                ranked_indices = result["indices"]
            else:
                ranked_indices = list(range(len(docs)))
            reranked_docs = [docs[i] for i in ranked_indices if i < len(docs)]
            return reranked_docs[:4]
        except Exception as e:
            logger.error(f"Reranker Servis Hatası: {e}. Varsayılan Qdrant sıralaması kullanılıyor.")
            return docs[:4]


async def get_chatbot_response(
    user_message: str,
    model: str = "qwen3.5:4b",
    thinking: str = "auto", # 🚀 Varsayılan artık 'auto'
    history: list = None,
    file_context: str = "",
    files: List = None
):
    if history is None: history = []

    gecmis_mesajlar = [Mesaj(rol=msg.get("role", "user"), icerik=msg.get("content", "")) for msg in history]

    niyet: Niyet = niyet_bul(user_message, gecmis_mesajlar)
    logger.info(f"🎯 Tespit Edilen Niyet: {niyet.tur} | Banka: {niyet.banka_kodu} | Alan: {niyet.alan}")

    if niyet.tur in ("statik", "tavsiye") and niyet.statik_cevap:
        async def static_stream():
            yield f"[STATUS]Yanıt iletiliyor...[/STATUS]\n\n"
            yield niyet.statik_cevap
        return StreamingResponse(static_stream(), media_type="text/plain")

    async def stream_generator():
        q = asyncio.Queue()

        async def progress_cb(msg: str):
            await q.put({"type": "status", "content": msg})

        async def background_process():
            try:
                # 🚀 1. OTONOM DÜŞÜNME KARARI ALINIYOR
                await q.put({"type": "status", "content": "Sorgu karmaşıklığı analiz ediliyor..."})
                is_thinking_active = False
                
                if thinking == "auto":
                    try:
                        think_res = await thinking_decider_chain.ainvoke({"question": user_message})
                        is_thinking_active = safe_json_parse(think_res).get("thinking", False)
                        if is_thinking_active:
                            await q.put({"type": "status", "content": "Karmaşık soru tespit edildi, derin düşünme başlatıldı..."})
                            logger.info("🧠 Otonom Karar: Düşünme AKTİF")
                        else:
                            logger.info("🧠 Otonom Karar: Düşünme PASİF")
                    except Exception as e:
                        logger.error(f"Düşünme Motoru Hatası: {e}")
                
                file_context_str = ""
                if files:
                    file_names = []
                    dosya_icerikleri = []
                    for file in files:
                        if hasattr(file, 'filename') and file.filename:
                            await q.put({"type": "status", "content": f"{file.filename} işleme alındı..."})
                            file_path = os.path.join(TEMP_DIR, file.filename)
                            try:
                                with open(file_path, "wb") as buffer:
                                    shutil.copyfileobj(file.file, buffer)

                                from document_processor.parser import parse_document
                                extracted_text = await parse_document(file_path, progress_callback=progress_cb)
                                file_names.append(file.filename)
                                dosya_icerikleri.append(f"--- {file.filename} İÇERİĞİ ---\n{extracted_text}\n-------------------")
                            except Exception as e:
                                logger.error(f"Dosya işlenirken hata: {e}")
                                await q.put({"type": "error", "content": f"{file.filename} okunamadı."})
                            finally:
                                if os.path.exists(file_path): os.remove(file_path)

                    if file_names:
                        file_context_str = (f"\n\n[KULLANICI SİSTEME DOSYA YÜKLEDİ]\n\n"
                                        f"AŞAĞIDA BU DOSYALARIN İÇERİĞİ BULUNMAKTADIR:\n{chr(10).join(dosya_icerikleri)}")

                # REDIS VE MONGODB ENTEGRASYONU
                db_context = ""
                analiz_kelimeleri = ["grafik", "tablo", "oran", "kıyas", "analiz", "pazar", "listele", "kar payı", "faiz", "kampanya", "taksit", "vade", "ay", "ödül", "para", "tl", "bonus"]
                
                is_analyst = niyet.tur in ("karsilastirma", "banka_listesi") or any(k in user_message.lower() for k in analiz_kelimeleri)

                if is_analyst:
                    await q.put({"type": "status", "content": "Önbellek (Redis) kontrol ediliyor..."})
                    try:
                        db_params = await get_cached_db_params(user_message)
                        if not db_params:
                            await q.put({"type": "status", "content": "Otonom Ajan MongoDB'yi Sorguluyor..."})
                            raw_db_params = await sql_agent_chain.ainvoke({"question": user_message})
                            db_params = safe_json_parse(raw_db_params)
                            await set_cached_db_params(user_message, db_params)
                        
                        grafik_kodu, db_context = grafigi_hazirla_mongo_dinamik(user_message, db_params)
                        
                        if grafik_kodu:
                            await q.put({"type": "token", "content": grafik_kodu})
                    except Exception as e:
                        logger.error(f"MongoDB/Redis Grafik Hatası: {e}")

                # QDRANT RAG Arama
                await q.put({"type": "status", "content": "Vektör Veritabanı Taranıyor..."})
                context_text = ""
                kaynaklar_listesi = []
                
                sorgu_metni = niyet.baglam_soru if niyet.baglam_soru else user_message

                if sorgu_metni.strip():
                    try:
                        vs = get_vector_store()
                        initial_docs = await asyncio.to_thread(vs.similarity_search, sorgu_metni, k=10)

                        if initial_docs:
                            await q.put({"type": "status", "content": "Reranker ile belgeler optimize ediliyor..."})
                            for i, doc in enumerate(initial_docs):
                                kampanya_id = doc.metadata.get('kampanya_id', f'Bilinmiyor_{i}')
                                kaynaklar_listesi.append({"index": i + 1, "kampanya_id": kampanya_id, "icerik": doc.page_content})

                            docs = await rerank_documents(sorgu_metni, initial_docs)
                            for i, doc in enumerate(docs):
                                orij_idx = next((k["index"] for k in kaynaklar_listesi if k["icerik"] == doc.page_content), i+1)
                                context_text += f"\n--- Kaynak [{orij_idx}] ---\n{doc.page_content}\n"
                    except Exception as e:
                        logger.error(f"Qdrant/Reranker Arama Hatası: {e}")

                await q.put({"type": "status", "content": "Yapay zeka yanıtı hazırlıyor..."})
                
                gecmis_str = ""
                if history:
                    gecmis_str = "ÖNCEKİ KONUŞMALAR:\n" + "\n".join(
                        [f"{m.get('role').upper()}: {m.get('content')}" for m in history[-4:]]
                    ) + "\n\n"

                tam_baglam = ""
                if db_context: tam_baglam += f"[MONGODB KESİN SONUÇLARI]\n{db_context}\n\n"
                if context_text: tam_baglam += f"[VEKTÖR VERİTABANI KAMPANYA DETAYLARI]\n{context_text}"
                if not tam_baglam.strip(): tam_baglam = "Veritabanında sorguyla eşleşen aktif kampanya bilgisi bulunamadı."
                tam_baglam += (f"\n\n{file_context_str}" if file_context_str else "")
                
                formatted_prompt = RAG_CEVAP_PROMPTU.format(baglam=tam_baglam, gecmis=gecmis_str, soru=user_message)
                
                # 🚀 Düşünme kararı alındıysa prompta analitik talimatı ekle
                if is_thinking_active or thinking == "true": 
                    formatted_prompt += "\n(Lütfen adım adım mantıksal çıkarım yaparak analitik ve detaylı bir cevap ver.)"

                ollama_messages = [{"role": "user", "content": formatted_prompt}]
                payload = {"model": model, "messages": ollama_messages, "stream": True, "options": {"num_ctx": 32768}}
                timeout = httpx.Timeout(300.0, connect=10.0)

                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line:
                                chunk = json.loads(line)
                                token = chunk.get("message", {}).get("content", "")
                                if token: await q.put({"type": "token", "content": token})

                if kaynaklar_listesi:
                    await q.put({"type": "token", "content": f"\n\n[SOURCES]{json.dumps(kaynaklar_listesi)}[/SOURCES]\n\n"})

            except Exception as e:
                logger.error(f"Arka plan işlemi hatası: {str(e)}")
                await q.put({"type": "error", "content": str(e)})
            finally:
                await q.put({"type": "done"})

        asyncio.create_task(background_process())

        while True:
            item = await q.get()
            if item["type"] == "done": break
            elif item["type"] == "status": yield f"[STATUS]{item['content']}[/STATUS]\n\n"
            elif item["type"] == "token": yield item["content"]
            elif item["type"] == "error": yield f"\n[Hata: {item['content']}]"

    return StreamingResponse(stream_generator(), media_type="text/plain")