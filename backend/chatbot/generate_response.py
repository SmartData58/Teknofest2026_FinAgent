# =============================================================================
# generate_responses.py — Yapay Zeka Yanıt Üretim Motoru
# =============================================================================

import os
import json
import shutil
import asyncio
import httpx
import requests
from typing import List, AsyncGenerator
from loguru import logger

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Intent tespit motorundan gerekli yapıları içe aktarıyoruz
from chatbot.intent import niyet_bul, Mesaj, Niyet, RAG_CEVAP_PROMPTU

TEMP_DIR = "./temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Ortam Değişkenleri
QDRANT_URL = os.getenv("QDRANT_HOST", "http://qdrant:6333")
EMBEDDING_API_URL = os.getenv("EMBEDDING_URL", "http://embedding:8001/api/embed")
RERANKER_API_URL = os.getenv("RERANKER_URL", "http://reranker:8002/api/rerank")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434/api/chat")


# -----------------------------------------------------------------------------
# EMBEDDING VE VEKTÖR VERİTABANI İŞLEMLERİ
# -----------------------------------------------------------------------------

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
    """Qdrant'tan gelen belgeleri Reranker servisi ile yeniden sıralar."""
    if not docs:
        return []

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


# -----------------------------------------------------------------------------
# ANA CEVAP ÜRETİM STREAM GENERATOR
# -----------------------------------------------------------------------------

async def generate_response_stream(
    prompt: str,
    model: str = "qwen3.5:4b",
    thinking: str = "false",
    history_json: str = "[]",
    files: List = None,
) -> AsyncGenerator[str, None]:
    """Kullanıcı mesajını ve dosyaları işler, Niyet tespiti yapar ve yanıtı SSE/Stream olarak döner."""
    
    # 1. Sohbet Geçmişini Parse Et
    try:
        parsed_history = json.loads(history_json)
    except Exception:
        parsed_history = []

    gecmis_mesajlar = [
        Mesaj(rol=msg.get("role", "user"), icerik=msg.get("content", ""))
        for msg in parsed_history
    ]

    # 2. Niyet Tespiti (Intent Engine)
    niyet: Niyet = niyet_bul(prompt, gecmis_mesajlar)
    logger.info(f"🎯 Tespit Edilen Niyet: {niyet.tur} | Banka: {niyet.banka_kodu} | Alan: {niyet.alan}")

    # Statik Yanıtlar ve Tavsiye Reddi (LLM & RAG Baypas Edilir)
    if niyet.tur in ("statik", "tavsiye") and niyet.statik_cevap:
        yield f"[STATUS]Yanıt iletiliyor...[/STATUS]\n\n"
        yield niyet.statik_cevap
        return

    # Arka Plan İşlem Kuyruğu Oluşturma
    q = asyncio.Queue()

    async def progress_cb(msg: str):
        await q.put({"type": "status", "content": msg})

    async def background_process():
        try:
            # 3. Yüklenen Dosyaların İşlenmesi (OCR)
            file_context = ""
            if files:
                file_names = []
                dosya_icerikleri = []

                for file in files:
                    if file.filename:
                        await q.put({"type": "status", "content": f"{file.filename} işleme alındı..."})
                        file_path = os.path.join(TEMP_DIR, file.filename)
                        try:
                            # Dosyayı diske yaz
                            with open(file_path, "wb") as buffer:
                                shutil.copyfileobj(file.file, buffer)

                            # OCR ile metni çıkar
                            from document_processor.parser import parse_document
                            extracted_text = await parse_document(file_path, progress_callback=progress_cb)

                            file_names.append(file.filename)
                            dosya_icerikleri.append(
                                f"--- {file.filename} İÇERİĞİ ---\n{extracted_text}\n-------------------"
                            )

                        except Exception as e:
                            logger.error(f"Dosya işlenirken hata ({file.filename}): {e}")
                            await q.put({"type": "error", "content": f"{file.filename} okunamadı."})

                        finally:
                            # Temizlik: Geçici dosyayı sil
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                logger.info(f"🗑️ Geçici dosya silindi: {file_path}")

                if file_names:
                    isimler_str = ", ".join(file_names)
                    tum_icerik = "\n\n".join(dosya_icerikleri)
                    file_context = (
                        f"\n\n[KULLANICI SİSTEME {len(file_names)} ADET DOSYA YÜKLEDİ. "
                        f"Dosya adları: {isimler_str}]\n\n"
                        f"AŞAĞIDA BU DOSYALARIN İÇERİĞİ BULUNMAKTADIR:\n{tum_icerik}"
                    )

            # 4. RAG Arama (Qdrant + Reranker)
            await q.put({"type": "status", "content": "Veritabanı taranıyor ve sonuçlar optimize ediliyor..."})
            context_text = ""
            
            # Aranacak metin: Devam sorusu ise geçmiş bağlamıyla zenginleştirilmiş metin kullanılır
            sorgu_metni = niyet.baglam_soru if niyet.baglam_soru else prompt

            if sorgu_metni.strip():
                try:
                    vs = get_vector_store()
                    initial_docs = vs.similarity_search(sorgu_metni, k=10)

                    if initial_docs:
                        docs = await rerank_documents(sorgu_metni, initial_docs)
                        for i, doc in enumerate(docs):
                            context_text += f"\n--- Kampanya {i+1} ---\n{doc.page_content}\n"
                except Exception as e:
                    logger.error(f"Qdrant/Reranker Arama Hatası: {e}")

            # Context Yoksa Bilgilendirme
            if not context_text:
                context_text = "Veritabanında sorguyla eşleşen aktif kampanya bilgisi bulunamadı."

            # 5. LLM Prompt'unun Hazırlanması
            await q.put({"type": "status", "content": "Yapay zeka yanıtı hazırlıyor..."})
            
            # Geçmiş formatı oluşturma
            gecmis_str = ""
            if parsed_history:
                gecmis_str = "ÖNCEKİ KONUŞMALAR:\n" + "\n".join(
                    [f"{m.get('role').upper()}: {m.get('content')}" for m in parsed_history[-4:]]
                ) + "\n\n"

            # RAG Prompt Şablonunu Uygulama
            tam_baglam = context_text + (f"\n\n{file_context}" if file_context else "")
            formatted_prompt = RAG_CEVAP_PROMPTU.format(
                baglam=tam_baglam,
                gecmis=gecmis_str,
                soru=prompt
            )

            if thinking == "true":
                formatted_prompt += "\n(Lütfen mantıksal çıkarım yaparak detaylı cevap ver.)"

            ollama_messages = [{"role": "user", "content": formatted_prompt}]

            payload = {
                "model": model,
                "messages": ollama_messages,
                "stream": True,
                "options": {"num_ctx": 32768},
            }

            # 6. Ollama Streaming İsteği
            # httpx isteğinde timeout süresini None veya yüksek bir değer yapın:
            timeout = httpx.Timeout(300.0, connect=10.0)

            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                await q.put({"type": "token", "content": token})

        except Exception as e:
            logger.error(f"Arka plan işlemi hatası: {str(e)}")
            await q.put({"type": "error", "content": str(e)})
        finally:
            await q.put({"type": "done"})

    # Arka plan görevini başlat
    asyncio.create_task(background_process())

    # İstemciye Token/Status Stream Etme
    while True:
        item = await q.get()
        if item["type"] == "done":
            break
        elif item["type"] == "status":
            yield f"[STATUS]{item['content']}[/STATUS]\n\n"
        elif item["type"] == "token":
            yield item["content"]
        elif item["type"] == "error":
            yield f"\n[Hata: {item['content']}]"