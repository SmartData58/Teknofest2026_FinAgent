# 🏦 SmartData BiQuery (Teknofest 2026 FinAgent)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![NuxtJS](https://img.shields.io/badge/Nuxt-00DC82?style=for-the-badge&logo=nuxtdotjs&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-DC2626?style=for-the-badge&logo=qdrant&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**Katılım Bankacılığı için NLP, RAG ve Hibrit Çıkarım Destekli Finansal Veri Analiz Platformu**

</div>

---

## 📌 Proje Hakkında

**SmartData BiQuery**, Türkiye'deki katılım bankalarının kampanya, ürün ve finansman bilgilerini otomatik olarak toplayan, NLP (Doğal Dil İşleme) ve bilgi çıkarım (information extraction) yöntemleriyle anlamlandıran, yapılandırılmış veriye dönüştüren ve kullanıcılara RAG (Retrieval-Augmented Generation) tabanlı bir chatbot ve gösterge panelleri (dashboard) üzerinden sunan uçtan uca bir finansal analiz platformudur. **Teknofest 2026 FinAgent** yarışması gereksinimlerine göre özel olarak entegre edilip optimize edilmiştir.

Bankaların heterojen (farklı yapılardaki) veri formatlarını tek bir standart veri modeline oturtarak, kullanıcıların doğal dilde karmaşık finansal sorular sormasına ve net, görsellerle desteklenmiş (tablo/grafik) analitik cevaplar almasına olanak tanır.

> [!IMPORTANT]
> **Yarışma Entegrasyonu (Evren API):** Proje, yerel (Ollama vb.) LLM, Embedding ve Reranker servislerinden arındırılarak Teknofest yarışma altyapısı olan **Evren API** (`llm-large`, `llm-fast`, `router`, `bge-m3-embed`, `guard`) ile tam entegre hale getirilmiştir.

---

## ✨ Öne Çıkan Özellikler ve Güncellemeler

- 🧠 **Gelişmiş Çok Dilli Niyet Motoru (Intent Engine):** Chatbot, Türkçe sondan eklemeli yapıyı (örn. *listele, listeler misin, listesini*) hatasız yakalayan `\w*` duyarlı ek mantığına ve İngilizce (EN/TR) tam desteğe sahip regex tabanlı bir karar motoru kullanır.
- 🖼️ **Görsel Algılama ve Akıllı Çizim (`gorsel_karari`):** Sistem, "bana kâr payı tablosu çiz" gibi açık görsel istekleri ile "ödül tutarı en yüksek 3 kampanya" gibi veri sorularını ayırır. Açıklayıcı sorularda gereksiz grafik çizilmesini engeller.
- 👁️ **Doğrudan LLM Görsel İşleme (OCR Bypass):** Yüklenen kampanya görselleri yerel OCR adımlarını atlayarak doğrudan Evren API'nin görüntü okuyabilen (vision) çok kipli modeline aktarılır, hız ve isabet oranı artırılır.
- 🛡️ **Prompt Injection Savunması:** Kullanıcı girdilerinde ve yüklenen dokümanlarda "ignore all previous instructions" vb. zararlı yönlendirmeleri tespit eden güvenlik (Guard) katmanı içerir.
- 📊 **Dinamik Veri Filtreleme ve Kıyaslama:** Birden çok bankanın aynı anda karşılaştırılması (örn. *Kuveyt Türk ile Albaraka'yı kıyasla*), kampanya adı ile arama ve MongoDB sorgu altyapısıyla desteklenmektedir.
- 💰 **Finansman Hesabı Kazıyıcıları:** Sadece kampanyaları değil, katılım bankalarının finansman (kredi/kâr payı hesaplama) verilerini toplayan ve hesaplayan modülleri (`scraper/finans_hesap`) barındırır.

---

## 🛠️ Ön Koşullar (Prerequisites)

Projeyi çalıştırmadan önce sisteminizde aşağıdaki yazılımların kurulu olduğundan emin olun:
- **Docker & Docker Compose** (Tüm sistemi izole bir şekilde çalıştırmak için)
- **Python 3.10+** (Test scriptlerini ve yerel araçları çalıştırmak için)
- **Node.js 18+** (Sadece frontend'i Docker harici geliştirmek isterseniz)

---

## 🏗️ Sistem Mimarisi ve 5 Aşamalı Pipeline

Proje 5 ana işlem adımından (pipeline) oluşmaktadır:

```
[1. Seed] ──> [2. Scraper] ──> [3. NLP & Çıkarım] ──> [4. Embedding / Qdrant] ──> [5. Chatbot Backend & Frontend]
```

### 1. Seed Katmanı (`backend/db/seed_banks.py`)
- **İşlev:** 10 Katılım Bankasının (Albaraka, Kuveyt Türk, Türkiye Finans, Ziraat Katılım, Vakıf Katılım, Emlak Katılım, Hayat Finans, Dünya Katılım, Adil Katılım, TOM Katılım) sistem ön tanımlarını veritabanına yükler.

### 2. Kazıyıcı (Scraper) Katmanı (`scraper/`)
- **Teknoloji:** Python (Playwright / BeautifulSoup)
- **İşlev:** 10 Katılım Bankasının web sitelerinden kampanya ve ürün metinlerini otomatik olarak kazır. Ayrıca `scraper/finans_hesap/` modülü ile finansman hesaplama verilerini toplar.
- **Çıktı:** Ham verileri MongoDB'deki `ham_kampanya` koleksiyonlarına yazar.

### 3. Bilgi Çıkarımı (NLP Pipeline) Katmanı (`backend/nlp/`)
- **Teknoloji:** Regex, Normalizasyon (Tarih, Süre, Para, Yüzde), Kural Tabanlı & LLM Extractor, NER.
- **İşlev:** "Kâr payı oranı", "vade sayısı", "ödül miktarı", "son katılma tarihi" gibi parametreleri metinden ayrıştırır ve standart hale getirir.
- **Çıktı:** Yapılandırılmış veriler `smartdata.islenmis_kampanyalar` koleksiyonuna kaydedilir.

### 4. Vektörleştirme (Embedding) ve Reranker Kararı (`backend/chatbot/indexing.py`)
- **Teknoloji:** Evren API (`bge-m3-embed`) ve Qdrant Vector DB
- **İşlev:** İşlenmiş kampanya metinleri anlamsal arama yapılabilmesi için `bge-m3-embed` (bi-encoder) modeli ile Qdrant'a indekslenir.

> [!NOTE]
> **💡 Mimari Karar: Neden Reranker Kullanılmıyor?**
> Sistemimizde varsayılan olarak Reranker kapalı tutulmaktadır. Embedding modeli (BGE) ve Reranker (Qwen vb.) farklı ailelerden olsa dahi teknik bir uyuşmazlık yaratmazlar; zira Reranker (cross-encoder) hiçbir vektör işlemi yapmadan doğrudan ham metin üzerinden alaka skoru üretir.
> Ancak asıl sorun **kalibrasyon ve performans düşüşüdür**. Yapılan ölçümlerde Evren'in kendi rerank modelinin, `bge-m3-embed`'in hâlihazırda **0,95 (tavana yakın)** olan R@1 (ilk sıradaki isabet) başarısını **0,55'e düşürdüğü** görülmüştür. Katılım bankacılığına özgü, kısa ve Türkçe metinlerde genel amaçlı bir Reranker'ın kalibrasyonu ana arama motorundan daha zayıf kalabilmekte; kazandıracağı marj çok küçükken isabeti bozma riski büyük olmaktadır.

### 5. RAG Tabanlı Chatbot Backend & Frontend
- **Backend:** FastAPI, LangChain, Evren LLM, Redis Önbellek. Soru Niyet Motoru tarafından analiz edilir; Mongo ve Qdrant'tan çekilen veriler Evren LLM'e iletilerek yanıt üretilir.
- **Frontend:** Nuxt 3, Vue 3, Tailwind CSS, Pinia. Chat, Dashboard, Kampanyalar, Karşılaştırma ve Finansman sayfalarını sunar.

---

## 📁 Proje Klasör Yapısı

```
Teknofest2026_FinAgent/
├── backend/                  # FastAPI Backend Servisi ve Chatbot Mantığı
│   ├── api/                  # REST Uç Noktaları (campaing.py vb.)
│   ├── chatbot/              # RAG Motoru, Niyet Analizi, Evren Client, Önbellek
│   │   ├── agents.py         # Supervisor ve Görsel Ajanlar
│   │   ├── evren_client.py   # Evren API İstemcisi
│   │   ├── generate_response.py # RAG ve Yanıt Üretim Motoru
│   │   ├── indexing.py       # Qdrant Vektör İndeksleme
│   │   ├── intent.py         # Çok Dilli Regex Niyet Motoru
│   │   └── redis_cache.py    # Redis Önbellek Yönetimi
│   ├── configs/              # Banka Yapılandırmaları (banks.yaml)
│   ├── db/                   # MongoDB Bağlantı ve Seed İşlemleri
│   ├── document_processor/   # Doküman ve Görsel Ayrıştırma (PDF, Word, Excel, Image)
│   ├── nlp/                  # NLP Temizleme, Normalizasyon ve Bilgi Çıkarımı
│   └── test/                 # 19+ Teşhis ve Test Scripti
├── frontend/                 # Nuxt 3 / Vue 3 Kullanıcı Arayüzü
│   ├── app/
│   │   ├── pages/            # chat.vue, dashboard.vue, campaigns.vue, comparison.vue, finansman.vue
│   │   ├── components/       # UI Bileşenleri (ChatPrompt, Loaders vb.)
│   │   └── stores/           # Pinia Chat Store
│   └── i18n/locales/         # Türkçe (tr.json) ve İngilizce (en.json) Diller
├── scraper/                  # Banka Kazıma Örümcekleri ve Finansman Hesaplayıcılar
│   ├── spiders/              # 10 Katılım Bankası Kazıyıcısı
│   └── finans_hesap/         # Katılım Bankası Finansman Hesaplama Kazıyıcıları
├── docker-compose.yml        # Temel Docker Compose Dosyası
├── docker-compose.prod.yml   # Prodüksiyon Yapılandırma Override
├── docker-compose.nvidia.yml # NVIDIA GPU Yapılandırma Override (Hızlı OCR)
├── example.env               # Örnek Çevre Değişkenleri Şablonu
├── pipeline.py               # Uçtan Uca 5 Aşamalı İşlem Hattı Tetikleyici
└── LICENSE                   # Apache License 2.0
```

---

## 🏢 Şirket İçi Uyumluluk ve Dışa Bağımlılıklar

Proje, özellikle bankacılık gibi regülasyonların sıkı olduğu sektörlerdeki "veri gizliliği" ve "kurumsal ağ uyumluluğu" gözetilerek tasarlanmıştır.

### Şirket İçi Uyumluluk (Corporate Compliance)
- **Mikroservis Mimarisi:** Sistem (Frontend, Backend, Scraper, DB) tamamen konteynerize (Docker) edilmiştir. Bir bankanın mevcut şirket içi (on-premise) Kubernetes, OpenShift veya CI/CD boru hatlarına (pipeline) doğrudan entegre edilebilir.
- **Veri Gizliliği (Data Privacy):** Müşteri ve sohbet verileri dışarıdaki ticari / açık uçlu LLM sağlayıcılarına (Örn. OpenAI, Anthropic) gönderilmez. Proje tam izole veya kurum tarafından sağlanan özel modellere (şu an için Teknofest **Evren API** altyapısına) entegre çalışır.
- **Kurumsal Kullanıcı Modu (Analist Görünümü):** Chatbot'un şirket içi banka personeline özel bir görünüm seçeneği vardır. Analistler sistemi *"Rakiplerin taşıt kredisiyle bizimkini kıyasla"* gibi doğrudan rakip analizine yönelik banka-içi senaryolarla kullanabilirler.

### Dışa Bağımlılıklar (External Dependencies)
Sistemin ihtiyaç duyduğu temel ağ ve yazılım bağımlılıkları şunlardır:
1. **Evren API (Teknofest):** Projenin Doğal Dil İşleme (LLM), Vektörleştirme (`bge-m3-embed`) ve Güvenlik (Guard) işlemleri için internet üzerinden HTTPS (443) ile erişilen dış bağımlılığıdır. 
2. **Evren Qdrant (Cloud DB):** Vektör aramaları, Evren API ekibi tarafından sağlanan bulut Qdrant sunucusuna bağımlıdır (Çökme durumunda `yerel-vektor` profili ile bu bağımlılık ortadan kaldırılabilir).
3. **Playwright / Chromium:** Kazıyıcı (Scraper) modülü, banka sitelerini render edebilmek için Chromium tarayıcısına ihtiyaç duyar (Bu bağımlılık Docker imajı içinde paketlenmiş olarak gelir).
4. **PyTorch & CUDA (Opsiyonel):** Eğer sisteme belge yüklenecekse OCR ayrıştırmaları için yerel (host) donanımda GPU/Nvidia sürücülerine bağımlılık duyar. Aksi takdirde CPU'ya düşerek daha yavaş çalışır.
5. **Paket Yöneticileri:** Python tarafında `pip` (requirements.txt), Node.js tarafında `npm` (package.json) repolarına bağımlılık bulunmaktadır.

---

## 📚 API Dokümantasyonu (Swagger UI)

Backend servisi ayağa kalktıktan sonra, FastAPI tarafından otomatik olarak oluşturulan API dokümantasyonuna şu adresten ulaşabilirsiniz:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

Buradan `/api/chat` (Sohbet), `/api/kaziyiciyi-baslat` (Manuel scraping tetikleme) ve `/admin/reindex` (Vektörleri sıfırlama) endpoint'lerini doğrudan test edebilirsiniz.

---

## ⚙️ Konfigürasyon ve `.env` Rehberi

Proje dizinindeki `example.env` şablonunu kopyalayarak başlayın:
```bash
cp example.env .env
```

Projedeki tüm ayarlar bu tek `.env` dosyası üzerinden yönetilir:

#### 🟢 Evren API (Yarışma LLM) Ayarları
- **`EVREN_API_KEY`**: Yarışma LLM servisi için takımınıza özel anahtar (`sk-evren-<TAKIM>-...`).
- **`EVREN_MODEL` / `EVREN_MODEL_HIZLI`**: Kullanıcıya yanıt veren ana model (`llm-large`) ve ajanlar (çoklu-sorgu, özetleme vb.) için kullanılan hızlı model (`llm-fast`).
- **`EVREN_DUSUNME`**: LLM'in muhakeme (thinking) yeteneğini kontrol eder (`acik` veya `kapali`). Kapatılırsa modelin ilk yanıt süresi kısalır.
- **`EVREN_MAX_TOKENS`**: Modelin üretebileceği maksimum yanıt/muhakeme token bütçesi (Varsayılan: `16384`).
- **`EVREN_IPV4`**: Sunucu DNS çözünürlük timeout sorunlarını önlemek için IPv4 zorlaması yapar (`true`).
- **`EVREN_ISITMA_ARALIGI`**: Modelin sunucuda bellekten düşmemesi için arka planda atılan dummy istek aralığı (saniye).

#### 🔵 Vektör Arama (Qdrant) ve Embedding Ayarları
- **`EVREN_EMBED_MODEL`**: Metinleri vektöre çeviren model (`bge-m3-embed`).
- **`EVREN_QDRANT_URL`**: Vektör veritabanı adresi (`https://evren-vektor.ssyz.org.tr`).
- **`EVREN_TEAM`**: Qdrant'ta takımınıza ayrılan isim alanı (prefix).
- **`EVREN_QDRANT_KEY`**: Vektör veritabanı erişim anahtarı.
- **`EVREN_RERANK`**: Qdrant'tan dönen sonuçları bir kez daha sıralamaya sokup sokmayacağını belirler (`true` / `false`).

#### 🗄️ Veritabanı ve Önbellek (MongoDB & Redis)
- **`MONGO_USER` & `MONGO_PASSWORD`**: MongoDB root yetkilendirme bilgileri.
- **`MONGO_URI`**: *Önemli!* Host makineden (script veya testler için) bağlantılarda `localhost:27017` kullanılırken, Docker içinde backend doğrudan `mongodb://...` adresine bağlanır.
- **`STARTUP_CACHE_FLUSH`**: Sistem ayağa kalktığında eski sohbet ve veri önbelleklerini (Redis) temizler (`1` veya `0`). Demo öncesi `0` yapılması yanıtları hızlandırır.

#### 🤖 Ajan (Agent) ve Güvenlik Davranışları
- **`SUPERVISOR_AKTIF`**: Her LLM yanıtını son bir denetim modelinden geçirerek kalite kontrolü yapar (`true` / `false`).
- **`GORSEL_LLM_FALLBACK`**: Niyet Motoru grafik mi tablo mu çizileceğinden emin olamazsa, karar vermesi için hızlı bir LLM ajanına danışır (`true`).
- **`GUARD_AKTIF` / `GUARD_ENGELLE`**: Prompt Injection denemelerini tarar. `GUARD_ENGELLE=false` ise sadece uyarır ve loglar.
- **`ADMIN_TOKEN`**: `/admin/reindex` (Vektörleri sıfırdan oluşturma) REST ucunu korur.

---

## 🚀 Derleme (Build) ve Çalıştırma Komutları

Sistem farklı ortamlar (Geliştirme, Prod, GPU) için farklı Docker konfigürasyon dosyalarına sahiptir:

### 1. Standart Geliştirme (Dev) Ortamı Başlatma
```bash
docker-compose up -d --build
```

### 2. Prodüksiyon (Prod) Ortamında Başlatma
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 3. NVIDIA GPU Destekli Başlatma (Hızlı OCR)
Backend içerisinde belge ayrıştırma (OCR) işlemleri (PDF/DOCX yükleme vb.) yerel olarak çalışır ve `torch` (CUDA) kullanır. OCR hızını maksimize etmek ve backend'e GPU yetkisi vermek için:
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.nvidia.yml up -d --build
```
*GPU'nun tanınıp tanınmadığını test etmek için (Çalışırken):*
```bash
docker-compose exec backend python -c "import torch; print(torch.cuda.is_available())"
```

### 4. Tekil Docker İmajlarını Derleme (Manuel Build)
```bash
# Backend imajını derlemek için:
docker build -t finagent-backend ./backend

# Frontend imajını derlemek için:
docker build -t finagent-frontend ./frontend

# Scraper imajını derlemek için:
docker build -t finagent-scraper ./scraper
```

### 5. Yalnızca Vektör Veritabanı Yedeğini Çalıştırma (Fallback Profil)
```bash
docker-compose --profile yerel-vektor up -d
```

### 6. Veri Kazıma ve İndekslemeyi (Pipeline) Manuel Tetikleme
```bash
# Standart ortamda tüm 10 bankanın verisini çekmek için:
docker-compose exec scraper python pipeline.py --hepsi

# NVIDIA GPU profiliyle sistemi başlattıysanız tüm veriyi çekmek için:
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.nvidia.yml exec scraper python pipeline.py --hepsi

# Sadece belirli bir banka (örn. albaraka) için:
docker-compose exec scraper python pipeline.py albaraka
```

### 7. Servisleri Kapatma
```bash
docker-compose down
```

---

## 🧪 Test Scriptleri ve Kullanım Parametreleri

`backend/test/` dizini altında, projenin her bir katmanını veya sorunlu kısımlarını teşhis edebilmek için yazılmış test araçları yer alır:

### 1. `test_buyuk.py` (Kapsamlı Doğruluk ve Regresyon Testi)
Sistemin büyük bir prompt havuzuna (Örn. `buyuk_sonuc.json`) nasıl yanıt verdiğini (Accuracy, Halüsinasyon, Reranker farkı) ölçer.
*   **Kullanım:** `python backend/test/test_buyuk.py --kat liste,kiyas --kayit deneme1.json --paralel 3`

### 2. `testapi.py` (Canlı API Entegrasyon Testi)
Sistem tam ayaktayken `/api/chat` ve diğer uçları uçtan uca simüle eder.
*   **Kullanım:** `python backend/test/testapi.py --sec 1,4 --detay`

### 3. `test_dayaniklilik.py` (Chaos / Resilience Test)
FastAPI, Redis ve Veritabanı servisleri aniden çökerse sistemin nasıl tepki verdiğini ve kurtulduğunu test eder.
*   **Kullanım:** `python backend/test/test_dayaniklilik.py --onayla --sec qdrant,redis`

### 4. `llm_teshis.py` (LLM Muhakeme ve Token Testi)
Evren LLM'in `thinking` (muhakeme) sürecine giden token bütçesini ve bağlam şişmesini teşhis eder.
*   **Kullanım:** `python backend/test/llm_teshis.py --kampanya 10 --max-tokens 16384`

### 5. `ocr_olcum.py` (Yerel CUDA/GPU Performans Ölçümü)
Belge yükleme sürelerini CPU ve GPU (PyTorch/CUDA) arasında kıyaslar.
*   **Kullanım:** `python backend/test/ocr_olcum.py --dosya test.pdf --sadece-durum`

### Diğer Teşhis Araçları (Parametresiz Çalışırlar)
*   **`testintent.py` / `testgrafik.py`**: Doğal Dil Regex Niyet Motoru'nu (API'ye çıkmadan, 0 ms içinde) test eder.
*   **`gecikme_teshis.py`**: Sunucudaki IPv6/IPv4 DNS resolving timeout'larını analiz eder.
*   **`mongo_kontrol.py`**: MongoDB içindeki verilerin beklenen formatta olup olmadığını raporlar.
*   **`bagimlilik_denetimi.py`**: `.env` ve `requirements.txt` ile kod tabanındaki fiili "import" komutlarının uyumunu denetler.
*   **`test_db.py`**: Veritabanı bağlantısını test edip `islenmis_kampanyalar` koleksiyonundan örnek kayıtları (`banka_id`, `kampanya_turu`) basar.
*   **`test_turu.py`**: MongoDB'deki kampanya verilerini tarayarak sistemde benzersiz (distinct) kaç farklı kampanya türü (`kampanya_turu`) bulunduğunu listeler.

---

## 🤖 Kullanım Senaryoları (Chatbot Örnek Promptları)

- **Filtreleme & Listeleme:** *"Kuveyt Türk ile Albaraka'nın tüm kampanyalarını listeler misin?"*
- **Sıralama:** *"Ödül tutarı en yüksek olan 5 kampanyayı düşükten yükseğe sırala."*
- **Finansman & Kar Payı:** *"Ziraat Katılım taşıt finansmanı kâr payı oranlarını göster."*
- **Görsel Engelleme:** *"Bana tablo veya grafik çizme, sadece metin olarak anlat."*

---

## 📜 Lisans ve Kullanım Koşulları

Bu proje **Apache License 2.0** altında lisanslanmıştır. Kullanım koşullarının tam metni için kök dizindeki `LICENSE` dosyasına göz atabilirsiniz.
*   **Ticari Kullanım:** Açık kaynaklı ve ticari projelere (gerekli atıflar yapılarak) entegre edilebilir.
*   **Sorumluluk Reddi:** Yazılım "olduğu gibi (AS IS)" sunulur, hiçbir garanti içermez.

---

<div align="center">
  <br/>
  <b>Teknofest 2026 FinAgent Yarışması İçin Hazırlanmıştır.</b>
  <br/>
  <i>Geliştirici Ekip: 🚀 <b>BiQuery SmartData Takımı</b></i>
</div>
