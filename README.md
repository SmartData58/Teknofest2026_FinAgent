# 🏦 SmartData BiQuery

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![NuxtJS](https://img.shields.io/badge/Nuxt-00DC82?style=for-the-badge&logo=nuxtdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-DC2626?style=for-the-badge&logo=qdrant&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)

**Katılım Bankacılığı için NLP, RAG ve Hibrit Çıkarım Destekli Finansal Veri Analiz Platformu**

[Ana Özellikler](#-ana-özellikler)   •[Teknoloji Yığını](#-teknoloji-yığını) • [Sistem Mimarisi](#-sistem-mimarisi) • [Adımlar](#-adımlar)

</div>

---

## 📌 Hakkında

**SmartData BiQuery**, katılım bankacılığı alanındaki kampanya ve ürün bilgilerini otomatik olarak toplayan, Türkçe NLP modelleriyle anlamlandıran, yapılandırılmış veriye dönüştüren ve kullanıcıya dashboard, karşılaştırma ekranı ve RAG tabanlı chatbot üzerinden sunan **uçtan uca on-premise finansal analiz platformudur**.

Farklı bankaların heterojen formatlarda yayımladığı kampanya, finansman, kart ve yatırım ürünlerini tek bir standart veri modelinde toplar.

> [!NOTE]
> Proje, hassas finansal verilerin kurum dışına çıkmasını engellemek amacıyla tamamen **harici API bağımlılığı olmadan (on-premise / yerel LLM)** çalışacak şekilde tasarlanmıştır.

### ❓ Örnek Doğal Dil Sorguları

- 💬 *"En düşük kâr payı hangi bankada?"*
- 💬 *"120 ay vadeli konut finansmanı kampanyaları hangileri?"*
- 💬 *"Yeni müşteriye en yüksek ödülü veren banka hangisi?"*
- 💬 *"Kuveyt Türk ile Albaraka'nın taşıt finansmanı kampanyalarını karşılaştır."*

---
## Amaç

Katılım bankalarının farklı formatlarda yayımladığı kampanya, finansman, kart ve yatırım ürünü bilgilerini tek bir standart veri modelinde toplamak ve kullanıcıların bu veriler üzerinde doğal dil ile sorgulama, filtreleme ve karşılaştırma yapmasını sağlamaktır.

Örnek kullanıcı soruları:

```text
En düşük kâr payı hangi bankada?
120 ay vadeli konut finansmanı kampanyaları hangileri?
Yeni müşteriye en yüksek ödülü veren banka hangisi?
Kuveyt Türk ile Albaraka'nın taşıt finansmanı kampanyalarını karşılaştır.
```

## ✨ Ana Özellikler

- 🕷️ Katılım bankalarının resmi web sitelerinden otomatik veri toplama
- Kampanya, finansman, kart ve yatırım ürünü sayfalarının ayrıştırılması
- Türkçe metin temizleme ve ön işleme
- 🧹 Para, yüzde, tarih ve vade ifadelerinin normalize edilmesi
- Kâr payı, finansman tutarı, vade, taksit, ödül, indirim, masraf ve hedef kitle çıkarımı
- 🏷️ Domain-specific NER ile finansal varlık tanıma
- BERTurk tabanlı kampanya türü ve hedef kitle sınıflandırması
- ⚖️ Regex, NER ve LLM sonuçlarını birleştiren hibrit karar motoru
- Çıkarılan her bilgi için kanıt, yöntem ve güven skoru
- Embedding modeli ile anlamsal arama
- 🔍 RAG mimarisi ile kaynaklı chatbot cevapları
- Banka ve kampanya karşılaştırma motoru
- 📊 Nuxt tabanlı dashboard ve kullanıcı arayüzü
- Docker Compose ile on-premise kurulum

## Teknoloji Yığını

| Bileşen | Teknoloji |
| --- | --- |
| Backend API | FastAPI |
| Frontend | Nuxt, Vue, Tailwind CSS |
| Scraper | Python, BeautifulSoup, Playwright |
| Veritabanı | PostgreSQL / SQLite |
| ORM | SQLAlchemy |
| NLP | Regex, NER, BERTurk, Hugging Face Transformers |
| LLM | Yerel LLM, Ollama |
| Embedding | Türkçe/multilingual embedding modeli |
| Vector DB | Qdrant |
| Container | Docker, Docker Compose |
| Test | pytest |

## Sistem Mimarisi

```text
Banka Web Siteleri
        |
        v
Web Scraper
        |
        v
Ham Veri Deposu
        |
        v
NLP Pipeline
        |
        +--> Metin Temizleme
        +--> Normalizasyon
        +--> Kural Tabanlı Çıkarım
        +--> NER
        +--> BERTurk Sınıflandırma
        +--> LLM Destekli Çıkarım
        +--> Karar Birleştirme
        |
        v
PostgreSQL
        |
        +--> Dashboard API
        +--> Karşılaştırma API
        +--> Chatbot API
        |
        v
Embedding + Qdrant
        |
        v
RAG + Yerel LLM
        |
        v
Nuxt Arayüz
```
# Adımlar
## Veri Toplama

Scraper katmanı, her katılım bankası için ayrı spider kullanır. Her spider ilgili bankanın kampanya ve ürün sayfalarını dolaşır, metinleri çıkarır ve ham veri formatında saklar.

Toplanan temel alanlar:

```text
banka
başlık
kaynak URL
ham metin
kampanya türü
ürün türü
çekilme tarihi
```

Scraper çalıştırma:

```bash
python -m backend.db.seed
python -m scraper.runner --hepsi
```

Tek banka için:

```bash
python -m scraper.runner kuveytturk
```

## NLP Pipeline

NLP pipeline, ham veriyi işleyerek yapılandırılmış finansal bilgiye dönüştürür.

Çıkarılan alanlar:

```text
kampanya_turu
kar_payi_orani
finansman_tutari
vade_ay
taksit_sayisi
tahsis_ucreti
masraf_bilgisi
odul_miktari
indirim_orani
alisveris_puani
baslangic_tarihi
bitis_tarihi
hedef_kitle
kosullar
```

Pipeline çalıştırma:

```bash
python -m backend.nlp.pipeline
```

Tek banka için:

```bash
python -m backend.nlp.pipeline kuveytturk
```

## NER

NER modülü, kampanya metinlerinde finansal varlıkları tespit eder.

Desteklenen entity tipleri:

```text
BANKA_ADI
KAR_PAYI_ORANI
FINANSMAN_TUTARI
VADE
TAKSIT
TAHSIS_UCRETI
MASRAF
ODUL_MIKTARI
INDIRIM_ORANI
ALISVERIS_PUANI
BASLANGIC_TARIHI
BITIS_TARIHI
HEDEF_KITLE
URUN_TURU
KAMPANYA_TURU
```

Örnek:

```text
Yeni müşterilere özel %2,05 kâr payı ile 120 ay vadeli konut finansmanı.
```

NER çıktısı:

```json
[
  {"text": "Yeni müşterilere", "label": "HEDEF_KITLE"},
  {"text": "%2,05", "label": "KAR_PAYI_ORANI"},
  {"text": "120 ay", "label": "VADE"},
  {"text": "konut finansmanı", "label": "URUN_TURU"}
]
```

## Kampanya Sınıflandırma

sınıflandırma modeli, kampanyaları aşağıdaki türlere ayırır:

```text
konut_finansmani
tasit_finansmani
ihtiyac_finansmani
kart_kampanyasi
yatirim_urunu
alisveris_puani
yeni_musteri
maas_musterisi
genel
```

Bu sınıflar dashboard filtrelerinde, karşılaştırma motorunda ve chatbot niyet analizinde kullanılır.

## Hibrit Bilgi Çıkarımı

Sistem tek bir modele bağımlı değildir. Bilgi çıkarımı şu sırayla yapılır:

```text
Regex / kural tabanlı çıkarım
        |
        v
NER destekli çıkarım
        |
        v
BERTurk sınıflandırma
        |
        v
Yerel LLM ile eksik alan çıkarımı
        |
        v
Karar birleştirme ve güven skoru
```

Karar motoru, metinde kanıtı olmayan LLM çıktılarını reddeder. Böylece sistemin uydurma bilgi üretmesi engellenir.

## RAG ve Chatbot

Chatbot, doğrudan model hafızasına güvenmez. Önce veritabanı ve vektör indeksinden ilgili kampanyaları bulur, sonra kaynaklara dayalı cevap üretir.

Akış:

```text
Kullanıcı sorusu
        |
        v
Niyet analizi
        |
        v
Yapılandırılmış veri sorgusu + vektör arama
        |
        v
İlgili kampanyalar
        |
        v
Yerel LLM ile kaynaklı cevap
```

Örnek cevap:

```text
Toplanan verilere göre en düşük kâr payı Albaraka Türk'ün konut finansmanı kampanyasında görünmektedir: %1,89.
Bu değer kampanya metnindeki "%1,89 kâr payı" ifadesinden çıkarılmıştır.
```

## Backend API

Temel endpoint'ler:

```text
GET  /api/health
GET  /api/banks
GET  /api/campaigns
GET  /api/campaigns/{id}
GET  /api/campaigns/{id}/evidence
GET  /api/dashboard
GET  /api/compare
POST /api/chat
POST /api/scrape/run
POST /api/nlp/run
POST /api/rag/reindex
```

Örnek chatbot cevabı:

```json
{
  "answer": "En düşük kâr payı Albaraka Türk kampanyasında görünmektedir: %1,89.",
  "sources": [
    {
      "campaign_id": 12,
      "bank": "Albaraka Türk",
      "title": "Konut Finansmanı Kampanyası",
      "url": "https://..."
    }
  ]
}
```

## Dashboard

Dashboard aşağıdaki bilgileri gösterir:

```text
toplam banka sayısı
veri toplanan banka sayısı
toplam kampanya sayısı
kampanya türü dağılımı
çıkarılan alan sayıları
son veri toplama tarihi
en düşük kâr payı
en uzun vade
en yüksek ödül
model başarı metrikleri
```

## Kampanyalar Ekranı

Kampanyalar ekranında kullanıcılar:

```text
banka bazlı filtreleme
kampanya türüne göre filtreleme
hedef kitleye göre filtreleme
kâr payı olan kampanyaları listeleme
vade ve ödül bilgisine göre sıralama
kaynak URL görüntüleme
çıkarım kanıtlarını inceleme
```

yapabilir.

## Karşılaştırma Motoru

Karşılaştırma motoru, bankaları ve kampanyaları normalize edilmiş alanlara göre karşılaştırır.

Desteklenen analizler:

```text
en düşük kâr payı
en uzun vade
en yüksek ödül
en düşük masraf
banka bazlı kampanya karşılaştırma
kampanya türüne göre sıralama
hedef kitleye göre analiz
```

## Lisans

Bu proje açık kaynak olarak yayımlanmak üzere hazırlanmıştır. Lisans bilgisi `LICENSE` dosyasında yer alır.
