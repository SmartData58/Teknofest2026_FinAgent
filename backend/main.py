# =============================================================================
# main.py — FastAPI Web Servisi ve API Endpoint'leri
# =============================================================================

import os
import psycopg2
import httpx
from typing import List
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

# Yanıt Üretim Motorunu İçeri Aktar
from chatbot.generate_response import generate_response_stream

app = FastAPI(title="Katılım Bankacılığı Kampanya Asistanı API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# VERİTABANI BAĞLANTISI VE SCHEMAS
# -----------------------------------------------------------------------------

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "smartdata"),
        user=os.getenv("POSTGRES_USER", "user"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )


class ScrapePayload(BaseModel):
    url: str


class YeniKampanya(BaseModel):
    baslik: str
    kaynak: str


# -----------------------------------------------------------------------------
# KAZIYICI VE KAMPANYA API ENDPOINTLERİ
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# CHATBOT ENDPOINT
# -----------------------------------------------------------------------------

@app.post("/api/chat")
async def chat_endpoint(
    prompt: str = Form(""),
    model: str = Form("qwen3.5:4b"),
    thinking: str = Form("false"),
    history: str = Form("[]"),
    files: List[UploadFile] = File(default=None),
):
    logger.info(f"🚀 Chat İsteği Alındı! Soru: '{prompt}'")

    stream_generator = generate_response_stream(
        prompt=prompt,
        model=model,
        thinking=thinking,
        history_json=history,
        files=files,
    )

    return StreamingResponse(stream_generator, media_type="text/plain")