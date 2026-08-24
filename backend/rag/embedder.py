# =============================================================================
# embedder.py — Metin → Vektör (rag/ paketinin arayüzü)
#
# 🚀 YARIŞMA API'SİNE GEÇİŞ: gerçek çağrı artık evren_client üzerinden
# bge-m3-embed modeline gidiyor (1024 boyut). Yerel embedding servisi (
# embedding:8001) ve embedding_client.py'ye bağımlılık kaldırıldı.
#
# ⚠️ Embedding modeli değiştiği için Qdrant'taki ESKİ vektörler geçersizdir —
# koleksiyon sıfırdan kurulmalıdır: python -m chatbot.indexing
# =============================================================================

try:
    from evren_client import embed_batch, embed_hazir_mi
except ModuleNotFoundError:
    from chatbot.evren_client import embed_batch, embed_hazir_mi

def vektorle(metinler: list[str], ilerleme: bool = False):
    return embed_batch(metinler, normalize=True, ilerleme=ilerleme)

def embedder_hazir() -> bool:
    return embed_hazir_mi()