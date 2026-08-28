# SmartData BiQuery — Sunum Akışı ve Plan

> **Format:** 4 dakika sunum + 1 dakika demo videosu.
> **Slayt sayısı:** 7 ana slayt + 4 yedek (yalnızca soru-cevapta).
>
> 4 dakika = **240 saniye**. Bu, slayt başına ortalama 34 saniye demek.
> Aşağıdaki her slaytın yanında saniye bütçesi var; **prova ederken kronometre
> tutun.** Zaman aşan sunum, jüride "hazırlıksız" izlenimi bırakır.

---

## 0. Önce okunması gereken: doğrulanmamış iddialar

Elimizdeki taslak metinde kod tabanında **karşılığı olmayan** iddialar vardı.
Jüri sunumdan sonra sistemi test edeceği için bunlar doğrudan risk. Aşağıdakiler
plandan **çıkarıldı**; yerlerine gerçek ve en az onlar kadar güçlü olanlar kondu.

| Taslaktaki iddia | Gerçek durum | Yerine ne diyoruz |
|---|---|---|
| "ModernBERT-TR LoRA ile eğitilmiş model" | Kodda yok; ince ayarlı model bulunmuyor | "Kural tabanlı yüksek-kesinlik + LLM tamamlayıcı" — gerçek mimari, ölçülmüş sonuçlu |
| "Supervisor Çıktı Denetçisi (aktif kalkan)" | Kod var ama `SUPERVISOR_AKTIF=false` | "Çıkarım Kanıtları paneli" — gerçek şeffaflık katmanı |
| "Anti-Reranker Kalibrasyonu" | `EVREN_RERANK=false` | Anılmıyor |
| "Tahminleme motoru / gelecek ay öngörüsü" | Kodda 0 eşleşme | Yol haritasına taşındı ("yapacağız") |
| "NER modülü" | `nlp/ner/` klasörü boş | Anılmıyor |
| "%100 On-Premise, hiçbir harici API yok" | Kurum içi mod ayrı profil | "Tek komutla kurum içi; çekirdek çıkarım zaten dış ağa çıkmıyor" (kanıtlı) |

> **Altın kural:** Slayttaki her sayı ve özellik, jüri istediğinde canlı
> gösterilebilmeli. Gösteremeyeceğimiz hiçbir şeyi yazmıyoruz.

---

## Anlatının omurgası

**Tek cümlelik konumlandırma — sunumda en az iki kez geçsin:**

> "Katılım bankalarının dağınık kampanya metinlerini **kanıtlanabilir**
> yapılandırılmış veriye çeviren ve banka içinde, dışarı hiçbir veri
> çıkarmadan çalışan bir karşılaştırma motoru."

Üç kelime: **Kanıtlanabilir · Karşılaştırılabilir · Kurum içi**

### 4 dakikanın puan ağırlığına göre dağılımı

| Kriter | Ağırlık | Ayrılan süre | Slayt |
|---|---:|---:|---|
| Model Başarısı ve Anlamlandırma | %30 | ~75 sn | 2, 3, 4 |
| On-Prem Uygulanabilirlik | %20 | ~40 sn | 6 |
| Fonksiyonellik ve Senaryo Kapsamı | %20 | ~45 sn | 1, 5 |
| Teknik İmplementasyon ve Mimari | %20 | ~40 sn | 2 |
| Yenilikçilik ve Yaratıcılık | %10 | ~25 sn | 3, 7 |

### 4 dakikada anlatılmayacaklar (bilinçli feda)

Zaman yetmez; bunları **yedek slaytlara** koyduk, sorulursa çıkarırız:
takım görev dağılımı, port numaraları, Redis/ETag detayları, Tier gruplaması,
i18n, OCR belge girdisi, performans tabloları.

---

# SLAYTLAR

---

## Slayt 1 — Problem ve çözüm (aynı slaytta) · **30 sn**

**Görsel:** Üstte üç bankanın kampanya metninden gerçek kesit — aynı bilgi üç
farklı yazımda (`%1,89` / `% 1.89` / `yüzde 1,89`). Altta tek satırlık çözüm
şeridi: **Kanıtlanabilir · Karşılaştırılabilir · Kurum içi**

**Ekranda:**
- 10 katılım bankası · **599 kampanya** · her biri farklı formatta
- Bir analistin tek bir konut finansmanı kıyası için taraması gereken sayfa: **10+**

**Konuşma notu:**
> "Katılım bankacılığının kendine ait bir dili var: faiz yerine kâr payı, kredi
> yerine finansman. Ve bu dil her bankada farklı yazılıyor. Bir analist 'en
> uygun konut finansmanı hangisi' sorusu için on ayrı siteyi elle tarıyor.
>
> Biz bu metinleri kanıtlanabilir veriye çeviriyoruz, on bankayı tek tabloda
> karşılaştırılabilir kılıyoruz ve bunu bankanın kendi sunucusunda yapıyoruz."

⏱️ *Burada durma, hemen geç. Problemi herkes zaten biliyor.*

---

## Slayt 2 — Hibrit çıkarım mimarisi · **40 sn**

**Görsel:** Tek akış şeması:
`Ham metin → [1] Kural tabanlı (deterministik) → [2] LLM tamamlayıcı → Yapılandırılmış JSON`
Kenarda kırmızı anahtar: `FINAGENT_LLM=0` → sadece katman 1.
Altta küçük bir şerit: `%2,05` · `% 2.05` · `yüzde 2,05` → **2.05**

**Ekranda:**
- **Katman 1:** ~2.000 satır Türkçe morfoloji farkındalıklı kural — deterministik, açıklanabilir, **dış ağ gerektirmez**
- **Katman 2:** LLM yalnızca kuralın boş bıraktığı alanlarda devreye girer
- Normalizasyon: para · oran · vade · tarih → tek standart biçim

**Konuşma notu:**
> "Neden hibrit? Kâr payı oranı gibi bir alanda halüsinasyon kabul edilemez.
> Kural katmanı bunu deterministik çıkarıyor — aynı metin her zaman aynı sonuç.
> LLM sadece kuralın yakalayamadığı serbest ifadelerde devreye giriyor.
>
> Kritik nokta: LLM'i tamamen kapatsak bile sistem çalışmaya devam ediyor.
> Bu, birazdan göstereceğim kurum içi iddiasının temeli."

⏱️ *Türkçe tuzaklarını burada anlatma — yedek slaytta duruyor.*

---

## Slayt 3 — ⭐ Çıkarım Kanıtları · **40 sn**

**Görsel:** `/campaigns` alt panelinin ekran görüntüsü — kanıt tablosu net
okunacak şekilde büyütülmüş.

**Ekranda:**
> "Sistemin her değeri metindeki **hangi ifadeden** ve **hangi yöntemle**
> çıkardığını görün."

| Alan | Metindeki ifade | Değer | Yöntem | Güven |
|---|---|---|---|---|
| kar_payi_orani | "%2,87 'den başlayan kâr oranları" | 2.87 | REGEX | 0.94 |

**Konuşma notu — SUNUMUN EN ÖNEMLİ 40 SANİYESİ:**
> "Şunu özellikle vurgulamak istiyoruz. Çoğu NLP çözümü size bir sonuç verir ve
> 'güven bana' der. Biz her değerin **kaynağını** gösteriyoruz: metnin hangi
> ifadesinden, hangi yöntemle, ne güvenle çıkarıldı.
>
> Bir banka için bu süs değil zorunluluk. Yanlış bir kâr payı oranı müşteriye
> yansırsa denetim ekibi 'bu sayı nereden geldi' diye soracak. Bizde cevabı bir
> tık uzakta.
>
> Ekrandaki örnek gerçek bir Albaraka metni — kesme işaretinden önce boşluk var,
> standart bir regex burada tökezler."

---

## Slayt 4 — Ölçülmüş başarı · **35 sn**

**Görsel:** Solda dev punto **%99,3**, sağda kompakt yakalama tablosu.

**Ekranda:**

**Kesinlik %99,3** — 599 kayıtta 4 kusur

| Alan grubu | Yakalama |
|---|---:|
| kâr payı · vade · taksit · tutar · ödül · nakit iade | **%100** |
| bitiş tarihi | %93 |

*Ölçüm araçları boru hattına gömülü — her çalıştırmada yeniden koşuyor.*

**Konuşma notu:**
> "Bu sayıları iddia etmiyoruz, ölçüyoruz — üstelik ölçüm araçları boru hattının
> içinde, her çalıştırmada otomatik koşuyor.
>
> İki yönden bakıyoruz: çıkardığımız değer metinde gerçekten var mı, ve metinde
> gösterge varken alanı boş mu bıraktık? Yedi alanın altısında kaçak sıfır."

⏱️ *"Kâr payı neden 10 kampanyada" sorusu gelirse yedek slayt Y2'ye geç.*

---

## Slayt 5 — Ürün · **45 sn**

**Görsel:** Üç ekran görüntüsü tek slaytta — dashboard (radar), chatbot (iki
persona yan yana), finansman tablosu (ortalama okları görünür).

**Ekranda:**
- **Pazar Analizi:** 7 kriterde lider kampanyalar · sektör radarı · PNG/Excel/PDF
- **Çift persona chatbot:** müşteri sade dil ↔ analist pazar payı ve rakip boşluğu
- **Finansman/Katılım:** ortalamaya göre ok göstergeleri; taksit **hesaplanmıyor**, bankanın yayımladığı değer kullanılıyor

**Konuşma notu:**
> "Analistin ekranı: şartname 5.7'de sayılan karşılaştırma kriterlerinin tamamı
> kart olarak duruyor.
>
> Chatbot'ta aynı veri iki dille anlatılıyor — müşteriye 'pazar payı %13,4'
> demenin anlamı yok, analiste 'çok avantajlı' demenin de.
>
> Bir şeyi özellikle söyleyeyim: taksit tutarlarını biz hesaplamıyoruz. Banka ne
> yayımladıysa onu gösteriyoruz. Formül uygulamak gerçek veriyi tahminle
> değiştirmek olurdu."

⏱️ *Bu slaytta üç ürünü de saymaya çalışma; video zaten gösterecek.*

---

## Slayt 6 — ⭐ On-Premise: iddia değil kanıt · **40 sn**

**Görsel:** Üstte şartname 5.9'un dört maddesi ve dört yeşil tik. Altta gerçek
terminal çıktısının ekran görüntüsü.

**Ekranda:**

| Şartname 5.9 | Durum |
|---|---|
| Kurum içi sunucuda çalıştırılabilir | ✅ |
| Veri güvenliği | ✅ Ticari LLM sağlayıcı yok |
| Verilerin kurum dışına çıkmaması | ✅ |
| Dış servise bağımlı olmadan çalışma | ✅ |

**Dış ağ tamamen engelliyken:**
```
%1,89 kâr payı oranı          → kar_payi_orani = 1.89
31 Aralık 2026 tarihine kadar → bitis_tarihi   = 2026-12-31
konut finansmanı fırsatı      → kampanya_turu  = konut_finansmani
```

**Konuşma notu:**
> "Burada 'çalışır' demiyoruz, gösteriyoruz. Python'un ağ katmanını yamaladık;
> localhost dışına çıkan her bağlantı hata veriyor. Sonra şartnamenin **kendi
> örnek metnini** işledik. Sonuç ekranda: tek bir dış çağrı yapılmadan hepsi
> doğru çıkarıldı.
>
> Kurum içi moda geçmek kod değişikliği gerektirmiyor; LLM, embedding ve vektör
> adreslerinin üçü de ortam değişkeni. Bir banka için bu pazarlama cümlesi
> değil, satın alma şartı."

---

## Slayt 7 — Kapanış ve yol haritası · **10 sn**

**Görsel:** Slayt 1'deki üç kelimenin tekrarı + takım adı + QR (depo/demo).

**Ekranda:**
> **Kanıtlanabilir · Karşılaştırılabilir · Kurum içi**
>
> 599 kampanya · %99,3 kesinlik · 0,2 sn ilk yanıt · sıfır dış bağımlılık
>
> **Sıradaki:** finansman kapsamını 10 bankaya çıkarmak · geçmiş veriden
> sezonsal kampanya açığı analizi

**Konuşma notu:**
> "Kapsam eksiğimizi biliyoruz, sıradaki işimiz o. Teşekkürler."

⏱️ *Burada durma. Soru-cevaba geç.*

---

# METRİK KÜNYESİ — üç bölümün tüm sayıları

> Bu bölüm slaytta **olduğu gibi gösterilmez.** Amacı iki şey: (1) slaytlardaki
> her sayının nereden geldiğini tek yerde tutmak, (2) jüri "peki kaç kayıt,
> hangi aralıkta" diye sorduğunda anında cevap verebilmek.
>
> Tüm değerler çalışan sistemden canlı çekildi. Veri güncellenirse bu tablolar
> da yenilenmeli.

---

## A. KAMPANYA — 599 kayıt · 9 banka

### A1. Banka dağılımı

| Banka | Kampanya | Pay |
|---|---:|---:|
| Ziraat Katılım | 209 | %34,9 |
| Kuveyt Türk | 107 | %17,9 |
| TOM Katılım | 86 | %14,4 |
| Emlak Katılım | 67 | %11,2 |
| Albaraka Türk | 48 | %8,0 |
| Dünya Katılım | 45 | %7,5 |
| Vakıf Katılım | 24 | %4,0 |
| Hayat Finans | 11 | %1,8 |
| Türkiye Finans | 2 | %0,3 |
| Adil Katılım | 0 | — |

### A2. Çıkarılan finansal alanlar

| Alan | Dolu kayıt | En düşük | En yüksek | Ortalama |
|---|---:|---:|---:|---:|
| Kâr payı oranı | 8 | %1,99 | %4,99 | %3,19 |
| Vade (ay) | 73 | 2 | 60 | 12,0 |
| Finansman tutarı | 49 | 1.000 TL | 1.000.000 TL | 97.286 TL |
| Taksit sayısı | 273 | 2 | 36 | 6,3 |
| Ödül tutarı | 219 | 25 TL | 150.000 TL | 3.968 TL |
| Nakit iade oranı | 41 | %1 | %75 | %16,0 |
| MGM kişi başı kazanç | 9 | 500 TL | 22.000 TL | 5.806 TL |
| Tahsis ücreti | 6 | 4,20 TL | 75 TL | 28,53 TL |

> **Jüri sorarsa:** "Kâr payı neden sadece 8 kampanyada?" → 599 kampanyanın
> 484'ü kart kampanyası; bunlar tanım gereği oran yayımlamaz. Oranlar finansman
> ürünlerinde ve orada 48 kaydın 47'si dolu. Geri çağırma testi metinde oran
> göstergesi olan **8 kampanyanın 8'inde de** yakaladığımızı gösteriyor (%100).

### A3. Kampanya türü sınıflandırması (12 tür)

| Tür | Adet |
|---|---:|
| Kart kampanyası | 484 |
| Alışveriş puanı | 31 |
| İndirim kampanyası | 17 |
| Finansman (diğer) | 16 |
| MGM kampanyası | 15 |
| Yatırım ürünü | 8 |
| Hediye/promosyon | 7 |
| Yeni müşteri | 7 |
| İhtiyaç finansmanı | 6 |
| Taşıt finansmanı | 4 |
| Konut finansmanı | 1 |
| Belirlenemedi | 3 |

**Sınıflandırma başarısı: 596/599 = %99,5**

### A4. Dashboard'daki 7 lider kampanya kriteri

`Düşük Kâr Payı` · `Yüksek Ödül` · `Uzun Vade` · `Düşük Masraf` ·
`Yüksek Limit` · `MGM Davet` · `Nakit İade`

Şartname 5.7'nin saydığı kriterlerin tamamını kapsıyor.

---

## B. FİNANSMAN ÜRÜNLERİ — 48 kayıt · 4 banka

Bankalar: Albaraka Türk · Dünya Katılım · Vakıf Katılım · Ziraat Katılım

### B1. Ürün bazında kâr oranı aralıkları ⭐ **SLAYTA EN UYGUN TABLO**

| Ürün | Kayıt | En düşük | En yüksek | Ortalama |
|---|---:|---:|---:|---:|
| **Konut finansmanı** | 10 | **%2,90** | %3,19 | %3,01 |
| **Taşıt finansmanı** | 6 | **%3,21** | %3,39 | %3,32 |
| **İhtiyaç finansmanı** | 32 | **%3,90** | %4,99 | %4,24 |

> Bu tablo bir slaytta tek başına durabilir: üç ürün, üç bant, aralarındaki fark
> net görünüyor. "Karşılaştırılabilir hale getirmek" iddiasının en somut kanıtı.

### B2. Tüm finansman metrikleri

| Metrik | Dolu | En düşük | En yüksek | Ortalama |
|---|---:|---:|---:|---:|
| Kâr oranı | 47/48 | %2,90 | %4,99 | %3,88 |
| Vade | 48 | 12 ay | **120 ay** | 42,3 ay |
| Finansman tutarı | 48 | 50.000 TL | 2.000.000 TL | 433.333 TL |
| Aylık taksit | 48 | 3.058,76 TL | 65.308,18 TL | 19.085,56 TL |
| Toplam geri ödeme | 48 | 68.411,05 TL | 7.836.981,60 TL | 1.311.711,31 TL |
| Tahsis ücreti | 12 | 287,50 TL | 10.000,00 TL | 2.040,62 TL |

> **Kritik vurgu:** Aylık taksit ve toplam geri ödeme **hesaplanmıyor** —
> bankaların yayımladığı gerçek değerler. Formül uygulamak gerçek veriyi
> tahminle değiştirmek olurdu. Bu, sunumda söylenmesi gereken bir cümle.

### B3. Ek çıkarılan alanlar (şartname tablosunun ötesinde)

`tahsis_ucreti` · `ipotek_tesis_ucreti` · `ekspertiz_ucreti` · `urun_kodu` ·
`guncellenme_tarihi`

---

## C. KATILIM HESABI — 4 kayıt · 2 banka

Bankalar: Vakıf Katılım · Ziraat Katılım
Vadeler: `1 Ay Vadeli` · `32 gün / 1 Ay` — Tutarlar: 100.000 TL · 250.000 TL

### C1. Getiri metrikleri

| Metrik | En düşük | En yüksek | Ortalama |
|---|---:|---:|---:|
| Brüt kâr payı oranı | %28,00 | %31,50 | %29,75 |
| Net kâr payı oranı | %23,10 | **%25,99** | %24,55 |
| Brüt getiri | 2.377,67 TL | 6.687,90 TL | 4.421,23 TL |
| Net getiri | 1.961,57 TL | 5.517,51 TL | 3.647,51 TL |
| Vade sonu toplam | 101.961,57 TL | 255.517,51 TL | 178.647,51 TL |

### C2. Anlatılacak fark

Stopaj kesintisi ayrı bir alan olarak tutuluyor: brüt ile net arasındaki fark
kullanıcıya açıkça gösteriliyor. 100.000 TL / 1 ay örneğinde Vakıf Katılım
brüt %31,50 → net %25,99; yani müşterinin cebine giren 2.207,01 TL.

> **Jüri sorarsa:** "Neden sadece 2 banka?" → Katılım hesabı hesaplayıcısı
> yayımlayan banka sayısı sınırlı; kazıyıcı mimarisi banka başına modüler,
> kapsam genişletmek yeni modül yazmak demek, mimari değiştirmek değil.

---

## D. Sunumda kullanılacak "en güçlü tek sayılar"

Slaytlarda ve konuşmada tekrarlanacak çekirdek sayılar. Fazlasını ezberlemeye
çalışmayın; bu sekizi yeter.

| Sayı | Ne anlatıyor | Hangi slayt |
|---|---|---|
| **599** | Toplanan kampanya | 1 |
| **10** | BDDK listesindeki banka | 1 |
| **%99,3** | Çıkarım kesinliği | 4 |
| **%100** | 7 alanın 6'sında yakalama | 4 |
| **%2,90 – %4,99** | Finansman oran bandı (üç üründe) | 5 |
| **120 ay** | En uzun vade (konut) | 5 |
| **0,2 sn** | Chatbot ilk yanıt | 5 |
| **0** | Kurum içi modda dış çağrı | 6 |

---

## E. Metriklerin slaytlara dağılımı

Aşağıdaki üç ek, mevcut 7 slaytlık akışı **bozmadan** yerleştirilebilir:

| Slayt | Eklenecek metrik | Nasıl |
|---|---|---|
| Slayt 1 | 599 kampanya · 9 bankada veri · 12 kampanya türü | Alt şeride tek satır |
| Slayt 4 | A2 tablosundan 3 satır (kâr payı, ödül, nakit iade) | Yakalama tablosunun yanına |
| Slayt 5 | **B1 tablosunun tamamı** | Ekranın sol yarısı — en güçlü görsel |

> **Uyarı:** 4 dakikada bu tabloların hiçbiri okunmaz. Slayta koyulacaksa
> yalnızca **B1** konsun (üç satır, üç sütun); gerisi yedek slayt ve konuşma
> malzemesi olarak kalsın. Slayt tasarımının birinci kuralı: slayt başına tek
> fikir.

---

# YEDEK SLAYTLAR (yalnızca soru gelirse)

## Y1 — "Türkçe için özel ne yaptınız?"

| Tuzak | Sonuç | Çözüm |
|---|---|---|
| `"İ".lower()` → `i` + U+0307 | Regex'ler sessizce eşleşmiyor | Özel küçültme fonksiyonu |
| Eklemeli morfoloji ("kâr payına", "vadesi") | Kök eşleşmesi kaçıyor | Kurallarda son ek toleransı |
| `32.648,38` | Standart çevrim 32,64 veriyor | Binlik/ondalık ayracı ayrımı |

## Y2 — "Kâr payı neden sadece 10 kampanyada dolu?"

599 kampanyanın büyük çoğunluğu kart, alışveriş ve promosyon kampanyası —
bunlar tanım gereği kâr payı oranı yayımlamaz. Oranlar finansman ürünlerinde:
48 kaydın neredeyse tamamı dolu. Geri çağırma testi bunu doğruluyor: metinde
oran göstergesi olan 8 kampanyanın 8'inde de yakaladık. Yani çıkarım eksiği
değil, sektörün veri yayımlama biçimi.

## Y3 — "Veri kapsamınız neden eksik?"

Kampanya verisi 9 bankada (Adil Katılım sitesinde yayımlanmış kampanya yok,
Türkiye Finans'ta 2 tane). Finansman ürünü 4, katılım hesabı 2 bankada.
Kazıyıcı mimarisi banka başına modüler; kapsam genişletmek yeni modül yazmak,
mimari değiştirmek değil.

## Y4 — "Performans nedir?"

| Ölçüm | Değer |
|---|---|
| API sıcak yanıt | 4–9 ms |
| Sohbette ilk token | 0,12–0,20 sn |
| Mongo okuma (500 kayıt) | 4,7 ms medyan |
| Kampanya sayfası DOM | 1.240 öğe (pencereleme öncesi 10.403) |

---

# CANLI DEMO SORULARI

Jüri "chatbot'u deneyelim" derse. **Hepsi test edildi, çalışıyor.**

| # | Mod | Soru | Neden bu |
|---|---|---|---|
| 1 | Müşteri | *"Ziraat Katılım'ın konut finansmanı kâr payı oranı ne?"* | Şartname Senaryo 1'in birebir karşılığı |
| 2 | Analist | *"Albaraka mı daha avantajlı, Dünya Katılım mı?"* | Şartname Senaryo 2'nin **birebir yazımı** |
| 3 | Analist | *"En düşük kâr payı oranına sahip finansman hangi bankada?"* | Şartname 5.7 kriteri |
| 4 | Analist | *"En uzun vade seçeneği sunan finansman hangisi?"* | Şartname 5.7 kriteri |
| 5 | Müşteri | *"Vakıf Katılım'ın 100.000 TL katılım hesabı net getirisini diğer bankalarla karşılaştır"* | Mevduatın krediyle karıştırılmadığını gösterir |

> **Uyarı:** Demo öncesi Redis önbelleğini temizleyin ki cevaplar canlı üretilsin
> ve jüri "önceden hazırlanmış mı" diye şüphelenmesin.

---

# PROVA VE KONTROL LİSTESİ

**Prova disiplini:** 4 dakika kısa. En az üç kez kronometreyle prova edin.
Aşan kısım her seferinde Slayt 5'ten kısılsın (video zaten onu gösteriyor).

- [ ] Kronometreli prova ≤ 3 dk 50 sn (10 sn pay bırakın)
- [ ] Dört konteyner ayakta ve `healthy`
- [ ] Redis önbelleği temizlendi
- [ ] Beş demo sorusu bir kez denendi
- [ ] Kurum içi mod terminal çıktısı ekran görüntüsü slayt 6'da
- [ ] Çıkarım Kanıtları panelinde dolu bir kampanya seçili bırakıldı
- [ ] İnternet kesilirse diye demo videosu yerelde hazır
