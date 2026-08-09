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