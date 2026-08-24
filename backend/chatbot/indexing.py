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

from chatbot.intent import banka_bul, banka_adi_getir, banka_kodu_coz

# 🚀 Qdrant artık yarışma sunucusunda (url + port=443 + prefix=<takım> + api_key)
from evren_client import qdrant_ayarlari, embed_batch as evren_embed_batch
QDRANT_URL = os.getenv("QDRANT_HOST", "http://qdrant:6333")  # (yalnız geriye dönük)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")
COLLECTION_NAME = "banka_kampanyalari"


def _kampanya_belgesi_olustur(k: dict) -> Document:
    """Tek bir MongoDB kampanya kaydını, vektörlenecek LangChain Document'ine çevirir.

    🛠️ ŞEMA GÜNCELLEMESİ (pipeline.py'nin yazdığı islenmis_kampanyalar için):
    MongoDB Compass'ta doğrulandı — bu koleksiyonda `banka_kodu` ÜST SEVİYEDE,
    hazır ve indeksli bir alan (banka_kodu_1 index'i var); pipeline bunu zaten
    kendisi hesaplayıp yazıyor. Önceki kod bunu her zaman `banka_bul(banka_adi)`
    ile TAHMİN etmeye çalışıyordu — ama bu koleksiyonda banka adı düz
    "banka_adi"/"banka" alanında değil (muhtemelen genel_bilgi alt-belgesinde),
    yani `banka` değişkeni hep "Bilinmeyen Banka"ya düşüyor ve `banka_bul()`
    hiçbir zaman gerçek bir kod üretemiyordu. Sonuç: 344 kayıtlık GERÇEK veri
    vektörlendikten SONRA BİLE `/health` "banka_kodu YOK" uyarısı vermeye devam
    etti — bankaya göre filtreli arama hâlâ hiç eşleşmiyordu. Artık üst
    seviyedeki hazır `banka_kodu` alanı ÖNCELİKLİ kullanılıyor; sadece o alan
    yoksa (eski smartdata.processed_campaigns / finagent.kampanyalar
    kaynaklarında olduğu gibi) `banka_bul()` tahminine düşülüyor. Aynı şekilde
    üst seviyedeki hazır `kampanya_turu` ve `hedef_kitle` alanları da (ikisi de
    Compass'ta indeksli görüldü) içerik ve metadata'ya eklendi.

    ⚠️ HENÜZ YAPILMADI: `genel_bilgi` / `finansman_detay` / `mgm_detay` /
    `promosyon_detay` alt-belgelerinin TAM içeriği doğrulanmadı (Compass'ta
    sadece şema/tip görünümü paylaşıldı, örnek doküman değil) — bu yüzden
    kampanya adı, kâr payı, vade, ödül gibi alanlar hâlâ ESKİ düz alan
    adlarıyla (`kampanya_adi`, `kar_payi`, `vade`, `odul_tl` vb.) okunmaya
    çalışılıyor ve bu koleksiyonda bulunamadıkları için 0 / "Kampanya" gibi
    varsayılanlara düşüyorlar. Bir örnek doküman paylaşılınca bu kısım da
    doğru alt-belge yollarına (ör. `k["finansman_detay"]["kar_payi_orani"]`)
    bağlanacak — yanlış yol tahmin edip sessizce hatalı veri üretmemek için
    şimdilik BİLEREK eklenmedi.
    """
    # 🛠️ HATA DÜZELTMESİ (gerçek veriyle doğrulandı — mongo_kontrol.py):
    # Üst seviye `banka_kodu` bu koleksiyonda 344 kaydın HİÇBİRİNDE yok; kod
    # `genel_bilgi.banka_id` içinde ("kuveytturk", "albaraka", ...). Eski kod
    # bu yüzden HER kayıtta banka'yı "Bilinmeyen Banka" olarak yazıyordu —
    # sohbette "Kaynak" bölümünde aynen böyle görünüyordu — ve payload'daki
    # banka_kodu None kalıyordu, yani /health uyarısı ve "bankaya göre filtreli
    # vektör araması hiç eşleşmiyor" sorunu tam olarak buradan geliyordu.
    ust_banka_kodu = banka_kodu_coz(k)

    # 🛠️ ŞEMA GÜNCELLEMESİ #2 (Compass'ta bu kez ŞEMA AĞACI paylaşıldı, ham
    # doküman değil — bu yüzden yollar aşağıda AĞAÇTA GÖRÜNEN gerçek alan
    # adlarına dayanıyor, ama tam iç içelik %100 doğrulanmadı):
    #   genel_bilgi.kampanya_adi        -> kampanya adı
    #   finansman_detay.kar_payi_orani  -> kâr payı oranı
    #   finansman_detay.vade_ay VEYA finansman_detay.taksit.vade_ay -> vade
    #     (ağaçta "taksit" alt satırı "vade_ay"nın hemen üstünde duruyordu;
    #      iki olası derinlik de deneniyor, hangisi doluysa o kullanılıyor)
    #   promosyon_detay.odul_tutari / odul_metni -> ödül
    #   genel_bilgi.metin                -> kampanyanın ham açıklama metni
    # Bu koleksiyonda İNSAN OKUNABİLİR banka adı (ör. "Kuveyt Türk") için ayrı
    # bir alan YOK — sadece genel_bilgi.banka_id (muhtemelen smartdata.bankalar
    # koleksiyonuna referans) ve üst seviye banka_kodu var. O join henüz
    # kurulmadı; şimdilik banka adı olarak banka_kodu'nu (veya eski
    # kaynaklardaki banka_adi/banka alanını) kullanıyoruz.
    genel_bilgi = k.get("genel_bilgi") or {}
    finansman_detay = k.get("finansman_detay") or {}
    promosyon_detay = k.get("promosyon_detay") or {}

    # 🛠️ HATA DÜZELTMESİ: Bu zincir, banka_adi/banka alanları bu koleksiyonda
    # BULUNMADIĞI için neredeyse her kayıtta ya ham koda ya da doğrudan
    # "Bilinmeyen Banka"ya düşüyordu — ve bu metin Qdrant'a yazılan belgenin
    # İÇERİĞİNE ("Banka: Bilinmeyen Banka") gömüldüğü için, sohbette "Kaynak"
    # bölümünde kullanıcıya AYNEN böyle görünüyordu (bildirilen sorun tam
    # olarak buydu). Artık ortak chatbot.intent.banka_adi_getir() kullanılıyor:
    # üst seviyedeki banka_kodu'ndan düzgün görünen ad üretiliyor.
    ham_banka = k.get("banka_adi") or k.get("banka")
    if isinstance(ham_banka, dict):
        ham_banka = ham_banka.get("kisa_ad")
    banka = banka_adi_getir(ust_banka_kodu, ham_banka)

    kampanya_adi = (
        genel_bilgi.get("kampanya_adi")
        or k.get("kampanya_adi")
        or k.get("baslik")
        or "Kampanya"
    )
    kar_payi = finansman_detay.get("kar_payi_orani")
    if kar_payi is None:
        kar_payi = k.get("kar_payi", k.get("kar_payi_orani", 0))
    # 🛠️ `finansman_detay.taksit` bir ALT BELGE DEĞİL, düz bir sayı (ör. 9.0).
    # Eski kod dict varsayıp atlıyordu; 110 kayıttaki taksit bilgisi boşa
    # gidiyordu (bkz. generate_response.py'deki aynı düzeltme).
    taksit_ham = finansman_detay.get("taksit")
    vade = (taksit_ham or {}).get("vade_ay") if isinstance(taksit_ham, dict) else None
    if vade is None:
        vade = finansman_detay.get("vade_ay")
    if vade is None and isinstance(taksit_ham, (int, float)):
        vade = taksit_ham
    if vade is None:
        vade = k.get("vade", k.get("vade_ay", 0))
    odul = promosyon_detay.get("odul_tutari")
    if odul is None:
        odul = k.get("odul_tl", k.get("odul_miktari", 0))
    odul_metni = promosyon_detay.get("odul_metni")

    kampanya_turu = k.get("kampanya_turu") or genel_bilgi.get("kampanya_turu") or ""
    # 🛠️ hedef_kitle bazı kayıtlarda LİSTE (['tum_musteriler']), bazılarında düz
    # metin ("segment") olarak geliyor. Liste hâli str()'e verilince belgeye
    # "['tum_musteriler']" diye köşeli parantezli, çirkin ve arama için işe
    # yaramaz bir metin gömülüyordu.
    hedef_kitle = k.get("hedef_kitle") or genel_bilgi.get("hedef_kitle") or ""
    if isinstance(hedef_kitle, (list, tuple)):
        hedef_kitle = ", ".join(str(x).replace("_", " ") for x in hedef_kitle)
    aciklama = genel_bilgi.get("metin") or k.get("ham_metin")

    icerik = (
        f"Banka: {banka}\n"
        f"Kampanya: {kampanya_adi}\n"
        f"Kâr Payı/Faiz Oranı: %{kar_payi}\n"
        f"Maksimum Vade: {vade} Ay\n"
        f"Ödül Miktarı: {odul} TL"
    )
    if odul_metni:
        icerik += f"\nÖdül Açıklaması: {odul_metni}"
    if kampanya_turu:
        icerik += f"\nKampanya Türü: {kampanya_turu}"
    if hedef_kitle:
        icerik += f"\nHedef Kitle: {hedef_kitle}"
    if k.get("kosullar"):
        icerik += f"\nKoşullar: {k.get('kosullar')}"
    if aciklama:
        icerik += f"\nDetay: {aciklama}"

    metadata = {
        "kampanya_id": str(k.get("_id", "")),
        # 🧭 Vektör aramada banka filtresi bu alana bakar (bkz. modül başındaki
        # not). Üst seviyedeki hazır banka_kodu ÖNCELİKLİ; yoksa tahmine düş.
        "banka_kodu": ust_banka_kodu or banka_bul(str(banka)),  # (artık banka_kodu_coz sayesinde neredeyse hep dolu)
        "banka_adi": str(banka),
    }
    if kampanya_turu:
        metadata["kampanya_turu"] = str(kampanya_turu)
    if hedef_kitle:
        metadata["hedef_kitle"] = str(hedef_kitle)

    return Document(page_content=icerik, metadata=metadata)


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

    class _PipelineEmbedder(Embeddings):
        def embed_documents(self, texts):
            # 🚀 bge-m3-embed (1024 boyut) — yarışma API'si
            return evren_embed_batch(texts, normalize=False, ilerleme=True).tolist()

        def embed_query(self, text):
            sonuc = self.embed_documents([text])
            return sonuc[0] if sonuc else []

    return _PipelineEmbedder()


def _koleksiyonu_bul(client, koleksiyon_adi: str):
    """Verilen adla eşleşen koleksiyonu, hangi veritabanında olduğuna
    BAKMAKSIZIN bulur (mongo_durum.py'nin veritabanı keşfiyle aynı yaklaşım).

    Veritabanı adı burada sabit kodlanmıyor çünkü pipeline.py'nin (ADIM 1-3,
    backend.nlp.extraction.extractor) hangi veritabanı adını kullandığı bu
    dosyadan bilinmiyor — sadece koleksiyon adına bakılıyor, böylece
    veritabanı adı beklenenden farklı olsa bile bulunabilir.
    """
    for db_adi in client.list_database_names():
        if db_adi in ("admin", "local", "config"):
            continue
        try:
            if koleksiyon_adi in client[db_adi].list_collection_names():
                return client[db_adi][koleksiyon_adi], db_adi
        except Exception:
            continue
    return None, None


def _kampanyalari_oku() -> tuple[list, str]:
    """MongoDB'den kampanyaları okur.

    🛠️ Öncelik sırası GÜNCELLENDİ. pipeline.py (ADIM 1-3) gerçek kampanyaları
    artık 'islenmis_kampanyalar' koleksiyonuna yazıyor (kanıt: gerçek bir
    pipeline çalıştırmasında 344 kampanya buraya kaydedildi) — bu yüzden ARTIK
    ÖNCE bu koleksiyon aranıyor. Eski sıralama (smartdata.processed_campaigns ->
    finagent.kampanyalar) pipeline'ın gerçek çıktısını hiç kontrol etmiyordu;
    bu yüzden ADIM 4 hep 0 kayıt buluyordu (ya da yanlışlıkla
    finagent.kampanyalar'daki 32 adetlik SAHTE DEMO havuzunu vektörlüyordu).
    Eski iki koleksiyon, farklı bir kaynaktan veri gelmiş olma ihtimaline karşı
    yedek olarak KORUNDU.

    (kayitlar, kaynak_adi) döner — kaynak adı loglanıyor ki hangi koleksiyondan
    vektörlendiği görünsün.

    ⚠️ NOT (henüz yapılmadı): pipeline üç ayrı koleksiyon üretiyor
    (islenmis_kampanyalar, urun, cıkarılan_alanlar) — muhtemelen kampanya /
    finansman ürünü / alan-kanıtı olarak normalize edilmiş bir şema. Bu
    fonksiyon şimdilik sadece islenmis_kampanyalar'ı okuyor; 'urun' (finansman
    koşulları, oran/vade gibi alanlar muhtemelen BURADA) ve 'cıkarılan_alanlar'
    (kanıt/kaynak metni) ile zenginleştirme EKLENMEDİ — koleksiyonlar arası
    ilişkiyi (hangi alan hangi anahtarla birbirine bağlanıyor) doğrulamadan
    birleştirmek, yanlış varsayımla sessizce hatalı belge üretebilirdi
    (tıpkı bu projede daha önce yaşanan banka_kodu/koleksiyon karışıklıkları
    gibi). Üç koleksiyondan birer örnek doküman paylaşılırsa doğru şekilde
    bağlanabilir.
    """
    from pymongo import MongoClient

    client = MongoClient(MONGO_URI)
    try:
        koleksiyon, db_adi = _koleksiyonu_bul(client, "islenmis_kampanyalar")
        if koleksiyon is not None:
            kampanyalar = list(koleksiyon.find({}))
            if kampanyalar:
                return kampanyalar, f"{db_adi}.islenmis_kampanyalar"

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
        _q = qdrant_ayarlari()
        QdrantVectorStore.from_documents(
            docs,
            embeddings,
            collection_name=COLLECTION_NAME,
            content_payload_key="belge",
            force_recreate=True,
            **{k: v for k, v in _q.items() if k in ("url", "port", "prefix", "api_key", "timeout")},
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
        client = QdrantClient(**qdrant_ayarlari())
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