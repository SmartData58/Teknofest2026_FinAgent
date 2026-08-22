# =============================================================================
# embedder.py — Metin → Vektör (rag/ paketinin arayüzü)
#
# Gerçek HTTP çağrı mantığı artık embedding_client.py'de (chatbot/ ile PAYLAŞILAN,
# tek gerçek kaynak) — bkz. embedding_client.py başındaki not. Bu dosya sadece
# rag/ paketinin geri kalanının (indexer.py, retriever.py) beklediği isim ve
# imzaları koruyan ince bir sarmalayıcı.
# =============================================================================

from embedding_client import embed_batch, embed_hazir_mi

def vektorle(metinler: list[str], ilerleme: bool = False):
    return embed_batch(metinler, normalize=True, ilerleme=ilerleme)

def embedder_hazir() -> bool:
    return embed_hazir_mi()