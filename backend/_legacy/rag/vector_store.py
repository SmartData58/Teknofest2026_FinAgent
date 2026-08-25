# =============================================================================
# vector_store.py — Vektör Deposu (Qdrant Entegrasyonu)
# =============================================================================

import os
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

# Docker Compose'daki qdrant servisinin HTTP portu
QDRANT_URL = os.environ.get("FINAGENT_QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = "banka_kampanyalari"
VEKTOR_BOYUT = 1024

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)

def kaydet(kayitlar: list[tuple[int, str, np.ndarray]]) -> None:
    client = get_qdrant_client()

    # Eski SQLite'daki 'DELETE FROM' mantığı: Koleksiyonu sıfırla ve yeniden aç
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VEKTOR_BOYUT, distance=Distance.COSINE),
    )

    # Qdrant'ın anlayacağı formata (PointStruct) çeviriyoruz
    points = []
    for kid, belge, vektor in kayitlar:
        points.append(
            PointStruct(
                id=kid, # Qdrant Integer ID destekler
                vector=vektor.tolist(),
                payload={"kampanya_id": kid, "belge": belge} # Metadata
            )
        )

    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )


# 🛠️ HATA DÜZELTMESİ: retriever.py `from rag.vector_store import belgeleri_yukle`
# şeklinde bu fonksiyonu import ediyordu ama bu dosyada TANIMLI DEĞİLDİ — yani
# retriever.py import edilir edilmez ImportError ile çöküyordu, bu SQL-DB tabanlı
# RAG pipeline'ı (embedder → indexer → vector_store → retriever) uçtan uca hiç
# çalışamıyordu. `kaydet()`'in yazdığı payload alanlarıyla (kampanya_id, belge)
# birebir uyumlu, Qdrant'tan tüm noktaları sayfalayarak (scroll) belleğe yükleyen
# bir okuma fonksiyonu eklendi.
def belgeleri_yukle() -> tuple[list[int], list[str], np.ndarray]:
    """Qdrant koleksiyonundaki tüm (id, belge, vektör) üçlülerini belleğe yükler.
    retriever.py bunu numpy tabanlı kosinüs benzerliği (matris @ soru_vektoru)
    hesaplamak için kullanır — embedder.vektorle() vektörleri zaten L2-normalize
    ettiği için ek bir normalize adımına gerek yoktur."""
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        return [], [], np.empty((0, VEKTOR_BOYUT), dtype=np.float32)

    idler: list[int] = []
    belgeler: list[str] = []
    vektorler: list[list[float]] = []

    sonraki_sayfa = None
    while True:
        noktalar, sonraki_sayfa = client.scroll(
            collection_name=COLLECTION_NAME,
            with_payload=True,
            with_vectors=True,
            limit=256,
            offset=sonraki_sayfa,
        )
        for nokta in noktalar:
            payload = nokta.payload or {}
            idler.append(payload.get("kampanya_id", nokta.id))
            belgeler.append(payload.get("belge", ""))
            vektorler.append(nokta.vector)
        if sonraki_sayfa is None:
            break

    if not idler:
        return [], [], np.empty((0, VEKTOR_BOYUT), dtype=np.float32)

    matris = np.asarray(vektorler, dtype=np.float32)
    return idler, belgeler, matris