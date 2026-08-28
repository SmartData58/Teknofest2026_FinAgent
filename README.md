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

**SmartData BiQuery**, Türkiye'deki katılım bankalarının kampanya ve ürün bilgilerini otomatik olarak toplayan, NLP (Doğal Dil İşleme) modelleriyle anlamlandıran, yapılandırılmış veriye dönüştüren ve kullanıcılara dinamik RAG tabanlı bir chatbot ve gösterge panelleri (dashboard) üzerinden sunan uçtan uca bir finansal analiz platformudur. **Teknofest 2026 FinAgent** yarışması gereksinimlerine göre özel olarak optimize edilmiştir.    

Bankaların heterojen (farklı yapılardaki) veri formatlarını tek bir standart veri modeline oturtarak, kullanıcıların doğal dilde karmaşık finansal sorular sormasına ve net, görsellerle desteklenmiş (tablo/grafik) analitik cevaplar almasına olanak tanır.

> [!IMPORTANT]
> **Yarışma Güncellemesi (Evren API):** Proje, yerel (Ollama vb.) LLM, Embedding ve Reranker servislerinden arındırılarak Teknofest yarışma altyapısı olan **Evren API** (llm-large, llm-fast, bge-m3-embed) ile tam entegre hale getirilmiştir. 

---

## ✨ Öne Çıkan Özellikler ve Son Güncellemeler

- 🧠 **Gelişmiş Çok Dilli Niyet Motoru (Intent Engine):** Chatbot, Türkçe sondan eklemeli yapıyı (örn. *listele, listeler misin, listesini*) hatasız yakalayan ve İngilizce (EN/TR) tam destek sunan esnek bir regex niyet motoruna sahiptir.
- 🖼️ **Görsel Algılama ve Akıllı Çizim:** Sistem, "bana kâr payı tablosu çiz" gibi açık komutlarla, "ödül tutarı en yüksek 3 kampanya" gibi veri isteklerini ayırır. Açıklayıcı sorularda gereksiz grafik çizilmesini engelleyen merkezi bir görselleştirme kararı (tablo/grafik/metin) altyapısı mevcuttur.
- 👁️ **Doğrudan LLM Görsel İşleme (OCR Bypass):** Yüklenen kampanya görselleri artık hantal OCR işlemlerinden geçirilmeden doğrudan Evren API'nin görüntü okuyabilen (vision) modeline aktarılır, hız ve isabet artırılır.
- 🛡️ **Prompt Injection Savunması:** Kullanıcı girdilerinde ve yüklenen dosyalarda "ignore all previous instructions" vb. atakları tespit eden güvenlik gözlem katmanı içerir.
- 📊 **Dinamik Veri Filtreleme:** Birden çok bankanın aynı anda karşılaştırılması (örn. *Kuveyt Türk ile Albaraka'yı kıyasla*), kampanya adı ile arama ve sağlam MongoDB sorgu altyapısıyla desteklenmektedir.

---

## 🛠️ Ön Koşullar (Prerequisites)
Projeyi çalıştırmadan önce sisteminizde aşağıdaki yazılımların kurulu olduğundan emin olun:
- **Docker & Docker Compose** (Tüm sistemi izole bir şekilde çalıştırmak için)
- **Python 3.10+** (Test scriptlerini ve yerel araçları çalıştırmak için)
- **Node.js 18+** (Sadece frontend'i Docker harici geliştirmek isterseniz)

---

## 🏗️ Sistem Mimarisi ve Çalışma Mantığı

Proje 5 ana bileşenden (pipeline) oluşur:

### 1. Kazıyıcı (Scraper) Katmanı
- **Teknoloji:** Python (Playwright / BeautifulSoup)
- **İşlev:** 10 Katılım Bankasının (Albaraka, Kuveyt Türk, vb.) web sitelerini tarar.
- **Çıktı:** Ham verileri MongoDB'deki `ham_kampanya` koleksiyonlarına yazar.

### 2. Bilgi Çıkarımı (NLP Pipeline) Katmanı
- **Teknoloji:** Regex, Evren LLM
- **İşlev:** "kâr payı oranı", "vade sayısı", "ödül miktarı" gibi bilgileri yapılandırır.
- **Çıktı:** Normalize edilmiş veriler `smartdata.islenmis_kampanyalar` koleksiyonuna kaydedilir.


### 3. Vektörleştirme (Embedding) ve Reranker Kararı
- **Teknoloji:** Evren API (`bge-m3-embed`) ve Qdrant Vector DB
- **İşlev:** İşlenmiş kampanya metinleri anlamsal arama yapılabilmesi için Qdrant'a indekslenir.
- **İşlev:** İşlenmiş kampanya metinleri anlamsal arama yapılabilmesi için `bge-m3-embed` (bi-encoder) modeli ile Qdrant'a indekslenir.

> [!NOTE]
> **💡 Mimari Karar: Neden Reranker Kullanılmıyor?**
> Sistemimizde varsayılan olarak Reranker kapalı tutulmaktadır. Embedding modeli (BGE) ve Reranker (Qwen vb.) farklı ailelerden olsa dahi teknik bir uyuşmazlık yaratmazlar; zira Reranker (cross-encoder) hiçbir vektör işlemi yapmadan doğrudan ham metin üzerinden alaka skoru üretir.
> Ancak asıl sorun **kalibrasyon ve performans düşüşüdür**. Yapılan ölçümlerde Evren'in kendi rerank modelinin, `bge-m3-embed`'in hâlihazırda **0,95** olan R@1 (ilk sıradaki isabet) başarısını **0,55'e düşürdüğü** görülmüştür. Katılım bankacılığına özgü, kısa ve Türkçe metinlerde genel amaçlı bir Reranker'ın kalibrasyonu ana arama motorundan daha zayıf kalabilmekte; kazandıracağı marj çok küçükken isabeti bozma riski büyük olmaktadır.

### 4. RAG Tabanlı Chatbot Katmanı (Backend)
- **Teknoloji:** FastAPI, LangChain, Evren LLM
- **İşlev:** Soru Niyet Motoru tarafından analiz edilir. Veriler Mongo ve Qdrant'tan çekilir, Evren LLM'e promptlanarak cevap üretilir. Redis ile cevaplar önbelleklenir.

### 5. Arayüz (Frontend)
- **Teknoloji:** Nuxt.js, Vue 3, Tailwind CSS
- **İşlev:** Chat, Dashboard, Kampanyalar Karşılaştırma modülleri sunar. 

---

## 🔤 Veri Ön İşleme Adımları

Ham kampanya metni, bilgi çıkarımına girmeden önce sırayla şu adımlardan geçer
(`backend/nlp/preprocessing/cleaner.py`):

| # | Adım | Fonksiyon | Ne yapar |
|---|------|-----------|----------|
| 1 | Unicode normalizasyonu | `unicode_normalize` | Görsel olarak aynı ama farklı kodlanmış karakterleri tek biçime indirger |
| 2 | Emoji temizliği | `emojileri_temizle` | Kampanya başlıklarındaki süs emojilerini atar (regex eşleşmelerini bozuyorlardı) |
| 3 | Gürültü temizliği | `gurultu_temizle` | Çerez uyarısı, menü, "Detaylı bilgi için tıklayınız" gibi tekrar eden site kalıplarını siler |
| 4 | Boşluk düzeltme | `bosluk_duzelt` | Satır sonu, sekme ve çoklu boşlukları tek boşluğa indirir |

Ardından **normalizasyon katmanı** (`backend/nlp/normalizasyon/`) farklı yazım
biçimlerini tek bir değere indirir — şartname 5.6'nın istediği davranış:

| Modül | Girdi örnekleri | Çıktı |
|-------|-----------------|-------|
| `percentage.py` | `%2,05` · `% 2.05` · `2.05 %` · `%2,87 'den başlayan` | `2.05` / `2.87` |
| `money.py` | `500 TL` · `500₺` · `500 Türk Lirası` · `1.500.000 TL` | `500.0` / `1500000.0` |
| `duration.py` | `120 ay` · `10 yıl` · `120 aya kadar` | `120` (ay) |
| `date.py` | `31 Aralık 2026` · `31.12.2026` · `31/12/2026` | `2026-12-31` |

> **Türkçeye özgü iki tuzak.** (1) `"İ".lower()` Python'da `i` + birleşen nokta
> (U+0307) üretir; bu, küçültülmüş metinde regex eşleşmelerini sessizce
> bozuyordu — `_kucult()` bunu ayrıca temizler. (2) `32.648,38` sayısında nokta
> binlik ayracı, virgül ondalık ayracıdır; standart sayı çevrimi bu değeri
> `32.64` yapıyordu. Her iki durum da açıkça ele alınıyor.

---

## 📤 Model Çıktılarının Örnekleri

**Girdi** (Albaraka Türk kampanya metninden bir kesit):

> "…Size özel avantajlı oranlarla konut ve taşıt finansmanında fırsat zamanı.
> Ev sahibi olmanın tam zamanı **%2,87 'den başlayan** kâr oranları ile
> bütçenize uygun ödeme planı oluşturun… Yeni ya da ikinci el araç alımlarında,
> **%3,19 'dan başlayan** kâr oranı fırsatı…"

**Çıktı** (`islenmis_kampanyalar` koleksiyonundaki gerçek kayıt):

```json
{
  "genel_bilgi": {
    "banka_id": "albaraka",
    "kampanya_adi": "Dijitale Özel Konut ve Taşıt Finansmanı Kampanyası",
    "kampanya_turu": "tasit_finansmani",
    "sektor": "Akaryakıt ve Otomotiv",
    "hedef_kitle": ["mevcut_musteri"],
    "baslangic_tarihi": "2026-07-31",
    "bitis_tarihi": "2026-08-31",
    "sure_gun": 31,
    "is_active": "aktif"
  },
  "finansman_detay": {
    "kar_payi_orani": 2.87,
    "masraf_bilgi": "Tahsis ücreti belirtilmemiştir."
  }
}
```

Dikkat edilecek noktalar: oran, kesme işaretinden önce boşluk bulunan
`%2,87 'den` yazımından doğru okundu; kampanya türü metinden sınıflandırıldı;
süre iki tarihten hesaplandı.

**Bankalar arası karşılaştırma çıktısı** (konut finansmanı, `/finansman` ucu):

| Banka | Ürün | Kâr oranı | Vade |
|-------|------|-----------|------|
| Albaraka Türk | Konut finansmanı | %2,90 | 120 ay |
| Vakıf Katılım | Konut finansmanı | %2,99 | 120 ay |
| Dünya Katılım | Konut finansmanı | %2,99 | 84 ay |
| Ziraat Katılım | Konut finansmanı | %3,19 | 120 ay |

> Aylık taksit ve toplam geri ödeme tutarları **hesaplanmaz**; bankaların
> yayımladığı değerler olduğu gibi kullanılır (`chatbot/urun_verisi.py`).
> Formül uygulamak, gerçek veriyi tahminle değiştirmek olurdu.

---

## 📏 Model Performansını Değerlendirme Yöntemi

Doğruluk iki ayrı yönden, iki ayrı araçla ölçülür. Her ikisi de boru hattına
gömülüdür (`pipeline.py`, ADIM 3.5) ve tek başına da çalıştırılabilir.

### 1. Kesinlik (precision) — `backend/test/nlp_denetle.py`

Çıkarılan her değeri **kaynak metne karşı** doğrular: değer aralık dışı mı,
metinde gerçekten geçiyor mu (kanıtlı mı), tarihler tutarlı mı, etiket geçerli
taksonomide mi.

```bash
docker exec teknofest2026_finagent-backend-1 python /app/test/nlp_denetle.py
```

### 2. Geri çağırma (recall) — `backend/test/nlp_kacak.py`

Ters yönden bakar: metinde bir **gösterge** var ama alan boş kalmış mı? Yani
çıkarılabilecekken kaçırılan bilgiyi sayar.

```bash
docker exec teknofest2026_finagent-backend-1 python /app/test/nlp_kacak.py
```

### Güncel sonuçlar (599 kayıt)

**Kesinlik: %99,3** — 599 kayıtta 4 kusur (3'ü tür belirlenememesi, 1'i
kanıtsız ödül tutarı).

| Alan | Dolu | Metinde gösterge | Yakalama |
|------|-----:|-----------------:|---------:|
| `kar_payi_orani` | 10 | 8 | %100 |
| `vade_ay` | 73 | 20 | %100 |
| `taksit` | 273 | 273 | %100 |
| `finansman_tutari` | 49 | 15 | %100 |
| `odul_tutari` | 219 | 121 | %100 |
| `nakit_iade_yuzde` | 41 | 10 | %100 |
| `bitis_tarihi` | 460 | 388 | %93 |

> `kar_payi_orani` yalnızca 10 kampanyada dolu; bu bir çıkarım zayıflığı değil
> **veri gerçeğidir** — kart ve alışveriş kampanyalarının büyük çoğunluğu bir
> kâr payı oranı yayımlamaz. Oranlar ağırlıklı olarak finansman ürünlerinde
> bulunur ve `finansman_urun` koleksiyonundaki 48 kaydın neredeyse tamamında
> doludur.

### 3. Ürün katmanı testleri

```bash
python backend/test/test_urun_verisi.py
```
```bash
python backend/test/test_urun_chat_uctan_uca.py
```

Birincisi 14 birim testi (veritabanı gerektirmez), ikincisi canlı `/api/chat`
ucuna 4 uçtan uca test atar. Uçtan uca testler şartnamenin kendi örnek
senaryolarını (s.13) doğrular: tek bankaya bilgi sorma, iki banka
karşılaştırma, mevduat ürününün krediyle karıştırılmaması ve modele yazılmış
talimatların arayüze sızmaması.

---

## 🧯 Karşılaşılan Problemler ve Çözüm Yaklaşımları

| Problem | Belirti | Çözüm |
|---------|---------|-------|
| **Türkçe noktalı İ** | Küçültülmüş metinde regex'ler sessizce eşleşmiyordu | `İ→i`, `I→ı` eşlemesi ve birleşen noktanın atılması |
| **Binlik ayracı** | `32.648,38` değeri `32.64` olarak okunuyordu | Saf binlik kalıbı ayrı ele alınıyor |
| **Mevduat ↔ kredi karışması** | "katılım **hesabı** kâr payı getirisi" sorusundaki *isim*, "hesapla" *fiili* sanılıyor ve mevduat için "Aylık Taksit 125.990 TL" üretiliyordu | Taksit hesaplayıcısı kaldırıldı; mevduat ve finansman ayrı niyetlere bağlandı |
| **Oran biriminin varsayılması** | Kullanıcının verdiği yıllık mevduat oranı aylık kredi oranı kabul ediliyordu | Hesaplama kaldırıldı; bankanın yayımladığı taksit değeri kullanılıyor |
| **İki kopuk veri dünyası** | "En uzun vade" sorusuna 9 ay cevabı (kampanya taksitleri), oysa konut finansmanında 120 ay var | Ürün metriği + finansman/kredi geçen sorular ürün tablosuna yönlendiriliyor; "kampanya" geçen sorular kampanya akışında kalıyor |
| **Şartname Senaryo 2 yazımı** | "X mı daha avantajlı, Y mı?" sorusu "veri bulunamadı" veriyordu ("avantaj" kelimesi soruyu yorum sorusu sanıyordu) | Adı geçen banka sayısı ≥2 ve kıyas belirteci varsa tablo zorunlu (`iki_banka_kiyasi`) |
| **Kayıt kopyaları** | `katilim_hesap`'ta her kayıt 3 kez (kazıyıcı `insert_many` kullanıyordu) | Tekil indeks + `upsert`; kardeş kazıyıcıdaki kalıp uygulandı |
| **Model talimatının sızması** | Arayüzdeki tablo altyazısında "Bunları hâlen geçerli teklifmiş gibi sunma" yazıyordu | Notlar ikiye ayrıldı: modele giden ve kullanıcıya gösterilen |
| **Çift import kökü** | `pipeline.py` `backend.*`, konteyner `nlp.*` bekliyordu; geçici symlink gerekiyordu | Her iki yolu deneyen `try/except ModuleNotFoundError` kalıbı |
| **Tam tarama sorgusu** | Kanıt paneli 4.963 belgeyi tarıyordu | `kampanya_id` üzerinde indeks (COLLSCAN → IXSCAN, 1,68 → 0,33 ms) |
| **Her çağrıda yeni bağlantı** | Dört modül her istekte yeni `MongoClient` açıyordu | Paylaşılan havuz (`chatbot/mongo_baglanti.py`) |

---

## 🏢 Şirket İçi Uyumluluk ve Dışa Bağımlılıklar

Proje, özellikle bankacılık gibi regülasyonların sıkı olduğu sektörlerdeki "veri gizliliği" ve "kurumsal ağ uyumluluğu" gözetilerek tasarlanmıştır.

### Şirket İçi Uyumluluk (Corporate Compliance)
- **Mikroservis Mimarisi:** Sistem (Frontend, Backend, Scraper, DB) tamamen konteynerize (Docker) edilmiştir. Bir bankanın mevcut şirket içi (on-premise) Kubernetes, OpenShift veya CI/CD boru hatlarına (pipeline) doğrudan entegre edilebilir.
- **Veri Gizliliği (Data Privacy):** Müşteri ve sohbet verileri dışarıdaki ticari / açık uçlu LLM sağlayıcılarına (Örn. OpenAI, Anthropic) gönderilmez. Proje tam izole veya kurum tarafından sağlanan özel modellere (şu an için Teknofest **Evren API** altyapısına) entegre çalışır.
- **Kurumsal Kullanıcı Modu (Analist Görünümü):** Chatbot'un şirket içi banka personeline özel bir görünüm seçeneği vardır. Analistler sistemi *"Rakiplerin taşıt kredisiyle bizimkini kıyasla"* gibi doğrudan rakip analizine yönelik banka-içi senaryolarla kullanabilirler.

### Tam Kurum İçi (On-Premise) Mod — Sıfır Dış Bağımlılık

Şartname 5.9, çözümün "dış servislere bağımlı olmadan" çalışabilmesini istiyor.
Mimari bunu **kod değişikliği gerektirmeden** karşılar: LLM, embedding ve vektör
veritabanı adreslerinin üçü de ortam değişkenidir
(`backend/chatbot/evren_client.py` → `BASE_URL`, `MODEL_ANA`, `MODEL_HIZLI`,
`EMBED_MODEL`, `EVREN_QDRANT_URL`). Ollama OpenAI uyumlu bir `/v1` ucu
yayımladığı için mevcut `ChatOpenAI` istemcisi olduğu gibi çalışır.

**1. Yerel servisleri başlatın:**

```bash
docker compose --profile yerel-llm --profile yerel-vektor up -d ollama qdrant
```

**2. Modelleri indirin (bir kez):**

```bash
docker exec smartdata-ollama ollama pull qwen2.5:7b-instruct
```
```bash
docker exec smartdata-ollama ollama pull bge-m3
```

**3. `.env` dosyasını yerele çevirin:**

```env
EVREN_BASE_URL=http://ollama:11434/v1
EVREN_API_KEY=yerel
EVREN_MODEL=qwen2.5:7b-instruct
EVREN_MODEL_HIZLI=qwen2.5:7b-instruct
EVREN_EMBED_MODEL=bge-m3
EVREN_QDRANT_URL=http://qdrant:6333
EVREN_QDRANT_KEY=
EVREN_TEAM=
```

**4. Vektörleri yerelde yeniden kurun:**

```bash
docker exec teknofest2026_finagent-backend-1 python -m chatbot.indexing
```

Bu modda hiçbir istek kurum ağının dışına çıkmaz. MongoDB ve Redis zaten
yereldir; kalan tek dış çağrı, kazıyıcının banka sitelerine yaptığı — o da
zaten halka açık veri toplama adımıdır ve çalışma anında değil, veri güncelleme
sırasında yapılır.

> **Kritik nokta:** Bilgi çıkarımının kendisi hiçbir zaman LLM'e bağımlı
> değildir. Şartnamenin çekirdek işini yapan katman
> (`backend/nlp/extraction/rule_based.py`, ~2.000 satır kural) tamamen yerelde,
> deterministik olarak çalışır. LLM yalnızca sohbet arayüzünün cevabını
> biçimlendirir ve belirsiz ifadelerde yardımcı çıkarım yapar. LLM tamamen
> devre dışı bırakılsa bile kampanya metinlerinden bilgi çıkarma, sınıflandırma,
> normalizasyon ve bankalar arası karşılaştırma çalışmaya devam eder.


### Dışa Bağımlılıklar (External Dependencies)
Sistemin ihtiyaç duyduğu temel ağ ve yazılım bağımlılıkları şunlardır:
1. **Evren API (Teknofest):** Projenin Doğal Dil İşleme (LLM), Vektörleştirme (bge-m3-embed) ve Güvenlik (Guard) işlemleri için internet üzerinden HTTPS (443) ile erişilen dış bağımlılığıdır. 
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

## ⚙️ Konfigürasyon ve Kurulum

Sistem Docker Compose üzerine tasarlanmıştır ve tüm ortam yapılandırması `.env` dosyası üzerinden yönetilir.

### 1. `.env` Dosyasının Hazırlanması ve Konfigürasyon Detayları
Proje dizinindeki `example.env` şablonunu kopyalayarak başlayın:
```bash
cp example.env .env
```
Projedeki tüm ayarlar bu tek `.env` dosyası üzerinden yönetilir. Dosyadaki değişkenlerin işlevleri aşağıda kategoriler halinde açıklanmıştır:

#### 🟢 Evren API (Yarışma LLM) Ayarları
*Proje, yerel LLM yerine Teknofest yarışma sunucularını kullanır.*
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
- **`MONGO_USER` & `MONGO_PASSWORD`**: MongoDB root yetkilendirme bilgileri (Kendi belirleyeceğiniz şifre).
- **`MONGO_URI`**: *Önemli!* Host makineden (script veya testler için) bağlantılarda `localhost:27017` kullanılırken, Docker içinde backend doğrudan `mongodb://...` adresine bağlanır. Bu değişken host bazlı bağlantılar içindir, Docker Compose içerdekini ezer.
- **`STARTUP_CACHE_FLUSH`**: Sistem ayağa kalktığında eski sohbet ve veri önbelleklerini (Redis) temizler (`1` veya `0`). Demo öncesi `0` yapılması yanıtları hızlandırır.

#### 🤖 Ajan (Agent) ve Güvenlik Davranışları
- **`SUPERVISOR_AKTIF`**: Her LLM yanıtını son bir denetim modelinden geçirerek kalite kontrolü yapar (`true` / `false`). Güvenliği artırır ancak yanıt süresini uzatır.
- **`GORSEL_LLM_FALLBACK`**: Regex (Kurallı) Niyet Motoru grafik mi tablo mu çizileceğinden emin olamazsa, karar vermesi için hızlı bir LLM ajanına danışır (`true`).
- **`GUARD_AKTIF` / `GUARD_ENGELLE`**: Kullanıcı girdilerindeki Prompt Injection (saldırı) denemelerini tarar. `GUARD_ENGELLE=false` ise sadece uyarır ve loglar, sistemi bloklamaz.
- **`ADMIN_TOKEN`**: `/admin/reindex` (Vektörleri sıfırdan oluşturma) REST ucunu korur. Boş bırakılırsa uç herkese açık hale gelir!

---

## 🚀 Çalıştırma ve Derleme (Build) Komutları

Sistem farklı ortamlar (Geliştirme, Prod, GPU) için farklı Docker konfigürasyon dosyalarına sahiptir. İhtiyacınıza uygun olan komutu seçin:

### 1. Standart Geliştirme (Dev) Ortamı Başlatma
Varsayılan olarak `docker-compose.yml` ve (eğer dizinde varsa) `docker-compose.override.yml` otomatik yüklenir. İmajları derlemek ve arka planda başlatmak için:
```bash
docker-compose up -d --build
```

### 2. Prodüksiyon (Prod) Ortamında Başlatma
Sistemi canlıya alırken `docker-compose.prod.yml` dosyasını kullanmalısınız. Bu dosya, gereksiz geliştirme portlarını kapatır ve hata anında yeniden başlatma (restart) ilkelerini düzenler. 
*(Uyarı: `-f` ile özel bir dosya verdiğinizde `override.yml` otomatik yüklenmez)*
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 3. NVIDIA GPU Destekli Başlatma (Hızlı OCR)
Backend içerisinde belge ayrıştırma (OCR) işlemleri (PDF/DOCX yükleme vb.) yerel olarak çalışır ve `torch` (CUDA) kullanır. OCR hızını maksimize etmek ve backend'e GPU yetkisi vermek için `nvidia` yapılandırmasını dahil etmelisiniz:
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.nvidia.yml up -d --build
```
*GPU'nun tanınıp tanınmadığını test etmek için (Çalışırken):*
```bash
docker-compose exec backend python -c "import torch; print(torch.cuda.is_available())"
```

### 4. Tekil Docker İmajlarını Derleme (Manuel Build)
Tüm sistemi `docker-compose` ile tek seferde ayağa kaldırmak istemiyor veya sadece bir servisin imajını oluşturmak istiyorsanız şu komutları kullanabilirsiniz:

```bash
# Backend imajını derlemek için:
docker build -t finagent-backend ./backend

# Frontend imajını derlemek için:
docker build -t finagent-frontend ./frontend

# Scraper imajını derlemek için:
docker build -t finagent-scraper ./scraper
```

### 5. Yalnızca Vektör Veritabanı Yedeğini Çalıştırma (Fallback Profil)
Yarışma sırasında Evren Qdrant sunucusunun erişilemez olduğu senaryolar için bir "yedek" profil oluşturulmuştur. Bu profili aktif ederseniz sistem yerel bir Qdrant konteyneri ayağa kaldırır:
```bash
docker-compose --profile yerel-vektor up -d
```
*(Bu durumda `.env` içindeki `EVREN_QDRANT_URL=http://qdrant:6333` şeklinde güncellenmeli ve anahtarlar boş bırakılmalıdır.)*

### 6. Veri Kazıma ve İndekslemeyi (Pipeline) Manuel Tetikleme
Sistem ilk kurulduğunda veritabanları boş olacaktır. Verileri çekip işlemek için Scraper konteynerinde pipeline script'ini çalıştırın:
```bash
# Standart ortamda tüm 10 bankanın verisini çekmek için:
docker-compose exec scraper python pipeline.py --hepsi

# NVIDIA GPU profiliyle sistemi başlattıysanız tüm veriyi çekmek için:
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.nvidia.yml exec scraper python pipeline.py --hepsi

# Sadece belirli bir banka (örn. albaraka) için:
docker-compose exec scraper python pipeline.py albaraka
```

### 7. Servisleri Kapatma
Verilerinizi (Volume'lar) silmeden sistemi durdurmak için:
```bash
docker-compose down
```

---

## 🧪 Test Scriptleri ve Kullanım Parametreleri

`backend/test/` dizini altında, projenin her bir katmanını veya sorunlu kısımlarını teşhis edebilmek için özel olarak yazılmış birçok test dosyası bulunur. **Bu testler Docker içinden değil, doğrudan host makinenizde (Python kurulu bir terminalde) sanal ortam etkinleştirilerek kullanılmalıdır.** 

> Testleri çalıştırmadan önce `backend/requirements.txt` paketlerinin sisteminizde kurulu olduğundan emin olun ve kök dizindeki `.env` dosyasının doğru MongoDB/Qdrant hostlarını (localhost vb.) işaret ettiğine dikkat edin.

### 1. `test_buyuk.py` (Kapsamlı Doğruluk ve Regresyon Testi)
Sistemin büyük bir prompt havuzuna (Örn. `buyuk_sonuc.json`) nasıl yanıt verdiğini (Accuracy, Halüsinasyon, Reranker farkı) ölçer.
*   **Kullanım:** `python backend/test/test_buyuk.py [PARAMETRELER]`
*   **Önemli Parametreler:**
    *   `--kat <kategori>`: Yalnızca belirli soru kategorilerini test eder (Örn: `liste, kiyas, grafik, halusinasyon`).
    *   `--kayit <dosya.json>`: Test sonuçlarını belirtilen JSON dosyasına kaydeder (A/B testing için idealdir).
    *   `--paralel <N>`: Aynı anda N adet asenkron istek atarak süreci hızlandırır (Load testing'e dönüşebilir).
    *   `--devam`: Daha önce başlanmış bir `--kayit` dosyası verilirse, sadece eksik kalan senaryoları çalıştırır.
*   **Örnek:** `python backend/test/test_buyuk.py --kat liste,kiyas --kayit deneme1.json --paralel 3`

### 2. `testapi.py` (Canlı API Entegrasyon Testi)
Sistem tam ayaktayken `/api/chat` ve diğer uçları uçtan uca simüle eder.
*   **Kullanım:** `python backend/test/testapi.py [PARAMETRELER]`
*   **Önemli Parametreler:**
    *   `--liste`: Sistemde yüklü olan tüm hazır test senaryolarını numaralarıyla listeler.
    *   `--sec <numara,ad>`: Yalnızca virgülle ayrılmış numaraları veya isim parçalarını test eder.
    *   `--detay`: LLM'den gelen cevap metnini ve ajanların düşünme (thinking) aşamalarındaki zamanları (sn) loglar.
*   **Örnek:** `python backend/test/testapi.py --sec 1,4 --detay`

### 3. `test_dayaniklilik.py` (Chaos / Resilience Test)
FastAPI, Redis ve Veritabanı servisleri aniden çökerse / erişilemez olursa sistemin (özellikle Evren API bağlantılarının) nasıl tepki verdiğini ve kurtulduğunu test eder.
*   **Kullanım:** `python backend/test/test_dayaniklilik.py [PARAMETRELER]`
*   **Önemli Parametreler:**
    *   `--onayla`: Bunu eklemezseniz script sadece "kuru çalıştırma (dry run)" yapar. Konteynerleri **gerçekten** durdurup başlatması için zorunludur.
    *   `--sec <servis>`: Sadece belirtilen servisleri çökertip test eder (Örn: `qdrant,redis`).

### 4. `llm_teshis.py` (LLM Muhakeme ve Token Testi)
Özellikle Evren LLM'in `thinking` (muhakeme) sürecine giden token bütçesini, bağlam şişmesini ve olası "boş cevap" (length finish reason) sorunlarını teşhis eder.
*   **Kullanım:** `python backend/test/llm_teshis.py [PARAMETRELER]`
*   **Önemli Parametreler:**
    *   `--kampanya <N>`: Promptun içine sahte (dummy) bağlam olarak N adet kampanya metni basar (Bağlam sınırlarını zorlamak için).
    *   `--max-tokens <N>`: Test sırasında `.env` dosyasındaki limiti ezerek farklı token sınırları dener.

### 5. `ocr_olcum.py` (Yerel CUDA/GPU Performans Ölçümü)
Eğer sistem GPU içeren bir cihazda çalışıyorsa, belge yükleme sürelerini CPU ve GPU (PyTorch/CUDA) arasında kıyaslar.
*   **Kullanım:** `python backend/test/ocr_olcum.py [PARAMETRELER]`
*   **Önemli Parametreler:**
    *   `--dosya <yol>`: Hızı ölçülecek özel bir PDF veya görsel belirtir.
    *   `--sadece-durum`: Test çalıştırmaz, sadece sistemin GPU görüp görmediğini yazdırır.

### Diğer Kritik Araçlar (Parametresiz Çalışırlar)
*   **`testintent.py` / `testgrafik.py`**: Doğal Dil Regex Niyet Motoru'nu (API'ye çıkmadan, 0 ms içinde) test eder. (Örn: "grafik çizme" dendiğinde doğru yakalıyor mu?)
*   **`gecikme_teshis.py`**: Sunucudaki IPv6/IPv4 DNS resolving timeout'larını analiz eder (Örn. Yanıtın ilk saniyesinin neden 11 saniye geciktiğini bulur).
*   **`mongo_kontrol.py`**: MongoDB içindeki verilerin (örn: Taksit, Kâr Payı alanları) beklenen formatta olup olmadığını raporlar.
*   **`bagimlilik_denetimi.py`**: `.env` ve `requirements.txt` ile kod tabanındaki fiili "import" komutlarının birbiriyle uyumlu olup olmadığını saptar.
*   **`test_db.py`**: Veritabanı bağlantısını test edip `islenmis_kampanyalar` koleksiyonundan örnek kayıtları (`banka_id`, `kampanya_turu`) ekrana basarak verilerin sağlıklı şekilde ayrıştırıldığını doğrular.
*   **`test_turu.py`**: MongoDB'deki kampanya verilerini tarayarak sistemde benzersiz (distinct) kaç farklı kampanya türü (`kampanya_turu`) bulunduğunu listeler. Veri kazıma (scraping) ve sınıflandırma sonrası veri setinin çeşitliliğini görmek için idealdir.

---

## 🤖 Kullanım Senaryoları (Chatbot)
- **Filtreleme & Listeleme:** *"Kuveyt Türk ile Albaraka'nın tüm kampanyalarını listeler misin?"*
- **Sıralama:** *"Ödül tutarı en yüksek olan 5 kampanyayı düşükten yükseğe sırala."*
- **Görsel Engelleme:** *"Bana tablo veya grafik çizme, sadece metin olarak anlat."*

## 📜 Lisans ve Kullanım Koşulları
Bu proje **Apache License 2.0** altında lisanslanmıştır. Kullanım koşullarının tam metni için kök dizindeki `LICENSE` dosyasına göz atabilirsiniz.
*   **Ticari Kullanım:** Açık kaynaklı ve ticari projelere (gerekli atıflar yapılarak) entegre edilebilir.
*   **Sorumluluk Reddi:** Yazılım "olduğu gibi (AS IS)" sunulur, hiçbir garanti içermez.

<div align="center">
  <br/>
  <b>Teknofest 2026 FinAgent Yarışması İçin Hazırlanmıştır.</b>
  <br/>
  <i>Geliştirici Ekip: 🚀 <b>BiQuery SmartData Takımı</b></i>
</div>
