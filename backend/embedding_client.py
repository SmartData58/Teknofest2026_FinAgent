# =============================================================================
# embedding_client.py — TEK, PAYLAŞILAN embedding-servisi çağrı katmanı.
#
# chatbot/generate_response.py (LangChain Embeddings adaptörü, OzelQwenEmbedder)
# ve rag/embedder.py (numpy tabanlı ham arayüz, vektorle()) önceden birbirinden
# BAĞIMSIZ olarak neredeyse birebir aynı kodu (requests.post + retry + hata
# yönetimi + L2 normalize) tekrarlıyordu. Bu, tutarsızlık riski doğuruyordu —
# nitekim rag_ingest.py'deki ÜÇÜNCÜ bir kopyada embed_query, hata durumunda
# [][0] yaparak IndexError ile çöküyordu, diğer iki kopyada bu düzeltilmişti.
# chatbot/ ve rag/ aynı container/pakette çalıştığı için artık TEK gerçek kaynak
# burası: hem chatbot/generate_response.py hem rag/embedder.py bunu kullanır.
# =============================================================================

import os
import time
import numpy as np
import requests
from loguru import logger


def _resolve_embedding_url() -> str:
    # chatbot/ tarafı tam URL'yi EMBEDDING_URL ile veriyor (ör. ".../api/embed").
    # rag/ tarafı ise taban URL'yi FINAGENT_EMBED_URL ile veriyor ve /api/embed
    # kendisi ekliyordu. İkisi de desteklenir; EMBEDDING_URL varsa o önceliklidir.
    tam_url = os.environ.get("EMBEDDING_URL")
    if tam_url:
        return tam_url
    taban = os.environ.get("FINAGENT_EMBED_URL", "http://embedding:8001")
    return f"{taban.rstrip('/')}/api/embed"


EMBEDDING_URL = _resolve_embedding_url()
ZAMAN_ASIMI = 120
MAKS_KARAKTER = 3000
PARTI_BUYUKLUGU = 8
MAKS_DENEME = 2
VARSAYILAN_BOYUT = 1024


def _parti_gonder(girdi: list[str], url: str) -> np.ndarray:
    son_hata: Exception | None = None
    for deneme in range(1, MAKS_DENEME + 1):
        try:
            cevap = requests.post(url, json={"input": girdi}, timeout=ZAMAN_ASIMI)
            cevap.raise_for_status()
            return np.asarray(cevap.json()["embeddings"], dtype=np.float32)
        except requests.RequestException as e:
            son_hata = e
            logger.warning(f"Embedding API bağlantı hatası (deneme {deneme}/{MAKS_DENEME}): {e}")
            if deneme < MAKS_DENEME:
                time.sleep(5)
    raise son_hata  # type: ignore[misc]


def embed_batch(
    metinler: list[str],
    normalize: bool = True,
    ilerleme: bool = False,
    url: str | None = None,
) -> np.ndarray:
    """Metin listesini vektörlere çevirir: parti parti gönderir, karakter
    sınırı uygular, isteğe bağlı L2-normalize eder ve geçici hatalarda 1 kez
    yeniden dener. `normalize=False` chatbot/generate_response.py'nin ÖNCEKİ
    davranışını korumak için (Qdrant'ın COSINE mesafesi zaten normalize
    farkını otomatik ele alır, bu yüzden davranış değişmez)."""
    hedef_url = url or EMBEDDING_URL
    if not metinler:
        return np.empty((0, VARSAYILAN_BOYUT), dtype=np.float32)

    kirpik = [m[:MAKS_KARAKTER] for m in metinler]
    parcalar = []
    for i in range(0, len(kirpik), PARTI_BUYUKLUGU):
        parcalar.append(_parti_gonder(kirpik[i:i + PARTI_BUYUKLUGU], hedef_url))
        if ilerleme:
            print(f"  vektörlendi: {min(i + PARTI_BUYUKLUGU, len(kirpik))}/{len(kirpik)}")
    matris = np.vstack(parcalar)

    if normalize:
        normlar = np.linalg.norm(matris, axis=1, keepdims=True)
        normlar[normlar == 0] = 1.0
        matris = matris / normlar
    return matris


def embed_hazir_mi(url: str | None = None) -> bool:
    hedef_url = url or EMBEDDING_URL
    try:
        cevap = requests.post(hedef_url, json={"input": ["test"]}, timeout=10)
        return cevap.status_code == 200
    except requests.RequestException:
        return False