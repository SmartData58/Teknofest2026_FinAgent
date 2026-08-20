import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from loguru import logger

from chatbot.generate_response import get_chatbot_response

app = FastAPI(title="SmartData Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 NÜKLEER TOKAT: QDRANT OTO-KURULUM! (Acımasız Yıkım ve Yeniden İnşa)
async def auto_init_qdrant():
    from pymongo import MongoClient
    from langchain_core.documents import Document
    from langchain_qdrant import QdrantVectorStore
    from chatbot.generate_response import embeddings, QDRANT_URL
    from qdrant_client import QdrantClient
    
    try:
        logger.info("⏳ Qdrant Vektör Veritabanı OTOMATİK olarak inşa ediliyor...")
        
        # 🔥 ÖNCE QDRANT'I TEMİZLE (Hayalet Klasörleri Yok Et)
        try:
            q_client = QdrantClient(url=QDRANT_URL)
            q_client.delete_collection(collection_name="banka_kampanyalari")
            logger.warning("🧹 Eski/Bozuk Qdrant koleksiyonu silindi!")
        except Exception as e:
            pass # Koleksiyon zaten yoksa hata vermesin
            
        mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")
        client = MongoClient(mongo_uri)
        
        # Önce ana veritabanı (smartdata), yoksa test veritabanı (finagent)
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
        
        # 🚀 SIFIRDAN YARAT (force_recreate=True)
        QdrantVectorStore.from_documents(
            docs,
            embeddings,
            url=QDRANT_URL,
            collection_name="banka_kampanyalari",
            content_payload_key="belge",
            force_recreate=True 
        )
        logger.info(f"✅ BİNGO! Qdrant Vektör Veritabanı {len(docs)} kampanya ile OTOMATİK oluşturuldu!")
    except Exception as e:
        logger.error(f"Qdrant Otomatik Kurulum Hatası: {e}")

# Sunucu ayağa kalktığı an kurulumu tetikliyoruz
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Sistem Başlıyor: Otomatik Qdrant kurulumu tetiklendi...")
    asyncio.create_task(auto_init_qdrant())

@app.post("/api/chat")
async def chat_endpoint(
    prompt: str = Form(""),
    model: str = Form("qwen3.5:4b"),
    thinking: str = Form("auto"),
    history: str = Form("[]"),
    view_mode: str = Form("musteri"),
    language: str = Form("tr"),
    files: List[UploadFile] = File(default=[]) 
):
    try:
        parsed_history = json.loads(history)
    except Exception:
        parsed_history = []
        
    logger.info(f"Yeni İstek: Prompt='{prompt}', Mod={view_mode}, Dil={language}")

    return await get_chatbot_response(
        user_message=prompt,
        model=model,
        thinking=thinking,
        history=parsed_history,
        files=files,
        view_mode=view_mode, 
        language=language    
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)