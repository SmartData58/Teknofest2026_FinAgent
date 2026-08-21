import os
import json
import shutil
import asyncio
import httpx
import requests
import psycopg2
from typing import List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Rotalar
from api.campaing import router as campaign_router
from chatbot.generate_response import get_chatbot_response

app = FastAPI(title="SmartData API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaign_router)

def get_db_connection():
    return psycopg2.connect(
        host="postgres",
        database="smartdata",
        user="user",
        password="degistir_guclu_bir_sifre" 
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
            return response.json()
        except Exception as e:
            logger.error(f"Kazıyıcı bağlantı hatası: {str(e)}")
            return {"error": "Scraper servisinden yanıt alınamadı"}

@app.post("/api/kampanya-kaydet")
def kampanya_kaydet(kampanya: YeniKampanya):
    return {"status": "ok"}


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

EMBEDDING_API_URL = "http://embedding:8001/api/embed"
embeddings = OzelQwenEmbedder(api_url=EMBEDDING_API_URL)

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
            content_payload_key="belge"
        )
    return _vector_store

async def rerank_documents(query: str, docs: List) -> List:
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

async def auto_init_qdrant():
    from pymongo import MongoClient
    try:
        logger.info("⏳ Qdrant Vektör Veritabanı OTOMATİK olarak inşa ediliyor...")
        try:
            q_client = QdrantClient(url="http://qdrant:6333")
            q_client.delete_collection(collection_name="banka_kampanyalari")
            logger.warning("🧹 Eski/Bozuk Qdrant koleksiyonu silindi!")
        except Exception as e:
            pass
            
        mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")
        client = MongoClient(mongo_uri)
        
        db = client["smartdata"]
        kampanyalar = list(db["processed_campaigns"].find({}))
        if not kampanyalar:
            db = client["finagent"]
            kampanyalar = list(db["kampanyalar"].find({}))
            
        if not kampanyalar:
            logger.warning("❌ Qdrant için MongoDB'de veri bulunamadı!")
            return
            
        docs = []
        for k in kampanyalar:
            banka = k.get("banka_adi", k.get("banka", "Bilinmeyen Banka"))
            if isinstance(banka, dict): banka = banka.get("kisa_ad", "Bilinmeyen Banka")
            kampanya_adi = k.get("kampanya_adi", k.get("baslik", "Kampanya"))
            kar_payi = k.get("kar_payi", k.get("kar_payi_orani", 0))
            vade = k.get("vade", k.get("vade_ay", 0))
            odul = k.get("odul_tl", k.get("odul_miktari", 0))
            
            icerik = f"Banka: {banka}\nKampanya: {kampanya_adi}\nKâr Payı/Faiz Oranı: %{kar_payi}\nMaksimum Vade: {vade} Ay\nÖdül Miktarı: {odul} TL"
            
            if k.get("kosullar"): icerik += f"\nKoşullar: {k.get('kosullar')}"
            if k.get("ham_metin"): icerik += f"\nDetay: {k.get('ham_metin')}"
            
            docs.append(Document(page_content=icerik, metadata={"kampanya_id": str(k["_id"])}))

        logger.info(f"⏳ {len(docs)} kampanya vektörlenip Qdrant'a yükleniyor, lütfen bekleyin...")
        
        QdrantVectorStore.from_documents(
            docs,
            embeddings,
            url="http://qdrant:6333",
            collection_name="banka_kampanyalari",
            content_payload_key="belge",
            force_recreate=True 
        )
        logger.info(f"✅ BİNGO! Qdrant Vektör Veritabanı {len(docs)} kampanya ile OTOMATİK oluşturuldu!")
    except Exception as e:
        logger.error(f"Qdrant Otomatik Kurulum Hatası: {e}")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Sistem Başlıyor: Otomatik Qdrant kurulumu tetiklendi...")
    asyncio.create_task(auto_init_qdrant())
    
    # 🚀 YENİ NÜKLEER TOKAT: REDIS'İ KÖKÜNDEN TEMİZLE!
    # Sistem her başladığında LLM'in o eski hatalı ezberleri tamamen uçar.
    try:
        from chatbot.redis_cache import get_redis
        r = await get_redis()
        await r.flushall()
        logger.info("🧹 Redis Hafızası (Cache) başlangıçta tamamen TERTEMİZ edildi!")
    except Exception as e:
        logger.error(f"Redis temizlenirken hata: {e}")

TEMP_DIR = "./temp"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/api/chat")
async def chat_endpoint(
    prompt: str = Form(""),
    model: str = Form("qwen3.5:4b"), 
    thinking: str = Form("false"),
    history: str = Form("[]"),
    view_mode: str = Form("musteri"), 
    language: str = Form("tr"),       
    files: List[UploadFile] = File(default=[]) 
):
    logger.info(f"🚀 Sinyal alındı! Mesaj: '{prompt}' | Mod: {view_mode} | Dil: {language}")
    
    try:
        parsed_history = json.loads(history)
    except Exception:
        parsed_history = []
        
    file_context = ""
    
    if files:
        file_names = []
        dosya_icerikleri = []
        
        for file in files:
            if getattr(file, "filename", None): 
                file_path = os.path.join(TEMP_DIR, file.filename)
                try:
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)

                    from document_processor.parser import parse_document
                    
                    try:
                        extracted_text = await parse_document(file_path)
                    except TypeError:
                        async def dummy_cb(msg): pass
                        extracted_text = await parse_document(file_path, progress_callback=dummy_cb)

                    file_names.append(file.filename)
                    dosya_icerikleri.append(f"--- {file.filename} İÇERİĞİ ---\n{extracted_text}\n-------------------")

                except Exception as e:
                    logger.error(f"Dosya işlenirken hata oluştu ({file.filename}): {e}")

                finally:
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

    try:
        response = await get_chatbot_response(
            user_message=prompt,
            model=model,
            thinking=thinking,
            history=parsed_history,
            file_context=file_context,
            view_mode=view_mode, 
            language=language    
        )
        
        if isinstance(response, str):
            return {"response": response}
            
        return response
        
    except Exception as e:
        logger.error(f"Chatbot işlem hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chatbot işlem hatası: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)