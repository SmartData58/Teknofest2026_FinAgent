import json
import os
import sys
from typing import List
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from backend.test.embedding_client import embed_batch

# --- 1. ÖZEL QWEN EMBEDDER (LangChain Uyumluluğu) ---
# 🛠️ Bu üçüncü (chatbot/generate_response.py ve rag/embedder.py'den sonra) neredeyse
# birebir aynı embedder kopyasıydı; artık gerçek HTTP çağrısı için PAYLAŞILAN
# embedding_client.embed_batch()'i kullanıyor (bkz. embedding_client.py).
class OzelQwenEmbedder(Embeddings):
    def __init__(self, api_url: str = None):
        self.api_url = api_url

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            matris = embed_batch(texts, normalize=False, url=self.api_url)
            return matris.tolist()
        except Exception as e:
            print(f"Embedding API Hatası: {e}")
            return []

    def embed_query(self, text: str) -> List[float]:
        # 🛠️ HATA DÜZELTMESİ: embed_documents hata durumunda [] döner (bkz. yukarısı).
        # Önceki kod doğrudan [][0] yapıyordu -> her embedding hatasında IndexError
        # ile ÇÖKÜYORDU (Qdrant/embedding servisi geçici olarak erişilemez olduğunda
        # bütün ingest işlemi kontrolsüzce patlıyordu). Artık boş sorgu vektörü
        # (sıfır vektör değil, boş liste) dönüyor; çağıran taraf (LangChain) bunu
        # tutarlı şekilde ele alabiliyor ve hata loglanmış oluyor.
        sonuc = self.embed_documents([text])
        return sonuc[0] if sonuc else []

# --- 2. PYDANTIC ŞEMASI (Kategori Çıkarımı İçin NER) ---
class KampanyaKategorisi(BaseModel):
    kategori: str = Field(
        description="Kampanyanın ait olduğu ana kategori. "
                    "Örnekler: 'Seyahat', 'Giyim', 'E-Ticaret', 'Eğitim', 'Sağlık', 'Finansal', 'Eğlence', 'Diğer'"
    )

# --- 3. OLLAMA, EMBEDDER VE QDRANT BAĞLANTILARI ---
# 🛠️ Diğer servislerle (chatbot/agents.py, chatbot/generate_response.py) tutarlı
# olması ve tek bir docker-compose ağ adına bağımlı kalmaması için ortam
# değişkenlerinden okunuyor; env tanımlı değilse önceki sabit değerler varsayılan.
OLLAMA_BASE_URL = os.getenv("LANGCHAIN_OLLAMA_BASE_URL", "http://smartdata-llm-1:11434")
llm = ChatOllama(model="qwen3.5:4b", temperature=0.0, base_url=OLLAMA_BASE_URL)
structured_llm = llm.with_structured_output(KampanyaKategorisi)

# Embedding servisine bağlantı
EMBEDDING_API_URL = os.getenv("EMBEDDING_URL", "http://embedding:8001/api/embed")
embeddings = OzelQwenEmbedder(api_url=EMBEDDING_API_URL)

# Qdrant İstemcisi bağlantısı (Docker Compose üzerindeki 6333 portundan ulaşır)
QDRANT_URL = os.getenv("QDRANT_HOST", "http://qdrant:6333")
qdrant_client = QdrantClient(url=QDRANT_URL)
collection_name = "banka_kampanyalari"

# Qwen3-Embedding-0.6B için vektör boyutu genellikle 896 veya 1536'dır.
# Eğer API'niz farklı bir boyutta matris döndürürse bu değeri Qdrant hata vermemesi için değiştirin.
VECTOR_SIZE = 1024

# Koleksiyon yoksa yarat
if not qdrant_client.collection_exists(collection_name):
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

# 🛠️ HATA DÜZELTMESİ: content_payload_key belirtilmediği için LangChain varsayılanı
# ("page_content") kullanılıyordu. Ama bu koleksiyona yazan/okuyan diğer tüm kod
# (chatbot/chatbot.py'deki auto_init_qdrant, chatbot/generate_response.py'deki
# get_vector_store) her yerde content_payload_key="belge" kullanıyor. Bu script
# çalıştırılırsa yazdığı belgeler "page_content" altında saklanıyor, chat tarafı
# ise "belge" alanını arıyor — sonuç: bu script'in eklediği kayıtlar arama
# sırasında BOŞ İÇERİK olarak dönüyor (ya da hiç bulunamıyor). Artık aynı anahtar
# kullanılıyor ki AYNI koleksiyona yazan tüm yollar tutarlı olsun.
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=collection_name,
    embedding=embeddings,
    content_payload_key="belge",
)

# --- 4. ANA VERİ İŞLEME VE AKTARIM FONKSİYONU ---
def process_and_ingest(json_path: str):
    print(f"📄 Dosya işleniyor: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    kampanyalar = data.get("kampanyalar", [])
    documents_to_insert = []

    for i, kampanya in enumerate(kampanyalar):
        mevcut_kategori = kampanya.get("kategori")

        # Kategori yoksa veya verimsiz ("kendim_icin" gibi) ise LLM ile doldur
        if not mevcut_kategori or mevcut_kategori == "kendim_icin":
            print(f"🤖 LLM Analiz Ediyor ({i+1}/{len(kampanyalar)}): {kampanya.get('baslik', '')}")

            prompt = f"Şu kampanya metnini analiz et ve kategorisini belirle:\nBaşlık: {kampanya.get('baslik', '')}\nDetay: {kampanya.get('ham_metin', '')}"

            try:
                sonuc = structured_llm.invoke(prompt)
                kampanya["kategori"] = sonuc.kategori
                print(f"   ↳ Atanan Kategori: {sonuc.kategori}")
            except Exception as e:
                print(f"   ↳ LLM Hatası: {e}")
                kampanya["kategori"] = "Belirsiz"

        # Qdrant'ta metadata üzerinden keskin aramalar (filtreler) yapabilmek için veri setini hazırla
        metadata = {
            "banka": kampanya.get("banka", "Bilinmiyor"),
            "baslik": kampanya.get("baslik", ""),
            "url": kampanya.get("url", ""),
            "kategori": kampanya["kategori"],
            "tarih_metni": kampanya.get("tarih_metni", "")
        }

        # LangChain objesi olarak paketle
        doc = Document(
            page_content=kampanya.get("ham_metin", ""),
            metadata=metadata
        )
        documents_to_insert.append(doc)

    # Tüm verileri vektörleştir (Embedding) ve Qdrant'a yaz
    if documents_to_insert:
        print(f"💾 Qdrant'a {len(documents_to_insert)} adet kampanya yazılıyor...")
        vector_store.add_documents(documents_to_insert)
        print("✅ İşlem tamamlandı!")

if __name__ == "__main__":
    import glob

    # 🛡️ KAZARA ÇALIŞTIRMA KORUMASI: Proje MongoDB'ye taşındıktan sonra canlı
    # sistem chatbot.py'deki auto_init_qdrant() — o da AYNI Qdrant koleksiyonuna
    # ("banka_kampanyalari") yazıyor. Bu script disk üzerindeki JSON dosyalarından
    # okuyup vector_store.add_documents() ile aynı koleksiyona EKLEME yapıyor
    # (silmiyor, ama farklı bir şema/kaynaktan gelen kayıtları karıştırıyor).
    # Kazara/otomatik bir CI adımında tetiklenmesini önlemek için açık onay istiyoruz.
    if os.environ.get("FINAGENT_ALLOW_LEGACY_JSON_INGEST") != "1":
        raise SystemExit(
            "🚫 Bu script (JSON dosyalarından eski/tek seferlik RAG yükleyicisi) "
            "chatbot.py'nin MongoDB tabanlı auto_init_qdrant() ile AYNI Qdrant "
            "koleksiyonuna ('banka_kampanyalari') yazıyor. Proje MongoDB'ye "
            "taşındığı için bu muhtemelen artık kullanılmıyor; kazara "
            "çalıştırılması canlı verilerle karışabilir.\n"
            "Bilerek ve isteyerek çalıştırmak istiyorsanız:\n"
            "  FINAGENT_ALLOW_LEGACY_JSON_INGEST=1 python rag_ingest.py [dosya_yolu]"
        )

    # Script /app/rag dizininde çalıştığı için bir üst dizine çıkıp data/raw klasörünü gösteriyoruz
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    raw_klasoru = os.path.join(BASE_DIR, "..", "data", "raw")

    # raw klasörünün altındaki tüm klasörlerdeki .json dosyalarını bulur
    arama_deseni = os.path.join(raw_klasoru, "*", "*.json")
    json_dosyalari = glob.glob(arama_deseni)

    if not json_dosyalari:
        print(f"HATA: {raw_klasoru} konumunda hiç JSON dosyası bulunamadı! Lütfen dizini kontrol edin.")
    else:
        print(f"🔍 Toplam {len(json_dosyalari)} adet banka veri dosyası bulundu. Vektörleştirme başlatılıyor...\n")

        # Bulunan tüm dosyaları sırayla RAG boru hattına gönder
        for dosya_yolu in json_dosyalari:
            process_and_ingest(dosya_yolu)
            print("-" * 50)

        print("🎉 TÜM BANKALAR BAŞARIYLA QDRANT'A AKTARILDI!")

    # 🛠️ HATA DÜZELTMESİ: Burada önceden, yukarıdaki glob döngüsü TÜM dosyaları
    # (vakif_katilim'inki dahil) zaten işledikten SONRA, hep aynı sabit dosya
    # (vakif_katilim/20260803_100745.json) KOŞULSUZ olarak bir kez daha
    # process_and_ingest() ile işleniyordu. Bu, script her çalıştırıldığında o
    # bankanın kampanyalarını Qdrant'a YİNELENEN (duplicate) kayıtlar olarak
    # ikinci kez ekliyordu — muhtemelen geliştirme sırasında unutulmuş bir test/
    # debug satırıydı. Artık bu koşulsuz ikinci çalıştırma kaldırıldı; tek bir
    # dosyayı özellikle yeniden işlemek isteyen biri script'i
    # `python rag_ingest.py data/raw/vakif_katilim/20260803_100745.json` gibi bir
    # komut satırı argümanıyla çağırabilir.
    if len(sys.argv) > 1:
        hedef_dosya = sys.argv[1]
        if os.path.exists(hedef_dosya):
            process_and_ingest(hedef_dosya)
        else:
            print(f"HATA: JSON dosyası ({hedef_dosya}) bulunamadı!")