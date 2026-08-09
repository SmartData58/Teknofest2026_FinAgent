# =============================================================================
# embedder.py — Metin → Vektör (Custom Uvicorn Embedding API)
# =============================================================================

import os
import time
import numpy as np
import requests

# 🚀 URL'yi senin Ozel Uvicorn/PyTorch konteynerine (8001) geri çevirdik
EMBEDDING_URL = os.environ.get("FINAGENT_EMBED_URL", "http://embedding:8001")
ZAMAN_ASIMI = 120

MAKS_KARAKTER = 3000
PARTI_BUYUKLUGU = 8

def _parti_gonder(girdi: list[str]) -> np.ndarray:
    for deneme in (1, 2):
        try:
            # Custom API'nin beklediği formata göre sadece "input" yolluyoruz
            cevap = requests.post(
                f"{EMBEDDING_URL}/api/embed",
                json={"input": girdi},
                timeout=ZAMAN_ASIMI,
            )
            cevap.raise_for_status()
            return np.asarray(cevap.json()["embeddings"], dtype=np.float32)
        except requests.RequestException as e:
            print(f"\n⚠️ Embedding API Bağlantı Hatası: {e}")
            if deneme == 2:
                raise
            time.sleep(5)
    raise AssertionError("erişilmez")

def vektorle(metinler: list[str], ilerleme: bool = False) -> np.ndarray:
    if not metinler:
        return np.empty((0, 1024), dtype=np.float32)
        
    kirpik = [m[:MAKS_KARAKTER] for m in metinler]
    parcalar = []
    for i in range(0, len(kirpik), PARTI_BUYUKLUGU):
        parcalar.append(_parti_gonder(kirpik[i:i + PARTI_BUYUKLUGU]))
        if ilerleme:
            print(f"  vektörlendi: {min(i + PARTI_BUYUKLUGU, len(kirpik))}/{len(kirpik)}")
    matris = np.vstack(parcalar)
    
    # Sıfıra bölme hatasını engellemek için güvenlik önlemi
    normlar = np.linalg.norm(matris, axis=1, keepdims=True)
    normlar[normlar == 0] = 1.0
    return matris / normlar

def embedder_hazir() -> bool:
    """
    Ollama'nın /api/tags ucu yerine, senin custom Uvicorn sunucuna 
    'test' kelimesi yollayarak ayakta olup olmadığını anlıyoruz.
    """
    try:
        cevap = requests.post(f"{EMBEDDING_URL}/api/embed", json={"input": ["test"]}, timeout=10)
        return cevap.status_code == 200
    except requests.RequestException:
        return False