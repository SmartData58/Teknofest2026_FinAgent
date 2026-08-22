import os
import json
import shutil
import asyncio
import uuid
import inspect
import tempfile
from contextlib import asynccontextmanager
from typing import List

import httpx
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

# Rotalar
from api.campaing import router as campaign_router
from chatbot.generate_response import get_chatbot_response
from chatbot.indexing import qdrant_durumu, auto_init_qdrant

# ⚠️ document_processor.parser BİLEREK en üstte import EDİLMİYOR — bkz. _belge_isleyici_al().

# -----------------------------------------------------------------------------
# Yapılandırma — 🛠️ Tüm servis adresleri ve kimlik bilgileri artık ortam
# değişkenlerinden okunuyor. Önceden bunlar kodun içine gömülüydü (özellikle
# Postgres şifresi düz metin haldeydi) ve chatbot/generate_response.py zaten
# env kullandığı için iki dosya farklı adreslere bakabiliyordu.
# -----------------------------------------------------------------------------
SCRAPER_URL = os.getenv("SCRAPER_URL", "http://scraper:8002/scrape")
TEMP_DIR = os.getenv("TEMP_DIR", "./temp")

# Redis önbelleğini başlangıçta temizleme — varsayılan AÇIK.
# Kapatmak için: STARTUP_CACHE_FLUSH=0
STARTUP_CACHE_TEMIZLE = os.getenv("STARTUP_CACHE_FLUSH", "1") == "1"

os.makedirs(TEMP_DIR, exist_ok=True)

# Arka plan indeksleme görevine referans tutulur — 🛠️ asyncio.create_task()'in
# dönüşü bir yerde tutulmazsa görev çöp toplayıcı tarafından çalışırken
# toplanabilir (Python belgelerinin açıkça uyardığı bir durum); eski kodda
# referans hiçbir yerde saklanmıyordu.
_arka_plan_gorevleri: set[asyncio.Task] = set()


async def _redis_onbellegini_temizle() -> None:
    """Uygulamanın kendi önbellek anahtarlarını siler.

    🛠️ Eski kod `await r.flushall()` çağırıyordu. flushall() Redis
    sunucusundaki TÜM veritabanlarını, TÜM anahtarları siler — sadece bu
    uygulamanınkileri değil. Redis başka bir servisle (oturum yönetimi, kuyruk,
    başka bir uygulama) paylaşılıyorsa onların verisi de yok olur. Ayrıca
    uvicorn --reload ile çalışırken her kod değişikliği yeniden başlatma
    tetiklediği için önbellek sürekli sıfırlanıyor, dolayısıyla önbellek
    pratikte hiç işe yaramıyordu. Artık yalnızca kendi ön ekli anahtarlarımızı
    siliyoruz. Bu davranış varsayılan olarak AÇIK; kapatmak için
    STARTUP_CACHE_FLUSH=0.
    """
    from chatbot.redis_cache import get_redis

    r = await get_redis()
    silinen = 0
    # 🛠️ "api:*" eklendi — api/campaing.py'nin kampanya listesi/detay önbelleği
    # bu ön eki kullanıyor ve önceki sürümde temizlikten kaçıyordu.
    for onek in ("db_params:*", "full_res:*", "api:*"):
        async for anahtar in r.scan_iter(match=onek, count=500):
            await r.delete(anahtar)
            silinen += 1
    logger.info(f"🧹 Redis önbelleği temizlendi ({silinen} anahtar silindi).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🛠️ @app.on_event("startup") FastAPI'de kullanımdan kaldırıldı (deprecated);
    # yerine lifespan bağlam yöneticisi kullanılıyor.
    logger.info("🚀 Sistem başlıyor...")

    # 🛠️ OTOMATİK QDRANT VEKTÖRLEMESİ KALDIRILDI.
    # auto_init_qdrant() koleksiyonu force_recreate=True ile sıfırdan kuruyordu;
    # vektörlemeyi kendi pipeline'ınız yaptığı için uygulamanın her açılışı
    # sizin gerçek vektörlerinizi silip yerine MongoDB'de bulduğunu (32 adetlik
    # sahte demo havuzu) koyuyordu. uvicorn --reload ile bu, her kod
    # değişikliğinde tekrarlanıyordu. Elle çalıştırmak için:
    #     python -m chatbot.indexing
    # Koleksiyonun canlı durumu artık GET /health ile görülebilir.

    # 🛠️ /campaigns ucu banka_kodu / kampanya_turu / hedef_kitle alanlarında
    # filtreliyor; indeks yoksa her istek koleksiyonu baştan sona tarar.
    # Bloke eden bir çağrı olduğu için ayrı thread'de çalıştırılıyor.
    try:
        from api.campaing import indeksleri_kur
        await asyncio.to_thread(indeksleri_kur)
    except Exception as e:
        logger.warning(f"Kampanya indeksleri kurulamadı: {e}")

    if STARTUP_CACHE_TEMIZLE:
        try:
            await _redis_onbellegini_temizle()
        except Exception as e:
            logger.error(f"Redis temizlenirken hata: {e}")
    else:
        logger.info("ℹ️ Başlangıç önbellek temizliği kapalı (STARTUP_CACHE_FLUSH=0).")

    yield

    for g in list(_arka_plan_gorevleri):
        g.cancel()


app = FastAPI(title="SmartData API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaign_router)


class ScrapePayload(BaseModel):
    url: str


@app.get("/health")
async def health():
    """Servisin ve Qdrant koleksiyonunun CANLI durumu.

    Vektörlemeyi kendi pipeline'ınız yaptığı için bu uç, uygulamanın ne
    yazdığını değil, Qdrant'ta GERÇEKTEN ne olduğunu okur (salt okunur) ve
    payload sözleşmesi bozuksa ('belge' / 'banka_kodu' alanları) uyarır.
    """
    qdrant = await asyncio.to_thread(qdrant_durumu)
    return {"status": "ok", "qdrant": qdrant}


@app.post("/api/kaziyiciyi-baslat")
async def kaziyici_tetikle(payload: ScrapePayload):
    logger.info(f"Kazıyıcıya istek gönderiliyor: {payload.url}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(SCRAPER_URL, json={"url": payload.url}, timeout=120.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # 🛠️ Eski kod hata durumunda HTTP 200 ile {"error": ...} dönüyordu;
            # istemci tarafı bunu başarı sanıyordu. Artık gerçek bir hata kodu döner.
            logger.error(f"Kazıyıcı bağlantı hatası: {e}")
            raise HTTPException(status_code=502, detail="Scraper servisinden yanıt alınamadı.")


class ReindexYaniti(BaseModel):
    adet: int


@app.post("/admin/reindex", response_model=ReindexYaniti)
async def admin_reindex(x_admin_token: str | None = Header(default=None)):
    """Qdrant koleksiyonunu MongoDB'deki (pipeline'ın yazdığı) kampanyalardan
    yeniden kurar — chatbot/indexing.py::auto_init_qdrant()'ı çalıştırır.

    🛠️ Neden var: pipeline.py'nin ADIM 4'ü (kampanyaları vektörleyip Qdrant'a
    yazma) normalde 'chatbot' paketini doğrudan import edip aynı işi
    process-içinde yapar. Ancak pipeline.py backend.*/scraper.* modüllerini
    (ADIM 1-3) import edebiliyorken chatbot.*'ı edemiyorsa, bu ikisinin AYRI
    container'larda/servislerde çalıştığı anlamına gelir — o durumda import
    çözüm değildir, çünkü paket o dosya sisteminde hiç yok. Bu uç, container
    sınırını process değil AĞ üzerinden aşmak için var: pipeline.py bu ucu
    HTTP ile çağırır (bkz. pipeline.py::_adim4_http_ile_calistir).

    Aynı container'da çalışıyorsanız pipeline zaten doğrudan auto_init_qdrant()'ı
    import edip çağırır; bu durumda bu uca hiç istek gelmez, sadece hazır bulunur.

    Güvenlik: ADMIN_TOKEN ortam değişkeni ayarlıysa, eşleşen X-Admin-Token
    header'ı taşımayan istekler 401 ile reddedilir. ADMIN_TOKEN ayarlı
    değilse (varsayılan/geliştirme) bu uç korumasızdır — dışa açık bir
    ortamda ADMIN_TOKEN ayarlamanız önerilir, çünkü bu uç Qdrant koleksiyonunu
    force_recreate=True ile SIFIRDAN kurar.
    """
    beklenen_token = os.getenv("ADMIN_TOKEN")
    if beklenen_token and x_admin_token != beklenen_token:
        raise HTTPException(status_code=401, detail="Geçersiz veya eksik X-Admin-Token.")

    adet = await auto_init_qdrant()
    return ReindexYaniti(adet=adet)


# 🛠️ /api/kampanya-kaydet kaldırıldı. Uç, gövdesinde HİÇBİR ŞEY YAPMADAN
# {"status": "ok"} dönüyordu — yani istemciye kaydedildi diyip veriyi sessizce
# çöpe atıyordu (sessiz veri kaybı). Gerçekten gerekiyorsa kaydetme mantığıyla
# birlikte api/campaing.py router'ına eklenmeli; sahte bir başarı yanıtı
# döndürmektense ucu hiç sunmamak daha güvenli.


# Belge işleyici (OCR) tembel yükleme önbelleği: (fonksiyon, progress_callback_kabul_ediyor_mu)
_belge_isleyici: tuple | None = None


def _belge_isleyici_al():
    """document_processor.parser'ı İLK DOSYA YÜKLENDİĞİNDE import eder.

    🛠️ Bu import en üst seviyede olursa (bir önceki sürümde öyleydi) OCR modeli
    uygulama açılışında, hiç dosya yüklenmese bile belleğe yükleniyor; container
    başlangıcı yavaşlıyor ve RAM boşuna tutuluyor. Artık modül yalnızca gerçekten
    bir dosya işlenmesi gerektiğinde yükleniyor ve sonuç önbelleğe alınıyor —
    yani ikinci ve sonraki yüklemelerde tekrar import maliyeti yok.
    """
    global _belge_isleyici
    if _belge_isleyici is None:
        logger.info("📄 Belge işleyici (OCR) ilk kez yükleniyor...")
        from document_processor.parser import parse_document

        # parse_document'ın imzası projeye göre değişebiliyor (bazı sürümleri
        # zorunlu bir progress_callback bekliyor). Eski kod bunu her çağrıda
        # TypeError yakalayarak deniyordu — bu, parse_document'ın İÇİNDEKİ
        # gerçek bir TypeError'ı da yutup sessizce yanlış yola sapabilirdi.
        # Artık imza bir kez, açıkça inceleniyor.
        try:
            cb_destekli = "progress_callback" in inspect.signature(parse_document).parameters
        except (TypeError, ValueError):
            cb_destekli = False

        _belge_isleyici = (parse_document, cb_destekli)
        logger.info(f"✅ Belge işleyici hazır (progress_callback: {cb_destekli}).")
    return _belge_isleyici


async def _belgeyi_ayristir(file_path: str) -> str:
    parse_document, cb_destekli = _belge_isleyici_al()
    if cb_destekli:
        async def _bos_cb(mesaj):
            return None
        return await parse_document(file_path, progress_callback=_bos_cb)
    return await parse_document(file_path)


async def _yuklenen_dosyalari_isle(files: List[UploadFile]) -> str:
    """Yüklenen dosyaları geçici bir dizine yazar, metnini çıkarır ve LLM'e
    verilecek bağlam metnini üretir."""
    if not files:
        return ""

    file_names: list[str] = []
    dosya_icerikleri: list[str] = []

    # 🛠️ İki güvenlik/doğruluk sorunu birden çözülüyor:
    #  1) Yol sızması (path traversal): eski kod kullanıcıdan gelen
    #     file.filename'i doğrudan os.path.join(TEMP_DIR, ...) içinde
    #     kullanıyordu. "../../etc/cron.d/x" gibi bir dosya adı TEMP_DIR
    #     dışına yazmaya izin verirdi. Artık os.path.basename ile
    #     yalnızca dosya adı kısmı alınıyor.
    #  2) Eşzamanlılık çakışması: aynı anda iki kullanıcı "rapor.pdf"
    #     yüklerse eski kodda ikisi de aynı yola yazıyor, biri diğerinin
    #     içeriğini eziyor ve finally bloğunda diğerinin dosyasını siliyordu.
    #     Artık her istek kendi izole geçici dizinini kullanıyor.
    istek_dizini = tempfile.mkdtemp(prefix=f"upload_{uuid.uuid4().hex[:8]}_", dir=TEMP_DIR)

    try:
        for file in files:
            ham_ad = getattr(file, "filename", None)
            if not ham_ad:
                continue

            guvenli_ad = os.path.basename(ham_ad) or f"dosya_{uuid.uuid4().hex[:8]}"
            file_path = os.path.join(istek_dizini, guvenli_ad)

            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                extracted_text = await _belgeyi_ayristir(file_path)

                file_names.append(guvenli_ad)
                dosya_icerikleri.append(
                    f"--- {guvenli_ad} İÇERİĞİ ---\n{extracted_text}\n-------------------"
                )
            except Exception as e:
                logger.error(f"Dosya işlenirken hata oluştu ({guvenli_ad}): {e}")
    finally:
        # 🛠️ Geçici dizin, içindeki her şeyle birlikte tek seferde siliniyor.
        # Eski kodda dosya silme her dosyanın kendi finally'sindeydi; parse
        # sırasında beklenmedik bir hata olursa dosya diskte kalabiliyordu.
        shutil.rmtree(istek_dizini, ignore_errors=True)
        logger.info(f"🗑️ Geçici yükleme dizini silindi: {istek_dizini}")

    if not file_names:
        return ""

    isimler_str = ", ".join(file_names)
    tum_icerik = "\n\n".join(dosya_icerikleri)
    return (
        f"\n\n[KULLANICI SİSTEME {len(file_names)} ADET DOSYA YÜKLEDİ. "
        f"Dosya adları: {isimler_str}]\n\n"
        f"AŞAĞIDA BU DOSYALARIN İÇERİĞİ BULUNMAKTADIR:\n{tum_icerik}"
    )


@app.post("/api/chat")
async def chat_endpoint(
    prompt: str = Form(""),
    model: str = Form("qwen3.5:4b"),
    # 🛠️ Varsayılan "false" -> "auto". Frontend zaten "auto" gönderiyor ama
    # varsayılanın "false" olması, parametreyi göndermeyen her istemcide derin
    # RAG akışını (HyDE + Step-Back + Multi-Query) tamamen devre dışı bırakıyordu.
    thinking: str = Form("auto"),
    history: str = Form("[]"),
    view_mode: str = Form("musteri"),
    language: str = Form("tr"),
    files: List[UploadFile] = File(default=[]),
):
    logger.info(f"🚀 Sinyal alındı! Mesaj: '{prompt}' | Mod: {view_mode} | Dil: {language}")

    try:
        parsed_history = json.loads(history)
        if not isinstance(parsed_history, list):
            parsed_history = []
    except Exception:
        parsed_history = []

    file_context = await _yuklenen_dosyalari_isle(files)

    try:
        return await get_chatbot_response(
            user_message=prompt,
            model=model,
            thinking=thinking,
            history=parsed_history,
            file_context=file_context,
            view_mode=view_mode,
            language=language,
        )
    except Exception as e:
        logger.error(f"Chatbot işlem hatası: {e}")
        raise HTTPException(status_code=500, detail="Chatbot isteği işlenemedi.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)