# =============================================================================
# indexer.py — RAG İndeksi Kurulumu: kampanyalar → belgeler → vektörler
# =============================================================================

from db.database import get_session
from db.models import Kampanya
from rag.embedder import vektorle, embedder_hazir
from rag.vector_store import kaydet

def _alan_ozeti(k: Kampanya) -> str:
    parcalar = []
    if k.kampanya_turu:
        turler = {"ihtiyac_finansmani": "ihtiyaç finansmanı",
                  "konut_finansmani": "konut finansmanı",
                  "tasit_finansmani": "taşıt finansmanı",
                  "finansman": "finansman",
                  "yeni_musteri": "yeni müşteri kampanyası",
                  "yatirim_urunu": "yatırım/birikim ürünü",
                  "alisveris_puani": "alışveriş puanı/iade",
                  "kart": "kart kampanyası"}
        parcalar.append(f"tür: {turler.get(k.kampanya_turu, k.kampanya_turu)}")
    if k.kar_payi_orani is not None:
        parcalar.append(f"kâr payı oranı: %{k.kar_payi_orani:g}")
    if k.finansman_tutari is not None:
        parcalar.append(f"finansman tutarı: {k.finansman_tutari:,.0f} TL".replace(",", "."))
    if k.vade_ay is not None:
        parcalar.append(f"vade: {k.vade_ay} ay")
    if k.taksit_sayisi is not None:
        parcalar.append(f"taksit: {k.taksit_sayisi}")
    if k.tahsis_ucreti is not None:
        parcalar.append(f"tahsis ücreti: {k.tahsis_ucreti:g} TL")
    if k.odul_miktari is not None:
        parcalar.append(f"ödül: {k.odul_miktari:,.0f} TL".replace(",", "."))
    if k.indirim_orani is not None:
        parcalar.append(f"indirim: %{k.indirim_orani:g}")
    if k.bitis_tarihi is not None:
        parcalar.append(f"son geçerlilik: {k.bitis_tarihi}")
    if k.hedef_kitle:
        etiketler = {"yeni_musteri": "yeni müşteriler", "mevcut_musteri": "mevcut müşteriler",
                     "maas_musterisi": "maaş müşterileri", "segment": "özel segment"}
        parcalar.append(f"hedef kitle: {etiketler.get(k.hedef_kitle, k.hedef_kitle)}")
    return " | ".join(parcalar)

def belge_kur(k: Kampanya) -> str:
    satirlar = [f"Banka: {k.banka.kisa_ad}", f"Kampanya: {k.baslik}"]
    ozet = _alan_ozeti(k)
    if ozet:
        satirlar.append(f"Doğrulanmış bilgiler: {ozet}")
    satirlar.append(f"Kampanya metni: {k.ham_metin or ''}")
    return "\n".join(satirlar)

def indeksi_kur() -> int:
    if not embedder_hazir():
        raise SystemExit(
            "🚨 Embedding modeli hazır değil veya OLLAMA_URL yanlış. Ollama konteynerini kontrol et.")
            
    with get_session() as oturum:
        kampanyalar = oturum.query(Kampanya).all()
        
        # Boş veritabanı kontrolü (Numpy crash engelleme)
        if not kampanyalar:
            print("Veritabanında işlenecek kampanya bulunamadı! Lütfen önce pipeline'ı çalıştırın.")
            return 0
            
        kayitlar = [(k.id, belge_kur(k)) for k in kampanyalar]
        
    vektorler = vektorle([belge for _, belge in kayitlar], ilerleme=True)
    kaydet([(kid, belge, vektorler[i]) for i, (kid, belge) in enumerate(kayitlar)])
    return len(kayitlar)

if __name__ == "__main__":
    n = indeksi_kur()
    if n > 0:
        print(f"✅ RAG indeksi kuruldu: {n} kampanya belgesi başarıyla vektörlendi.")