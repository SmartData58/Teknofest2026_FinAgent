# =============================================================================
# indexer.py — RAG İndeksi Kurulumu: kampanyalar → belgeler → vektörler
#
# ⚠️ DEPRECATED (Ocak/Ağustos 2026 Mongo geçişinden sonra):
# Bu pipeline (embedder.py + indexer.py + vector_store.py + retriever.py) SQL
# veritabanındaki (db.models.Kampanya) kampanyaları okuyup Qdrant'ın
# "banka_kampanyalari" koleksiyonuna yazıyor. Proje NoSQL/MongoDB'ye taşındıktan
# sonra GÜNCEL/CANLI sistem artık chatbot.py'deki auto_init_qdrant() — o da AYNI
# Qdrant koleksiyonunu MongoDB'den besliyor.
#
# indeksi_kur() çağrıldığında vector_store.kaydet() koleksiyonu SİLİP YENİDEN
# KURUYOR (bkz. rag/vector_store.py) — yani bu script yanlışlıkla çalıştırılırsa
# chatbot.py'nin (canlı sohbet servisinin) beslediği veriyi tamamen SİLER.
# Bu yüzden aşağıya kazara çalıştırmayı engelleyen bir onay adımı eklendi.
# SQL veritabanı artık kullanılmıyorsa bu dosya (ve embedder.py/retriever.py,
# vector_store.py'nin kaydet() kısmı) güvenle silinebilir/arşivlenebilir.
# =============================================================================

from db.database import get_session
from db.models import Kampanya
from backend._legacy.rag.embedder import vektorle, embedder_hazir
from backend._legacy.rag.vector_store import kaydet

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
    import os

    # 🛡️ KAZARA ÇALIŞTIRMA KORUMASI: indeksi_kur() -> kaydet() koleksiyonu SİLİP
    # yeniden kuruyor. Proje artık MongoDB kullandığından bu SQL tabanlı pipeline
    # muhtemelen artık canlı veri kaynağı DEĞİL — yanlışlıkla çalıştırılması,
    # chatbot.py'nin (gerçek sohbet servisinin) MongoDB'den beslediği Qdrant
    # koleksiyonunu tamamen siler. Bilinçli bir çalıştırma olduğunu belirtmek için
    # ortam değişkeni gerektiriyoruz.
    if os.environ.get("FINAGENT_ALLOW_LEGACY_SQL_INDEX") != "1":
        raise SystemExit(
            "🚫 Bu script (SQL veritabanı tabanlı eski RAG indeksleyicisi) artık "
            "chatbot.py'nin MongoDB tabanlı auto_init_qdrant() ile aynı Qdrant "
            "koleksiyonunu ('banka_kampanyalari') kullanıyor ve onu SİLİP YENİDEN "
            "KURUYOR. Proje MongoDB'ye taşındığı için bunu çalıştırmak muhtemelen "
            "canlı sohbet servisinin verisini siler.\n"
            "Bunu bilerek ve isteyerek yapmak istiyorsanız:\n"
            "  FINAGENT_ALLOW_LEGACY_SQL_INDEX=1 python indexer.py"
        )

    n = indeksi_kur()
    if n > 0:
        print(f"✅ RAG indeksi kuruldu: {n} kampanya belgesi başarıyla vektörlendi.")