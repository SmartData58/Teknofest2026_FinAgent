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
