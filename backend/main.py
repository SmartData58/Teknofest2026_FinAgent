import os
import json
import shutil
import asyncio
import httpx
import requests
import psycopg2
import contextlib
from typing import List
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from chatbot.static_responses import sabitle_yanitla

# --- ARKA PLANDA OCR YÜKLEME (LIFESPAN) ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme ortamı için tüm kaynaklara izin verir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Ortam değişkeni varsa onu alır, yoksa varsayılan olarak localhost kullanır:
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
EMBEDDING_API_URL = os.getenv("EMBEDDING_URL", "http://localhost:8001/api/embed")
RERANKER_API_URL = os.getenv("RERANKER_URL", "http://localhost:8002/api/rerank")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

# --- VERİTABANI VE KAZIYICI ENDPOINTLERİ ---
def get_db_connection():
    return psycopg2.connect(
        host="postgres",
        database="smartdata",
        user="user",
        password="password"
    )

class ScrapePayload(BaseModel):
    url: str

class YeniKampanya(BaseModel):
    baslik: str
    kaynak: str    

@app.post("/api/kaziyiciyi-baslat")
async def kaziyici_tetikle(payload: ScrapePayload):
    scraper_url = "http://scraper:8002/scrape"
    logger.info(f"Kazıyıcıya istek gönderiliyor: {payload.url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(scraper_url, json={"url": payload.url}, timeout=120.0)
            logger.info(f"Kazıyıcıdan yanıt alındı: {response.status_code}")
            return response.json()
        except Exception as e:
            logger.error(f"Kazıyıcı bağlantı hatası: {str(e)}")
            return {"error": "Scraper servisinden yanıt alınamadı"}

@app.get("/api/kampanyalar")
def get_kampanyalar():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, baslik, kaynak FROM kampanyalar ORDER BY id DESC")
        rows = cur.fetchall()
        kampanyalar = [{"id": r[0], "baslik": r[1], "kaynak": r[2]} for r in rows]
        return {"kampanyalar": kampanyalar}
    except Exception as e:
        logger.error(f"Veritabanı hatası: {str(e)}")
        return {"error": str(e)}
    finally:
        if conn:
            cur.close()
            conn.close()

@app.post("/api/kampanya-kaydet")
def kampanya_kaydet(kampanya: YeniKampanya):
    return {"status": "ok"}


# --- RAG (Vektör Veritabanı) VE EMBEDDING AYARLARI ---
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
        return self.embed_documents([text])[0]

# --- ESKİ HALİ (SİLİNECEK) ---
# qdrant_client = QdrantClient(url="http://qdrant:6333")
# vector_store = QdrantVectorStore(...)

# --- YENİ HALİ (BUNU YAPIŞTIR) ---
EMBEDDING_API_URL = "http://embedding:8001/api/embed"
embeddings = OzelQwenEmbedder(api_url=EMBEDDING_API_URL)

# Vektör veritabanını globalde hemen BAŞLATMIYORUZ (Tembel Yükleme)
_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        logger.info("Qdrant ve Embedding servisine ilk bağlantı kuruluyor...")
        qdrant_client = QdrantClient(url="http://qdrant:6333")
        _vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name="banka_kampanyalari",
            embedding=embeddings,
            content_payload_key="belge" # 🚀 HAYAT KURTARAN DOKUNUŞ: LLM'e metni nerede bulacağını söylüyoruz
        )
    return _vector_store


# --- YENİ: RERANKER FONKSİYONU ---
async def rerank_documents(query: str, docs: List) -> List:
    """Qdrant'tan gelen belgeleri Reranker servisi ile yeniden puanlar ve sıralar"""
    if not docs:
        return []
    
    rerank_url = "http://reranker:8002/api/rerank"
    texts = [doc.page_content for doc in docs]
    payload = {"query": query, "texts": texts}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(rerank_url, json=payload, timeout=30.0)
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
            logger.error(f"Reranker Servis Hatası: {e}. Qdrant sıralaması kullanılıyor.")
            return docs[:4]


# --- CHATBOT VE DOSYA İŞLEME ENDPOINT'İ ---
# DOĞRU (Docker Compose içi LLM adresi ve chat endpoint'i):
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434/api/chat")

TEMP_DIR = "./temp"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/api/chat")
async def chat_endpoint(
    prompt: str = Form(""),
    model: str = Form("qwen3.5:4b"),
    thinking: str = Form("false"),
    history: str = Form("[]"),
    files: List[UploadFile] = File(default=None)
):
    logger.info(f"🚀 Sinyal alındı! Mesaj: '{prompt}'")
    
    try:
        parsed_history = json.loads(history)
    except Exception:
        parsed_history = []
        
    static_answer = sabitle_yanitla(prompt)
    if static_answer:
        async def static_stream():
            yield static_answer

        return StreamingResponse(static_stream(), media_type="text/plain")
        
    ollama_messages = [{"role": msg.get("role", "user"), "content": msg.get("content", "")} for msg in parsed_history]
    
    q = asyncio.Queue()

    async def progress_cb(msg: str):
        await q.put({"type": "status", "content": msg})

    async def background_process():
        try:
            file_context = ""
            if files:
                file_names = []
                dosya_icerikleri = []
                
                for file in files:
                    if file.filename: 
                        await q.put({"type": "status", "content": f"{file.filename} işleme alındı..."})
                        file_path = os.path.join(TEMP_DIR, file.filename)
                        try:
                            # 1. Dosyayı temp klasörüne yaz
                            with open(file_path, "wb") as buffer:
                                shutil.copyfileobj(file.file, buffer)

                            # 2. OCR ile metni çıkart
                            from document_processor.parser import parse_document
                            extracted_text = await parse_document(file_path, progress_callback=progress_cb)

                            file_names.append(file.filename)
                            dosya_icerikleri.append(f"--- {file.filename} İÇERİĞİ ---\n{extracted_text}\n-------------------")

                        except Exception as e:
                            logger.error(f"Dosya işlenirken hata oluştu ({file.filename}): {e}")
                            await q.put({"type": "error", "content": f"{file.filename} okunamadı."})

                        finally:
                            # 🚀 3. DISMOUNT (TEMİZLİK): OCR'ın işi bittiğinde dosyayı anında yok et!
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                logger.info(f"🗑️ Geçici dosya silindi (Dismounted): {file_path}")
                        
                if file_names:
                    isimler_str = ", ".join(file_names)
                    tum_icerik = "\n\n".join(dosya_icerikleri)
                    file_context = (
                        f"\n\n[KULLANICI SİSTEME {len(file_names)} ADET DOSYA YÜKLEDİ. "
                        f"Dosya adları: {isimler_str}]\n\n"
                        f"AŞAĞIDA BU DOSYALARIN İÇERİĞİ BULUNMAKTADIR:\n{tum_icerik}"
                    )

            # --- GÜNCELLENDİ: QDRANT + RERANKER ---
            await q.put({"type": "status", "content": "Veritabanı taranıyor ve sonuçlar Reranker ile optimize ediliyor..."})
            context_text = ""
            
            if prompt.strip():
                try:
                    # 1. Aşama: Qdrant'tan geniş bir havuz (10 aday) çek
                    vs = get_vector_store()
                    initial_docs = vs.similarity_search(prompt, k=10)
                    
                    if initial_docs:
                        # 2. Aşama: Reranker ile bu 10 adayı yapay zeka süzgecinden geçirip en iyi 4'ü al
                        docs = await rerank_documents(prompt, initial_docs)
                        
                        for i, doc in enumerate(docs):
                            context_text += f"\n--- Kampanya {i+1} ---\n{doc.page_content}\n"
                except Exception as e:
                    logger.error(f"Qdrant/Reranker Arama Hatası: {e}")

            await q.put({"type": "status", "content": "Yapay zeka yanıtı hazırlıyor..."})
            
            final_prompt = prompt
            
            if file_context:
                final_prompt += file_context
                
            if context_text:
                final_prompt += (
                    f"\n\n[SİSTEM NOTU: Aşağıda veritabanından çekilen güncel kampanya bilgileri bulunmaktadır. "
                    f"Kullanıcının sorusunu yanıtlarken bu bilgileri DİKKATE AL:]\n{context_text}"
                )
                
            if thinking == "true":
                final_prompt += "\n(Lütfen adım adım düşün ve mantıksal bir çıkarım yaparak detaylı cevap ver.)"

            ollama_messages.append({"role": "user", "content": final_prompt})

            payload = {
                "model": model,
                "messages": ollama_messages,
                "stream": True,
                "options": {"num_ctx": 32768}
            }

            async with httpx.AsyncClient() as client:
                async with client.stream("POST", OLLAMA_URL, json=payload, timeout=300.0) as response:
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

    asyncio.create_task(background_process())

    async def stream_generator():
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

    return StreamingResponse(stream_generator(), media_type="text/plain")