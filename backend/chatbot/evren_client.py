# -*- coding: utf-8 -*-
"""
evren_client.py — Yarışma çıkarım servisi (evren-llmapi) için paylaşılan istemci.

Yerel Ollama + yerel embedding + yerel reranker yerine, yarışmanın 8×H200
üzerinde çalışan OpenAI-uyumlu servisini kullanır.

TEK GERÇEK KAYNAK: sohbet akışı, embedding ve rerank çağrılarının TAMAMI burada.
chatbot/agents.py, chatbot/generate_response.py, chatbot/indexing.py ve
embedding_client.py bu modülü kullanır — böylece adres/anahtar/model değişimi
tek dosyadan yapılır.

⚠️ ANAHTARLAR KODA YAZILMAZ. Hepsi ortam değişkeninden okunur (bkz. .env.ornek).

HIZLI DOĞRULAMA (anahtarlar tanımlıyken):
    python evren_client.py            # sohbet + embedding + rerank'i sırayla dener
    python evren_client.py --sadece embed
"""
import json
import os
import time
from typing import Iterable, List, Optional

import httpx
import numpy as np

try:
    from loguru import logger
except Exception:                                   # loguru yoksa sessiz düş
    class _L:
        def __getattr__(self, _):
            return lambda *a, **k: None
    logger = _L()


# =============================================================================
# YAPILANDIRMA
# =============================================================================
BASE_URL = os.getenv("EVREN_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1").rstrip("/")
API_KEY = os.getenv("EVREN_API_KEY", "")

# Kullanıcı tercihi: her şey llm-large (TR-MMLU %79,6).
# Ajanları hızlandırmak istersen EVREN_MODEL_HIZLI=llm-fast ver — küçük işler
# (niyet, öneri, denetim) oraya gider, ana cevap llm-large'da kalır.
MODEL_ANA = os.getenv("EVREN_MODEL", "llm-large")          # kullanıcıya giden cevap
MODEL_HIZLI = os.getenv("EVREN_MODEL_HIZLI", "llm-fast")   # niyet/öneri/denetim ajanları

# bge-m3-embed: dokümantasyonda "en yüksek ilk-isabet: R@1 0,95" ve çıktısı
# 1024 BOYUT — mevcut Qdrant koleksiyon ayarınızla (VECTOR_SIZE=1024) birebir
# uyumlu. Diğer seçenek "embed" 2560 boyut üretir; ona geçilecekse koleksiyonun
# BOYUTU da değiştirilip sıfırdan kurulmalıdır (docs: "koleksiyonun kullanılacak
# modele uygun boyutla oluşturulması gerekmektedir").
EMBED_MODEL = os.getenv("EVREN_EMBED_MODEL", "bge-m3-embed")
RERANK_MODEL = os.getenv("EVREN_RERANK_MODEL", "rerank")

# ⚠️ RERANK VARSAYILAN OLARAK KAPALI — YARIŞMA DOKÜMANTASYONUNUN KENDİ ÖLÇÜMÜ:
# model kartında rerank satırı "R@1 0,95 -> 0,55 (önerilmez)" diyor; yani yoğun
# getirmeden sonra yeniden sıralamak ilk-isabeti neredeyse YARIYA düşürüyor.
# Referans getirme hattında (docs 12. bölüm) de bilinçli olarak yok.
# Denemek isterseniz: EVREN_RERANK=true
RERANK_AKTIF = os.getenv("EVREN_RERANK", "false").strip().lower() in ("true", "1", "acik", "açık", "evet")

# Bağlam pencereleri devasa (llm-large 262.144) — eski num_predict/num_ctx
# dertleri bitti. Yine de üretimi sınırsız bırakmıyoruz.
MAX_TOKENS = int(os.getenv("EVREN_MAX_TOKENS", "2048"))
ZAMAN_ASIMI = float(os.getenv("EVREN_TIMEOUT", "120"))
EMBED_PARTI = int(os.getenv("EVREN_EMBED_BATCH", "64"))


def hazir_mi() -> bool:
    """Anahtar tanımlı mı? (Tanımlı değilse çağıranlar eski yola düşebilir.)"""
    return bool(API_KEY)


def _basliklar() -> dict:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


class EvrenHatasi(RuntimeError):
    pass


# =============================================================================
# 1. SOHBET (streaming) — OpenAI /v1/chat/completions
# =============================================================================
async def sohbet_akisi(
    mesajlar: List[dict],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
    timeout: Optional[float] = None,
):
    """Cevabı parça parça (token token) üretir — async generator.

    Ollama'nın /api/chat akışından farkı: burada SSE ("data: {...}" satırları)
    var ve içerik `choices[0].delta.content` altında geliyor. Akış
    "data: [DONE]" ile bitiyor.

    Sunucu streaming desteklemezse otomatik olarak tek seferlik (non-stream)
    çağrıya düşer — kullanıcı yine cevabını alır, sadece harf harf akmaz.
    """
    if not hazir_mi():
        raise EvrenHatasi("EVREN_API_KEY tanımlı değil (.env dosyanı kontrol et).")

    govde = {
        "model": model or MODEL_ANA,
        "messages": mesajlar,
        "max_tokens": max_tokens or MAX_TOKENS,
        "temperature": temperature,
        "stream": True,
    }
    url = f"{BASE_URL}/chat/completions"
    hic_veri_geldi = False

    try:
        async with httpx.AsyncClient(timeout=timeout or ZAMAN_ASIMI) as istemci:
            async with istemci.stream("POST", url, headers=_basliklar(), json=govde) as cevap:
                if cevap.status_code >= 400:
                    ham = await cevap.aread()
                    raise EvrenHatasi(f"HTTP {cevap.status_code}: {ham[:300].decode('utf-8', 'replace')}")
                async for satir in cevap.aiter_lines():
                    if not satir:
                        continue
                    if satir.startswith("data:"):
                        satir = satir[5:].strip()
                    if satir == "[DONE]":
                        break
                    try:
                        parca = json.loads(satir)
                    except json.JSONDecodeError:
                        continue
                    for secim in parca.get("choices") or []:
                        icerik = (secim.get("delta") or {}).get("content") or ""
                        if icerik:
                            hic_veri_geldi = True
                            yield icerik
        if hic_veri_geldi:
            return
        logger.warning("Akış boş döndü — streaming desteklenmiyor olabilir, tek seferlik çağrıya düşülüyor.")
    except EvrenHatasi:
        raise
    except Exception as e:
        logger.warning(f"Streaming başarısız ({type(e).__name__}: {e}), tek seferlik çağrıya düşülüyor.")

    # --- Yedek: non-stream ---
    metin = await sohbet_tek_seferlik(mesajlar, model, max_tokens, temperature, timeout)
    if metin:
        yield metin


async def sohbet_tek_seferlik(
    mesajlar: List[dict],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
    timeout: Optional[float] = None,
) -> str:
    """Akışsız sohbet çağrısı (yedek yol ve kısa ajan çağrıları için)."""
    govde = {
        "model": model or MODEL_ANA,
        "messages": mesajlar,
        "max_tokens": max_tokens or MAX_TOKENS,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=timeout or ZAMAN_ASIMI) as istemci:
        r = await istemci.post(f"{BASE_URL}/chat/completions", headers=_basliklar(), json=govde)
        r.raise_for_status()
        veri = r.json()
    try:
        return veri["choices"][0]["message"]["content"] or ""
    except Exception:
        raise EvrenHatasi(f"Beklenmeyen sohbet yanıtı: {json.dumps(veri)[:300]}")


# =============================================================================
# 2. EMBEDDING — OpenAI /v1/embeddings
#
# ⚠️ ÖNEMLİ: Embedding modelini değiştirmek, Qdrant'taki MEVCUT vektörleri
# GEÇERSİZ kılar. Boyut aynı (1024) olsa bile vektör uzayı farklıdır; eski
# vektörlerle yeni sorgu vektörlerini kıyaslamak sessizce saçma sonuç üretir.
# Bu modüle geçtikten sonra koleksiyonu SIFIRDAN kurmak ZORUNLUDUR:
#     python -m chatbot.indexing
# =============================================================================
def _embed_istek(metinler: List[str], model: str, timeout: float) -> List[List[float]]:
    govde = {"model": model, "input": metinler}
    with httpx.Client(timeout=timeout) as istemci:
        r = istemci.post(f"{BASE_URL}/embeddings", headers=_basliklar(), json=govde)
        if r.status_code >= 400:
            raise EvrenHatasi(f"Embedding HTTP {r.status_code}: {r.text[:300]}")
        veri = r.json()

    # Standart OpenAI biçimi: {"data": [{"embedding": [...], "index": 0}, ...]}
    if isinstance(veri, dict) and isinstance(veri.get("data"), list):
        sirali = sorted(veri["data"], key=lambda d: d.get("index", 0))
        return [d["embedding"] for d in sirali]
    # Bazı geçitler doğrudan liste döner: [[...], [...]]
    if isinstance(veri, list):
        return veri
    # Ya da {"embeddings": [[...]]}
    if isinstance(veri, dict) and isinstance(veri.get("embeddings"), list):
        return veri["embeddings"]
    raise EvrenHatasi(f"Beklenmeyen embedding yanıtı: {json.dumps(veri)[:300]}")


def embed_batch(
    metinler: Iterable[str],
    normalize: bool = False,
    url: Optional[str] = None,      # geriye dönük uyumluluk (yok sayılır)
    ilerleme: bool = False,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
) -> np.ndarray:
    """Metin listesini vektör matrisine çevirir.

    İmza bilerek eski `embedding_client.embed_batch` ile AYNI: çağıran kodun
    (chatbot/generate_response.py, chatbot/indexing.py, rag/embedder.py)
    değişmesine gerek kalmasın.
    """
    metinler = [str(m) for m in metinler]
    if not metinler:
        return np.empty((0, 0), dtype=np.float32)
    if not hazir_mi():
        raise EvrenHatasi("EVREN_API_KEY tanımlı değil (.env dosyanı kontrol et).")

    model = model or EMBED_MODEL
    timeout = timeout or ZAMAN_ASIMI
    tum_vektorler: List[List[float]] = []

    for i in range(0, len(metinler), EMBED_PARTI):
        parti = metinler[i:i + EMBED_PARTI]
        son_hata = None
        for deneme in range(3):                      # geçici hatalarda yeniden dene
            try:
                tum_vektorler.extend(_embed_istek(parti, model, timeout))
                son_hata = None
                break
            except Exception as e:
                son_hata = e
                if deneme < 2:
                    time.sleep(2 * (deneme + 1))
        if son_hata:
            raise EvrenHatasi(f"Embedding partisi başarısız ({i}-{i+len(parti)}): {son_hata}")
        if ilerleme:
            print(f"  embedding: {min(i + EMBED_PARTI, len(metinler))}/{len(metinler)}", flush=True)

    matris = np.asarray(tum_vektorler, dtype=np.float32)
    if normalize and matris.size:
        normlar = np.linalg.norm(matris, axis=1, keepdims=True)
        normlar[normlar == 0] = 1.0
        matris = matris / normlar
    return matris


def embed_hazir_mi() -> bool:
    """rag/embedder.py'nin beklediği isim."""
    try:
        return embed_batch(["deneme"]).size > 0
    except Exception:
        return False


# =============================================================================
# 3. RERANK
#
# ⚠️ Rerank OpenAI standardında DEĞİL; geçitler farklı şemalar kullanıyor.
# Bu yüzden bilinen üç biçim SIRAYLA deneniyor ve ÇALIŞAN biçim hatırlanıyor
# (sonraki çağrılarda doğrudan o kullanılıyor). Dokümantasyondaki örnek kod
# elimize geçince bu deneme-yanılma tek biçime sabitlenebilir.
# =============================================================================
_CALISAN_RERANK_BICIMI: Optional[str] = None

_RERANK_BICIMLERI = {
    # Cohere/Jina tarzı
    "documents": lambda model, soru, metinler, n: {
        "model": model, "query": soru, "documents": metinler, "top_n": n},
    # TEI (text-embeddings-inference) tarzı
    "texts": lambda model, soru, metinler, n: {
        "model": model, "query": soru, "texts": metinler},
    # top_n'siz sade biçim
    "sade": lambda model, soru, metinler, n: {
        "model": model, "query": soru, "documents": metinler},
}


def _rerank_yanitini_coz(veri) -> List[tuple]:
    """Yanıttan [(index, skor), ...] çıkarır — farklı şemaları tolere eder."""
    kayitlar = None
    if isinstance(veri, list):
        kayitlar = veri
    elif isinstance(veri, dict):
        for anahtar in ("results", "data", "scores", "rankings"):
            if isinstance(veri.get(anahtar), list):
                kayitlar = veri[anahtar]
                break
    if kayitlar is None:
        raise EvrenHatasi(f"Beklenmeyen rerank yanıtı: {json.dumps(veri)[:300]}")

    cikti = []
    for sira, k in enumerate(kayitlar):
        if isinstance(k, (int, float)):                    # düz skor listesi
            cikti.append((sira, float(k)))
            continue
        if not isinstance(k, dict):
            continue
        idx = k.get("index", k.get("corpus_id", k.get("document_index", sira)))
        skor = k.get("relevance_score", k.get("score", k.get("logit", 0.0)))
        cikti.append((int(idx), float(skor)))
    return cikti


async def rerank(soru: str, metinler: List[str], top_n: int = 4,
                 model: Optional[str] = None, timeout: float = 30.0) -> List[int]:
    """Metinleri soruya göre yeniden sıralar; en iyi `top_n` INDEKSİ döner.

    Hata durumunda boş liste döner — çağıran taraf orijinal sırayı korur
    (rerank bir iyileştirme, zorunluluk değil).
    """
    global _CALISAN_RERANK_BICIMI
    if not RERANK_AKTIF:
        return []          # bkz. RERANK_AKTIF notu — dokümantasyon önermiyor
    if not (hazir_mi() and metinler):
        return []

    model = model or RERANK_MODEL
    denenecek = ([_CALISAN_RERANK_BICIMI] if _CALISAN_RERANK_BICIMI
                 else list(_RERANK_BICIMLERI.keys()))

    async with httpx.AsyncClient(timeout=timeout) as istemci:
        for bicim in denenecek:
            govde = _RERANK_BICIMLERI[bicim](model, soru, metinler, top_n)
            try:
                r = await istemci.post(f"{BASE_URL}/rerank", headers=_basliklar(), json=govde)
                if r.status_code >= 400:
                    logger.debug(f"rerank biçimi '{bicim}' reddedildi: HTTP {r.status_code} {r.text[:120]}")
                    continue
                ciftler = _rerank_yanitini_coz(r.json())
                if not ciftler:
                    continue
                if _CALISAN_RERANK_BICIMI != bicim:
                    _CALISAN_RERANK_BICIMI = bicim
                    logger.info(f"✅ Rerank biçimi belirlendi: '{bicim}'")
                ciftler.sort(key=lambda x: x[1], reverse=True)
                return [i for i, _ in ciftler if 0 <= i < len(metinler)][:top_n]
            except Exception as e:
                logger.debug(f"rerank biçimi '{bicim}' hata verdi: {type(e).__name__}: {e}")
                continue

    logger.warning("Rerank hiçbir biçimde çalışmadı — sıralama değiştirilmeden devam ediliyor.")
    return []


# =============================================================================
# 4. QDRANT (yarışma sunucusu)
# =============================================================================
# Dokümantasyondaki referans yapılandırma (12. bölüm):
#     qc = QdrantClient(url="https://evren-vektor.ssyz.org.tr", port=443,
#                       prefix=os.environ["EVREN_TEAM"],
#                       api_key=os.environ["EVREN_QDRANT_KEY"], timeout=600)
# port=443 ve prefix ZORUNLU: prefix verilmezse istekler /team28/collections
# yerine köke gider ve 404 alırsınız.
QDRANT_URL = os.getenv("EVREN_QDRANT_URL", os.getenv("QDRANT_HOST", "http://qdrant:6333"))
QDRANT_API_KEY = os.getenv("EVREN_QDRANT_KEY", os.getenv("QDRANT_API_KEY", "")) or None
TAKIM = os.getenv("EVREN_TEAM", "").strip("/") or None


def qdrant_ayarlari() -> dict:
    """QdrantClient(**qdrant_ayarlari()) ile kullanılır."""
    url = QDRANT_URL.rstrip("/")
    onek = TAKIM
    port = None

    # Adres yol önekli verilmişse (.../team28) öneki ayır — qdrant-client
    # bunu `prefix` parametresiyle ayrı bekliyor.
    for sema in ("https://", "http://"):
        if url.startswith(sema):
            govde = url[len(sema):]
            if "/" in govde:
                sunucu, _, yol = govde.partition("/")
                url = sema + sunucu
                onek = onek or (yol.strip("/") or None)
            if sema == "https://":
                port = 443
            break

    ayar = {"url": url, "timeout": int(os.getenv("EVREN_QDRANT_TIMEOUT", "600"))}
    if port:
        ayar["port"] = port
    if onek:
        ayar["prefix"] = onek
    if QDRANT_API_KEY:
        ayar["api_key"] = QDRANT_API_KEY
    return ayar


# =============================================================================
# 5. KENDİ KENDİNİ TEST — python evren_client.py
# =============================================================================
def _kendini_test(sadece: str = ""):
    import asyncio

    print("=" * 70)
    print(f"BASE_URL      : {BASE_URL}")
    print(f"API_KEY       : {'tanımlı ✅' if API_KEY else 'YOK ❌ (.env kontrol et)'}")
    print(f"Ana model     : {MODEL_ANA}   | hızlı: {MODEL_HIZLI}")
    print(f"Embedding     : {EMBED_MODEL} | rerank: {RERANK_MODEL}")
    q = qdrant_ayarlari()
    print(f"Qdrant        : {q.get('url')} prefix={q.get('prefix')} anahtar={'var' if q.get('api_key') else 'yok'}")
    print("=" * 70)
    if not API_KEY:
        return 1

    hata = 0

    if sadece in ("", "sohbet"):
        print("\n[1] SOHBET (streaming)")
        try:
            async def calis():
                bas = time.time()
                ilk = None
                parcalar = []
                async for p in sohbet_akisi(
                    [{"role": "user", "content": "Tek cümlede kendini tanıt."}],
                    max_tokens=64,
                ):
                    if ilk is None:
                        ilk = round(time.time() - bas, 2)
                    parcalar.append(p)
                print(f"  ilk token: {ilk}sn | toplam: {round(time.time()-bas,2)}sn")
                print(f"  cevap: {''.join(parcalar)[:200]}")
            asyncio.run(calis())
            print("  ✅")
        except Exception as e:
            hata += 1
            print(f"  ❌ {type(e).__name__}: {e}")

    if sadece in ("", "embed"):
        print("\n[2] EMBEDDING")
        try:
            bas = time.time()
            m = embed_batch(["kâr payı oranı nedir", "ödüllü kampanyalar"])
            print(f"  şekil: {m.shape} | süre: {round(time.time()-bas,2)}sn")
            if m.shape[1] != 1024:
                print(f"  ⚠️ BOYUT {m.shape[1]} — Qdrant koleksiyonu 1024 bekliyor! "
                      f"VECTOR_SIZE'ı güncelleyip koleksiyonu yeniden kurman gerekir.")
            print("  ✅")
        except Exception as e:
            hata += 1
            print(f"  ❌ {type(e).__name__}: {e}")

    if sadece in ("", "rerank"):
        print("\n[3] RERANK")
        try:
            metinler = [
                "Albaraka Türk konut finansmanı kampanyası",
                "Kuveyt Türk kâr payı oranı %2,99 taksitlendirme",
                "Hava durumu bugün güneşli",
            ]
            idx = asyncio.run(rerank("kâr payı oranı en düşük hangisi", metinler, top_n=2))
            print(f"  sıralama: {idx} (beklenen ilk: 1) | biçim: {_CALISAN_RERANK_BICIMI}")
            print("  ✅" if idx else "  ⚠️ boş döndü — dokümantasyondaki rerank örneğini paylaş")
        except Exception as e:
            hata += 1
            print(f"  ❌ {type(e).__name__}: {e}")

    print("\n" + ("HEPSİ ÇALIŞTI ✅" if hata == 0 else f"{hata} BAŞARISIZ ❌"))
    return 1 if hata else 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sadece", default="", choices=["", "sohbet", "embed", "rerank"])
    raise SystemExit(_kendini_test(ap.parse_args().sadece))