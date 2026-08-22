# =============================================================================
# indexing.py — Qdrant vektör indeksinin MongoDB'den kurulması
#
# ⚠️ ARTIK UYGULAMA AÇILIŞINDA OTOMATİK ÇALIŞMIYOR (main.py'den kaldırıldı).
#
# Sebep: auto_init_qdrant() koleksiyonu force_recreate=True ile SIFIRDAN kuruyor.
# Vektörlemeyi kendi pipeline'ınız (kampanyaları çektikten sonra) yaptığı için,
# uygulamanın her açılışı sizin yazdığınız GERÇEK vektörleri siliyor ve yerine
# MongoDB'de ne bulursa onu (ki bu, finagent.kampanyalar'daki 32 adetlik sahte
# demo havuzuydu) koyuyordu. uvicorn --reload ile çalışıldığında bu, her kod
# değişikliğinde tekrarlanıyordu — "hep 32 kampanya" sorununun kaynağı buydu.
#
# Fonksiyon silinmedi; gerekirse elle çalıştırılabilir:
#     python -m chatbot.indexing
#
# 📌 KENDİ VEKTÖRLEME PIPELINE'INIZ İÇİN SÖZLEŞME:
# Qdrant'a yazarken aşağıdakileri KORUMAK ZORUNDASINIZ, yoksa sohbet tarafı bozulur:
#   • content_payload_key = "belge"  -> yoksa arama sonuçları BOŞ İÇERİK döner
#   • payload["banka_kodu"]          -> yoksa bankaya göre filtreli arama hiç eşleşmez
#     (chatbot/generate_response.py::_banka_filtresi bu alana bakar; değeri
#      chatbot.intent.banka_bul() ile üretilmeli, ör. "Kuveyt Türk" -> "kuveytturk")
#   • payload["kampanya_id"]         -> kaynak gösterimi için kullanılır
# Durumu doğrulamak için: GET /health  (qdrant bölümü uyarı verirse hizalayın)
#
# ⚠️ TEK GERÇEK KAYNAK: Bu fonksiyon önceden hem main.py'de hem chatbot.py'de
# AYRI AYRI (kopyala-yapıştır) tanımlıydı ve ikisi zamanla BİRBİRİNDEN AYRIŞTI:
# chatbot.py'deki sürüme belgelere `banka_kodu` metadata'sı eklenmişti, main.py'deki
# sürüme eklenmemişti. Uvicorn'un yüklediği gerçek uygulama main.py olduğu için,
# canlı sistemde Qdrant'a yazılan belgelerde `banka_kodu` HİÇ BULUNMUYORDU —
# oysa chatbot/generate_response.py'deki vektör arama filtresi
# (_banka_filtresi -> FieldCondition(key="banka_kodu")) tam olarak bu alana
# bakıyor. Sonuç: banka filtreli her arama HİÇBİR ZAMAN eşleşme bulamıyor,
# her seferinde filtresiz yedek aramaya düşüyordu (yani "Kuveyt Türk'ün
# kampanyaları" gibi sorularda vektör tarafı bankaya göre daraltma yapamıyordu).
# Artık her iki entrypoint de bu tek modülü import ediyor; bir daha ayrışamazlar.
# =============================================================================

import os
from loguru import logger
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from chatbot.intent import banka_bul

QDRANT_URL = os.getenv("QDRANT_HOST", "http://qdrant:6333")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")
COLLECTION_NAME = "banka_kampanyalari"


def _kampanya_belgesi_olustur(k: dict) -> Document:
    """Tek bir MongoDB kampanya kaydını, vektörlenecek LangChain Document'ine çevirir."""
    banka = k.get("banka_adi", k.get("banka", "Bilinmeyen Banka"))
    if isinstance(banka, dict):
        banka = banka.get("kisa_ad", "Bilinmeyen Banka")
    kampanya_adi = k.get("kampanya_adi", k.get("baslik", "Kampanya"))
    kar_payi = k.get("kar_payi", k.get("kar_payi_orani", 0))
    vade = k.get("vade", k.get("vade_ay", 0))
    odul = k.get("odul_tl", k.get("odul_miktari", 0))

    icerik = (
        f"Banka: {banka}\n"
        f"Kampanya: {kampanya_adi}\n"
        f"Kâr Payı/Faiz Oranı: %{kar_payi}\n"
        f"Maksimum Vade: {vade} Ay\n"
        f"Ödül Miktarı: {odul} TL"
    )
    if k.get("kosullar"):
        icerik += f"\nKoşullar: {k.get('kosullar')}"
    if k.get("ham_metin"):
        icerik += f"\nDetay: {k.get('ham_metin')}"

    return Document(
        page_content=icerik,
        metadata={
            "kampanya_id": str(k.get("_id", "")),
            # 🧭 Vektör aramada banka filtresi bu alana bakar (bkz. modül başındaki not).
            "banka_kodu": banka_bul(str(banka)),
            "banka_adi": str(banka),
        },
    )


def _varsayilan_embedder():
    """LangChain Embeddings arayüzü — paylaşılan embedding_client üzerinden.

    Neden burada: auto_init_qdrant'a embedder verilmezse, onu almak için
    `chatbot.generate_response` import etmek gerekirdi; o modül de
    `chatbot.agents`'ı çekiyor ve orada modül seviyesinde ChatOllama örnekleniyor.
    Yani sadece vektörleme yapmak isteyen bir pipeline adımı, LLM sohbet
    yığınının tamamını yüklemek (ve Ollama ayarları bozuksa patlamak) zorunda
    kalıyordu. Bu hafif sarmalayıcı o zinciri tamamen atlar.
    """
    from langchain_core.embeddings import Embeddings
    from embedding_client import embed_batch

    class _PipelineEmbedder(Embeddings):
        def embed_documents(self, texts):
            return embed_batch(texts, normalize=False, ilerleme=True).tolist()

        def embed_query(self, text):
            sonuc = self.embed_documents([text])
            return sonuc[0] if sonuc else []

    return _PipelineEmbedder()


def _kampanyalari_oku() -> tuple[list, str]:
    """MongoDB'den kampanyaları okur: önce smartdata.processed_campaigns,
    boşsa finagent.kampanyalar (chatbot/generate_response.py ile aynı sıra).

    (kayitlar, kaynak_adi) döner — kaynak adı loglanıyor ki hangi koleksiyondan
    vektörlendiği görünsün. Daha önce bu görünmediği için, smartdata boş olduğunda
    sessizce finagent.kampanyalar'daki 32 adetlik SAHTE DEMO havuzu vektörleniyor
    ve kimse fark etmiyordu.
    """
    from pymongo import MongoClient

    client = MongoClient(MONGO_URI)
    try:
        kampanyalar = list(client["smartdata"]["processed_campaigns"].find({}))
        if kampanyalar:
            return kampanyalar, "smartdata.processed_campaigns"
        kampanyalar = list(client["finagent"]["kampanyalar"].find({}))
        return kampanyalar, "finagent.kampanyalar"
    finally:
        client.close()


async def auto_init_qdrant(embeddings=None) -> int:
    """Qdrant koleksiyonunu MongoDB'deki kampanyalardan sıfırdan kurar.
    Yüklenen belge sayısını döner (hata/veri yoksa 0).

    `embeddings` verilmezse hafif varsayılan embedder kullanılır
    (bkz. _varsayilan_embedder) — pipeline'dan çağırmayı kolaylaştırır.
    """
    try:
        logger.info("⏳ Qdrant vektör veritabanı inşa ediliyor...")

        kampanyalar, kaynak = _kampanyalari_oku()
        if not kampanyalar:
            logger.warning("❌ Qdrant için MongoDB'de veri bulunamadı! Mevcut koleksiyon korunuyor.")
            return 0

        logger.info(f"📦 Veri kaynağı: {kaynak} ({len(kampanyalar)} kayıt)")

        # 🚨 Sahte demo verisi uyarısı: tools.py'deki test havuzu tam 32 kayıttır.
        # Gerçek veri yerine yanlışlıkla onu vektörlemek, bu projede daha önce
        # uzun süre fark edilmeden yaşandı.
        if kaynak == "finagent.kampanyalar" and len(kampanyalar) == 32:
            logger.warning(
                "🚨 DİKKAT: finagent.kampanyalar'dan tam 32 kayıt okundu — bu, tools.py "
                "içindeki SAHTE DEMO havuzunun boyutuyla birebir aynı. Gerçek veriniz "
                "smartdata.processed_campaigns'e yazılmamış olabilir. Doğrulamak için: "
                "python mongo_durum.py"
            )

        if embeddings is None:
            embeddings = _varsayilan_embedder()

        docs = [_kampanya_belgesi_olustur(k) for k in kampanyalar]
        logger.info(f"⏳ {len(docs)} kampanya vektörleniyor ve Qdrant'a yükleniyor...")

        # 🛠️ Koleksiyon ARTIK ÖNCEDEN SİLİNMİYOR. Eski kodda koleksiyon en başta
        # delete_collection() ile siliniyor, sonra Mongo okunuyor ve vektörleme
        # (dakikalarca sürebilen bir işlem) yapılıyordu. Bu arada gelen sohbet
        # istekleri BOŞ bir koleksiyonda arama yapıyordu; Mongo boşsa veya
        # embedding servisi hata verirse koleksiyon kalıcı olarak boş kalıyordu.
        # from_documents(force_recreate=True) zaten koleksiyonu atomik biçimde
        # yeniden kurar — yani silme işlemi, yerine koyacak veri hazır olduğunda
        # ve tek adımda gerçekleşir.
        QdrantVectorStore.from_documents(
            docs,
            embeddings,
            url=QDRANT_URL,
            collection_name=COLLECTION_NAME,
            content_payload_key="belge",
            force_recreate=True,
        )
        logger.info(f"✅ Qdrant vektör veritabanı {len(docs)} kampanya ile oluşturuldu!")
        return len(docs)
    except Exception as e:
        logger.error(f"Qdrant otomatik kurulum hatası: {e}")
        return 0


def qdrant_durumu() -> dict:
    """Qdrant koleksiyonunun CANLI durumunu okur — SALT OKUNUR, hiçbir şey yazmaz/silmez.

    /health ucu bunu kullanır. Kendi vektörleme pipeline'ınız çalıştıktan sonra
    payload sözleşmesine (bkz. modül başındaki not) uyup uymadığını buradan
    doğrulayabilirsiniz.
    """
    try:
        client = QdrantClient(url=QDRANT_URL)
        if not client.collection_exists(COLLECTION_NAME):
            return {
                "koleksiyon": COLLECTION_NAME,
                "var": False,
                "belge_sayisi": 0,
                "uyarilar": ["Koleksiyon yok — vektörleme pipeline'ınızı çalıştırın."],
            }

        sayi = client.get_collection(COLLECTION_NAME).points_count or 0
        uyarilar = []

        if sayi == 0:
            uyarilar.append("Koleksiyon boş — vektörleme pipeline'ınızı çalıştırın.")
        else:
            noktalar, _ = client.scroll(
                collection_name=COLLECTION_NAME, limit=1,
                with_payload=True, with_vectors=False,
            )
            if noktalar:
                p = noktalar[0].payload or {}
                if "belge" not in p:
                    uyarilar.append(
                        "payload'da 'belge' alanı YOK -> arama sonuçları boş içerik döner. "
                        "Yazarken content_payload_key='belge' kullanın."
                    )
                if not p.get("banka_kodu"):
                    uyarilar.append(
                        "payload'da 'banka_kodu' YOK -> bankaya göre filtreli arama hiç eşleşmez. "
                        "chatbot.intent.banka_bul() ile üretip payload'a ekleyin."
                    )

        return {
            "koleksiyon": COLLECTION_NAME,
            "var": True,
            "belge_sayisi": sayi,
            "uyarilar": uyarilar,
        }
    except Exception as e:
        return {"koleksiyon": COLLECTION_NAME, "hata": str(e)}


if __name__ == "__main__":
    # Elle vektörleme: python -m chatbot.indexing
    # (Pipeline bunu pipeline.py ADIM 4 üzerinden onaysız çağırır.)
    import asyncio as _asyncio

    print("⚠️ Bu, Qdrant koleksiyonunu SIFIRDAN kurar ve mevcut vektörleri SİLER.")
    if input("Devam edilsin mi? (evet/hayır): ").strip().lower() not in ("evet", "e", "yes", "y"):
        raise SystemExit("İptal edildi.")
    _asyncio.run(auto_init_qdrant())