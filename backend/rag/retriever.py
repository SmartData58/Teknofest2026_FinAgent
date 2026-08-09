# =============================================================================
# retriever.py — Anlamsal Arama: soru → en ilgili kampanya belgeleri
# =============================================================================

from dataclasses import dataclass
from rag.embedder import vektorle
from rag.vector_store import belgeleri_yukle

SORU_ONEKI = ("Instruct: Verilen soruya cevap olabilecek banka kampanyalarını bul\n"
              "Query: ")

MIN_BENZERLIK = 0.45

@dataclass
class AramaSonucu:
    kampanya_id: int
    belge: str
    benzerlik: float

_onbellek: tuple | None = None

def _indeks():
    global _onbellek
    if _onbellek is None:
        _onbellek = belgeleri_yukle()
    return _onbellek

def onbellegi_sifirla() -> None:
    global _onbellek
    _onbellek = None

def ara(soru: str, k: int = 4) -> list[AramaSonucu]:
    idler, belgeler, matris = _indeks()
    if not idler:
        return []
    soru_vektoru = vektorle([SORU_ONEKI + soru])[0]
    benzerlikler = matris @ soru_vektoru 
    sirali = benzerlikler.argsort()[::-1][:k]
    return [
        AramaSonucu(idler[i], belgeler[i], float(benzerlikler[i]))
        for i in sirali
        if benzerlikler[i] >= MIN_BENZERLIK
    ]