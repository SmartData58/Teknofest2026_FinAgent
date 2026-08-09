import json
import os
import requests
from typing import List
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# --- 1. ÖZEL QWEN EMBEDDER (LangChain Uyumluluğu) ---
class OzelQwenEmbedder(Embeddings):
    def __init__(self, api_url: str):
        self.api_url = api_url

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            # Embedding API'niz EmbedRequest modeline göre "input" anahtarını bekliyor
            response = requests.post(self.api_url, json={"input": texts})
            response.raise_for_status()
            
            # API'den dönen {"embeddings": [...]} yanıtını ayıkla
            return response.json().get("embeddings", [])
        except Exception as e:
            print(f"Embedding API Hatası: {e}")
            return []

    def embed_query(self, text: str) -> List[float]:
        # Tekil arama işlemleri için listenin ilk elemanını döndür
        return self.embed_documents([text])[0]

# --- 2. PYDANTIC ŞEMASI (Kategori Çıkarımı İçin NER) ---
class KampanyaKategorisi(BaseModel):
    kategori: str = Field(
        description="Kampanyanın ait olduğu ana kategori. "
                    "Örnekler: 'Seyahat', 'Giyim', 'E-Ticaret', 'Eğitim', 'Sağlık', 'Finansal', 'Eğlence', 'Diğer'"
    )

# --- 3. OLLAMA, EMBEDDER VE QDRANT BAĞLANTILARI ---
# Kategorileri otomatik etiketlemesi için Ollama bağlantısı (Sıcaklık 0)
llm = ChatOllama(model="qwen3.5:4b", temperature=0.0, base_url="http://smartdata-llm-1:11434")
structured_llm = llm.with_structured_output(KampanyaKategorisi)

# Embedding servisine bağlantı
# DİKKAT: "embedding" olan kısmı docker-compose'daki kendi embedding servis isminle,
# 8000 olan kısmı ise o servisin içeride açık olan portuyla değiştirmelisin.
EMBEDDING_API_URL = "http://embedding:8001/api/embed"
embeddings = OzelQwenEmbedder(api_url=EMBEDDING_API_URL)

# Qdrant İstemcisi bağlantısı (Docker Compose üzerindeki 6333 portundan ulaşır)
qdrant_client = QdrantClient(url="http://qdrant:6333")
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

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=collection_name,
    embedding=embeddings,
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
    # raw dizini altındaki tüm klasörleri tarayıp dinamik yapabilirsiniz
    # Şimdilik örnek JSON dosyasını hedef alıyoruz:
    hedef_dosya = os.path.join("data", "raw", "vakif_katilim", "20260803_100745.json")
    
    if os.path.exists(hedef_dosya):
        process_and_ingest(hedef_dosya)
    else:
        print(f"HATA: JSON dosyası ({hedef_dosya}) bulunamadı!")