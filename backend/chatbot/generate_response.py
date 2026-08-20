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
from chatbot.tools import safe_json_parse
from pymongo import MongoClient 
from chatbot.agents import sql_agent_chain, thinking_decider_chain, hyde_chain, step_back_chain, suggestion_chain
from chatbot.redis_cache import get_cached_db_params, set_cached_db_params, get_cached_full_response, set_cached_full_response

TEMP_DIR = "./temp"
os.makedirs(TEMP_DIR, exist_ok=True)

QDRANT_URL = os.getenv("QDRANT_HOST", "http://qdrant:6333")
EMBEDDING_API_URL = os.getenv("EMBEDDING_URL", "http://embedding:8001/api/embed")
RERANKER_API_URL = os.getenv("RERANKER_URL", "http://reranker:8002/api/rerank")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434/api/chat")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")

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
        except Exception:
            return docs[:4]

# 🚀 TOKAT: ARTIK GERÇEK VE DEV (355 KAYITLIK) TABLODAN BESLENİYOR!
def grafigi_hazirla_mongo_dinamik(user_query: str, db_params: dict):
    query_lower = user_query.lower()
    chart_type = "bar" if any(w in query_lower for w in ["çubuk", "bar", "tablo", "liste"]) else "doughnut"
    
    hedef_sutun_llm = db_params.get("hedef_sutun", "kar_payi")
    kategori = db_params.get("kategori", "hepsi")
    prefix = db_params.get("prefix", "")
    suffix = db_params.get("suffix", "")
    title = db_params.get("title", "Dinamik Pazar Analizi")
    
    if hedef_sutun_llm not in ["kar_payi", "vade", "odul_tl"]:
        hedef_sutun_llm = "kar_payi"
        prefix, suffix = "%", ""

    client = MongoClient(MONGO_URI)
    
    # 🚀 AKILLI SÜTUN EŞLEŞTİRİCİ
    alan_adaylari = []
    if hedef_sutun_llm == "kar_payi": alan_adaylari = ["kar_payi", "kar_payi_orani", "oran"]
    elif hedef_sutun_llm == "vade": alan_adaylari = ["vade", "vade_ay", "taksit"]
    elif hedef_sutun_llm == "odul_tl": alan_adaylari = ["odul_tl", "odul_miktari", "bonus_tl"]
    else: alan_adaylari = [hedef_sutun_llm]

    # Değerlerin boş olmamasını ve 0'dan büyük olmasını garanti eden sorgu
    or_conditions = [{"$and": [{s: {"$ne": None}}, {s: {"$gt": 0}}]} for s in alan_adaylari]
    mongo_query = {"$or": or_conditions}

    if kategori != "hepsi" and kategori in ["kart", "taşıt", "konut", "ihtiyaç"]:
        mongo_query = {
            "$and": [
                {"$or": or_conditions},
                {"$or": [
                    {"kategori": kategori}, 
                    {"kampanya_adi": {"$regex": kategori, "$options": "i"}},
                    {"baslik": {"$regex": kategori, "$options": "i"}},
                    {"kampanya_kategorisi": {"$regex": kategori, "$options": "i"}}
                ]}
            ]
        }

    # 🔥 1. ÖNCE GERÇEK TABLOYU DENE
    collection = client["smartdata"]["processed_campaigns"]
    sonuclar = list(collection.find(mongo_query))
    
    # 🚀 2. ASIL ÇÖZÜM: Eğer gerçek tabloda uygun (sayısal) veri YOKSA, test tablomuza geç!
    if len(sonuclar) == 0:
        logger.warning("Asıl tabloda uygun sayısal veri bulunamadı, Finagent test tablosuna geçiliyor!")
        collection = client["finagent"]["kampanyalar"]
        sonuclar = list(collection.find(mongo_query))

    client.close()

    # Olası alan isimlerinden dolu olan ilk veriyi getiren Safe-Get Fonksiyonu
    def safe_get_val(doc):
        for a in alan_adaylari:
            if doc.get(a): return float(doc[a])
        return 0.0

    # Grafik çorbaya dönmesin diye en iyi 30 kampanyayı sıralayarak limitliyoruz
    sonuclar.sort(key=safe_get_val, reverse=True)
    sonuclar = sonuclar[:30] 

    labels, sub_labels, values, source_indices, full_texts = [], [], [], [], []
    db_context = ""
    
    for idx, doc in enumerate(sonuclar):
        # Güvenli Key Çekimi (KeyError hatasını kökünden çözer)
        banka = doc.get("banka_adi", doc.get("banka", "Bilinmeyen Banka"))
        if isinstance(banka, dict): banka = banka.get("kisa_ad", "Bilinmeyen Banka")
        
        kampanya_adi = doc.get("kampanya_adi", doc.get("baslik", "Kampanya"))
        deger = safe_get_val(doc)
        
        labels.append(str(banka))
        sub_labels.append(str(kampanya_adi))
        values.append(deger)
        source_indices.append(idx + 1)
        
        kat = doc.get("kategori", doc.get("kampanya_kategorisi", "-"))
        detay = doc.get("ham_metin", doc.get("kosullar", "Ek detay bulunmamaktadır."))
        
        tam_metin = f"🏦 Banka / Kurum: {banka}\n🏷️ Kampanya Adı: {kampanya_adi}\n📦 Kategori: {kat}\n⚖️ {hedef_sutun_llm.upper()}: {deger}\n\n📌 Detaylı Koşullar:\n{detay}"
        full_texts.append(tam_metin)
        
        db_context += f"- Banka: {banka}, Kampanya: {kampanya_adi}, {hedef_sutun_llm.upper()}: {deger}\n"

    if len(labels) > 0:
        non_zero_values = [v for v in values if v > 0]
        avg_val = sum(non_zero_values) / len(non_zero_values) if len(non_zero_values) > 0 else 0
        
        chart_data = {
            "type": chart_type,
            "title": title,
            "subtitle": f"Otonom MongoDB Ajanı veri tabanını (Max: 30 sonuç) başarıyla sıraladı.",
            "prefix": prefix, 
            "suffix": suffix, 
            "labels": labels,
            "sub_labels": sub_labels,
            "values": values,
            "source_indices": source_indices,
            "full_texts": full_texts, 
            "stats": {"avg": round(avg_val, 2), "min": min(values), "max": max(values)}
        }
        return f'\n\n[CHART]{json.dumps(chart_data)}[/CHART]\n\n', db_context
    return "", ""

async def get_chatbot_response(
    user_message: str,
    model: str = "qwen3.5:4b",
    thinking: str = "auto", 
    history: list = None,
    file_context: str = "",
    files: List = None,
    view_mode: str = "musteri", 
    language: str = "tr"
):
    if history is None: history = []

    gecmis_mesajlar = [Mesaj(rol=msg.get("role", "user"), icerik=msg.get("content", "")) for msg in history]
    niyet: Niyet = niyet_bul(user_message, gecmis_mesajlar)

    dil_kurali = "Yanıtlarını KESİNLİKLE Türkçe ver." if language == "tr" else "Yanıtlarını KESİNLİKLE İngilizce (English) ver."
    mod_kurali = "Karşında BİR MÜŞTERİ var. Gizli banka operasyon terimlerini KULLANMA, nazik, net ve anlaşılır bir dil kullan." if view_mode == "musteri" else "Karşında BİR BANKA ÇALIŞANI (Analist) var. Detaylı, teknik, sayısal verilerle dolu, profesyonel bir dil kullan."

    if niyet.tur in ("statik", "tavsiye") and niyet.statik_cevap:
        async def static_stream():
            yield f"[STATUS]Yanıt iletiliyor...[/STATUS]\n\n"
            yield niyet.statik_cevap
        return StreamingResponse(static_stream(), media_type="text/plain")

    async def stream_generator():
        q = asyncio.Queue()

        async def progress_cb(msg: str): await q.put({"type": "status", "content": msg})

        async def background_process():
            try:
                final_full_response = ""
                db_params = {} # 🚀 EKLENDİ: Tüm bloklarda takip için!
                
                if not files:
                    cached_full = await get_cached_full_response(user_message)
                    if cached_full:
                        await q.put({"type": "status", "content": "Önbellek (Redis) taranıyor..."})
                        await asyncio.sleep(0.3)
                        await q.put({"type": "status", "content": "Yanıt Redis'ten (RAM) direkt olarak getirildi!"})
                        await q.put({"type": "token", "content": cached_full})
                        await q.put({"type": "done"})
                        return

                await q.put({"type": "status", "content": "Sorgu karmaşıklığı analiz ediliyor..."})
                is_thinking_active = False
                
                if thinking == "auto":
                    try:
                        think_res = await thinking_decider_chain.ainvoke({"question": user_message})
                        is_thinking_active = safe_json_parse(think_res).get("thinking", False)
                        if is_thinking_active:
                            await q.put({"type": "status", "content": "Karmaşık soru tespit edildi, derin düşünme başlatıldı..."})
                    except Exception: pass
                
                file_context_str = ""
                if files:
                    file_names = []
                    dosya_icerikleri = []
                    for file in files:
                        if hasattr(file, 'filename') and file.filename:
                            await q.put({"type": "status", "content": f"Dosya inceleniyor: {file.filename}..."})
                            file_path = os.path.join(TEMP_DIR, file.filename)
                            try:
                                with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
                                from document_processor.parser import parse_document
                                extracted_text = await parse_document(file_path, progress_callback=progress_cb)
                                file_names.append(file.filename)
                                dosya_icerikleri.append(f"--- {file.filename} İÇERİĞİ ---\n{extracted_text}\n-------------------")
                            except Exception:
                                await q.put({"type": "error", "content": f"{file.filename} okunamadı."})
                            finally:
                                if os.path.exists(file_path): os.remove(file_path)

                    if file_names:
                        file_context_str = (f"\n\n[KULLANICI SİSTEME DOSYA YÜKLEDİ]\n\n"
                                        f"AŞAĞIDA BU DOSYALARIN İÇERİĞİ BULUNMAKTADIR:\n{chr(10).join(dosya_icerikleri)}")

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
                            
                            # 🚀 NÜKLEER TOKAT: Bozuk Veriyi Asla Cache'leme!
                            if db_params and "hedef_sutun" in db_params:
                                await set_cached_db_params(user_message, db_params)
                            else:
                                logger.warning("⚠️ Otonom ajan düzgün JSON üretemedi, önbelleğe (cache) YAZILMADI!")
                        
                        grafik_kodu, db_context = grafigi_hazirla_mongo_dinamik(user_message, db_params)
                        if grafik_kodu:
                            final_full_response += grafik_kodu
                            await q.put({"type": "token", "content": grafik_kodu})
                    except Exception as e:
                        logger.error(f"Grafik Motoru Hatası: {e}")

                context_text = ""
                kaynaklar_listesi = []
                sorgu_metni = niyet.baglam_soru if niyet.baglam_soru else user_message

                if sorgu_metni.strip():
                    try:
                        vs = get_vector_store()
                        await q.put({"type": "status", "content": "Arama Ajanları (HyDE & Step-Back) çalıştırılıyor..."})
                        
                        hyde_task = hyde_chain.ainvoke({"question": sorgu_metni})
                        step_back_task = step_back_chain.ainvoke({"question": sorgu_metni})
                        hyde_res, step_back_res = await asyncio.gather(hyde_task, step_back_task)
                        
                        genisletilmis_sorgu = f"{sorgu_metni}\n{hyde_res}\n{step_back_res}"
                        
                        await q.put({"type": "status", "content": "Vektör Veritabanı (Qdrant) Taranıyor..."})
                        initial_docs = await asyncio.to_thread(vs.similarity_search, genisletilmis_sorgu, k=10)

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
                        logger.error(f"Qdrant Arama Hatası: {e}")

                await q.put({"type": "status", "content": "Yapay zeka yanıtı hazırlıyor..."})
                
                gecmis_str = ""
                if history:
                    gecmis_str = "ÖNCEKİ KONUŞMALAR:\n" + "\n".join([f"{m.get('role').upper()}: {m.get('content')}" for m in history[-4:]]) + "\n\n"

                tam_baglam = ""
                if db_context: tam_baglam += f"[MONGODB KESİN SONUÇLARI]\n{db_context}\n\n"
                if context_text: tam_baglam += f"[VEKTÖR VERİTABANI KAMPANYA DETAYLARI]\n{context_text}"
                if not tam_baglam.strip(): tam_baglam = "Veritabanında sorguyla eşleşen aktif kampanya bilgisi bulunamadı."
                tam_baglam += (f"\n\n{file_context_str}" if file_context_str else "")
                
                formatted_prompt = RAG_CEVAP_PROMPTU.format(dil_kurali=dil_kurali, mod_kurali=mod_kurali, baglam=tam_baglam, gecmis=gecmis_str, soru=user_message)
                
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
                                if token: 
                                    final_full_response += token
                                    await q.put({"type": "token", "content": token})

                if kaynaklar_listesi:
                    src_str = f"\n\n[SOURCES]{json.dumps(kaynaklar_listesi)}[/SOURCES]\n\n"
                    final_full_response += src_str
                    await q.put({"type": "token", "content": src_str})
                    
                await q.put({"type": "status", "content": "Öneriler düşünülüyor..."})
                try:
                    hedef_dil = "Türkçe" if language == "tr" else "English"
                    sug_raw = await suggestion_chain.ainvoke({
                        "question": user_message, 
                        "answer": final_full_response, 
                        "language": hedef_dil
                    })
                    
                    sugs = re.findall(r"\[SUGGESTION\](.*?)\[\/SUGGESTION\]", sug_raw, re.IGNORECASE)
                    
                    if not sugs:
                        satirlar = [s.strip() for s in sug_raw.split('\n') if s.strip() and len(s)>5]
                        sugs = satirlar[:3]

                    if sugs:
                        sug_string = ""
                        for s in sugs:
                            temiz_s = re.sub(r'^\d+[\.\)]\s*', '', s.strip()) 
                            sug_string += f"[SUGGESTION]{temiz_s}[/SUGGESTION]"
                            
                        final_full_response += f"\n\n{sug_string}"
                        await q.put({"type": "token", "content": f"\n\n{sug_string}"})
                except Exception as e:
                    logger.error(f"Öneri motoru hatası: {e}")

                # 🚀 TOKAT: HATALI VERİYİ CACHE'LEME YASAKLANDI!
                if is_analyst and not files and final_full_response.strip() and "hedef_sutun" in db_params:
                    await set_cached_full_response(user_message, final_full_response)

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