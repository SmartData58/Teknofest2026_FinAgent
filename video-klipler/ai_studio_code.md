# SmartData BiQuery — Kapsamlı After Effects MCP Kurgu & Render Kılavuzu

> **Sekans ve Render Standardı:** **1080p @ 30 fps** (`1920×1080` Full HD çözünürlük, `30.00 fps` kare hızı, `Square Pixels 1.0`, `Progressive`). Çekilen ham kayıtlar, AE kompozisyonları ve final render çıktısı kesinlikle bu formatta olmalıdır.

Bu doküman, TEKNOFEST jürisine sunulacak "SmartData BiQuery" ekran kaydı tanıtım videosunun, After Effects MCP (`Dakkshin/after-effects-mcp`) kullanılarak nasıl kurgulanacağını belirler. 

**Videonun Temel Tasarım Felsefesi (Hibrit Stil):**
Bu video, düz bir ekran kaydı birleştirmesi DEĞİLDİR. İki farklı üst düzey teknoloji tanıtım stilinin karmasıdır:
1.  **Aydınlık & Minimalist UI Stili (Sahneler 1-7):** Apple/LangEase tarzı saf beyazlar, parlak kurumsal maviler, hızlı zıplayan (bounce) tipografiler, temiz cam efektli (frosted glass) alt bantlar ve yumuşak 3D uzay yakınlaştırmaları. Ekran kayıtları 3D uzayda hafif eğimli paneller olarak sunulur.
2.  **Karanlık, Neon & Glassmorphism Stili (Sahneler 8-9):** NeuraFlow tarzı derin lacivert arka planlar, elektrik mavisi/mor parlamalar (glow), yüzen (floating) UI elementleri, hologram hissi ve sinematik karanlık tema geçişleri.

---

## BÖLÜM 1: Dakkshin After Effects MCP Komut Referansı

Claude, projeyi inşa ederken aşağıdaki MCP araçlarını ve parametrelerini kesinlikle bu kurallara göre kullanmalıdır:

### 1. Temel Proje ve Kompozisyon Yönetimi
*   **`create_composition`**: 1080p 30fps ana kompozisyon açar.
    *   *Parametreler:* `name` (String), `width` (1920), `height` (1080), `frameRate` (30), `duration` (Saniye cinsinden).
*   **`import_file`**: Ekran kayıtlarını (footage) ve logoları projeye dahil eder.
    *   *Parametreler:* `filePath` (Dosya yolu).
*   **`add_item_to_comp`**: İçe aktarılan veya oluşturulan bir öğeyi zaman çizelgesine yerleştirir.

### 2. Katman (Layer) Özellikleri ve Animasyon
*   **`set_layer_property`**: Katmanların temel transform özelliklerini ayarlar.
    *   *Hedefler:* `Position`, `Scale`, `Rotation` (X, Y, Z), `Opacity`, `Anchor Point`.
*   **`add_keyframe`**: Yumuşak geçişler (Easing) oluşturmak için kullanılır.
    *   *Parametreler:* `layerName`, `propertyName`, `time` (saniye), `value`, `easeType` (Kesinlikle `Ease In/Out` veya `Bezier` kullanılmalı, hareketler robotik olmamalıdır).
*   **`set_layer_3d`**: Bir katmanı 3D uzaya taşır. Hibrit stilde ekran kayıtlarını hafif açılı göstermek için (örn: `Y Rotation: -15`) zorunludur.

### 3. Efektler ve Gelişmiş Şekillendirme
*   **`apply_effect`**: Katmana AE efekti ekler.
    *   *Kullanılacak Efektler:* 
        *   `Drop Shadow` (Aydınlık sahnelerde panellerin altına yumuşak gölge için).
        *   `Gaussian Blur` (Cam efekti/Glassmorphism arka planlarını bulandırmak için).
        *   `Glow` (Karanlık sahnelerde neon metinler ve terminal vurguları için).
*   **`add_expression`**: Sürekli animasyonlar için.
    *   *Kullanım:* Yüzen (floating) ekran hissi için Position'a `wiggle(0.5, 10)`, dönen arka plan auraları için Rotation'a `time*15`.
*   **`execute_jsx` (ExtendScript):** MCP'nin standart komutlarıyla yapılamayan karmaşık işlemler (Shape layer çizimi, Blend Mode'u "Multiply" yapma, maskeleme, "Trim Paths" ekleme) için doğrudan JavaScript for After Effects kodları çalıştırmak için kullanılır.

---

## BÖLÜM 2: Sahne Sahne Hibrit Kurgu Akışı

> **GENEL KURAL:** Ekran kayıtları yatay/dikey kaydırma (scroll) İÇERMEYECEK şekilde, yüksek çözünürlükte statik olarak çekilmiştir. Hareket, After Effects'teki 3D Kamera ve katman manipülasyonlarıyla (Pan/Tilt/Zoom) sağlanacaktır. Tüm alt yazılar ekranın sol altına, arkası bulanıklaştırılmış (Glassmorphism) yuvarlak hatlı bir panel (Shape Layer) içine yerleştirilecektir.

### Sahne 1 — Problem (00:00–00:08) | Stil: Aydınlık / Hızlı Kesme
*   **Görüntü:** 3 farklı bankanın yüksek çözünürlüklü kampanya sayfaları.
*   **AE Animasyonu:**
    *   Sayfalar ekrana 3D olarak hafifçe geriden öne doğru zıplayarak (Bounce/Scale) gelir.
    *   **Vurgu:** Kâr payı oranlarının üzerine (`%1,89` vb.) `execute_jsx` ile sarı (`#FFE600`) bir Shape Layer (Rectangle) çizilir. Blend Mode `Multiply` yapılır. `Scale X` %0'dan %100'e hızlıca anime edilerek "fosforlu kalemle çizme" hissi verilir.
*   **Metin Animasyonu:** "10 banka", "599 kampanya", "farklı format" kelimeleri LangEase stilinde merkeze hızlı Jump Cut'lar ve sürekli büyüyen (Continuous Scale) formda gelir, sonra sol alta (alt banta) küçülerek oturur.

### Sahne 2 — Çıkarım ve Kanıt (00:08–00:20) ⭐ VİDEONUN KALBİ
*   **Görüntü:** `/campaigns` sayfasında Albaraka seçilir, Çıkarım Kanıtları paneli açılır.
*   **AE Animasyonu:**
    *   Görüntü 3D uzayda tam karşıdadır. Alt panel açıldığında, bir `Camera` objesi veya `Null Object` kullanılarak `Position` ve `Scale` değerlerine yumuşak bir `Ease Out` animasyonu (Süre: 1.5 saniye) ile panele **Zoom In** yapılır.
    *   Panelin etrafına, dikkati çekmek için mavi, çok ince ve atan (pulse) bir Glow (Parlama) çerçevesi eklenir.
*   **Alt Bant Yazısı:** `Her değerin kaynağı görünür` (Cam efektli panel üzerinde belirir).

### Sahne 3 — Dashboard (00:20–00:30) | Stil: 3D Mekansal Kaydırma
*   **Görüntü:** `/dashboard` statik, devasa bir ekran kaydıdır. Scroll yoktur.
*   **AE Animasyonu:**
    *   Ekran kaydı kompozisyonda dikey olarak çok uzun bir katman olarak yerleştirilir. `set_layer_3d` aktif edilir.
    *   Kamera, sayfanın en üstünden (Tier 1 filtreleme) başlayıp, pürüzsüz bir `Position Y` animasyonu ile en aşağı (Grafiklere ve PDF indirme butonuna) doğru kayar. Bu, kullanıcının kaydırmasından çok daha profesyonel bir "Kamera Pan" hareketidir.
*   **Alt Bant Yazısı:** `Dinamik Dashboard · Tier 1 Analizi · Anlık PDF Raporlama`

### Sahne 4 & 5 — Finansman ve Katılım (00:30–00:52) | Stil: Fokuslanma
*   **Görüntü:** `/finansman` tablosundaki yön okları ve `/katilim-hesap` ekranı.
*   **AE Animasyonu:**
    *   Kullanıcı (fare imleci kapalıdır) yön okunun üzerine geldiğinde, AE'de okun bulunduğu bölge dışındaki tüm ekran `%30 Opacity` siyah bir `Solid` tabaka ile karartılır. Sadece okun olduğu alana aydınlık bir "Spot ışığı" (Mask) açılır.
    *   FinAgent ikonuna tıklanma anında (00:42), ikonun merkezinden dışa doğru büyüyen şeffaf bir mavi dalga (Ripple efekti) yayılır.
*   **Alt Bant Yazısı:** `Finansman Karşılaştırması · Sektör Ortalaması ve Yön Göstergeleri` -> `Katılım Hesabı · FinAgent AI Chat Entegrasyonu`

### Sahne 6 — Chatbot / Doğal Dil (00:54–01:06) | Stil: Apple Minimalizmi
*   **Görüntü:** `/chat` ekranında prompt yazılır, AI tablo döndürür.
*   **AE Animasyonu:** Chatbot arayüzü çok detaylıdır, bu yüzden kamerada ekstrem zoom yapılmaz. Ekrana "Excel Çıktısı" butonuna tıklandığında sol alttan LangEase stilinde küçük, şık bir "Dosya İndirildi" (Yeşil Check ikonu) 3D pop-up kartı uçarak girer ve kaybolur.
*   **Alt Bant Yazısı:** `Doğal Dil Analizi · Metrikler & Öneriler · Anlık Excel Çıktısı`

### Sahne 7 — Kurum İçi Kanıt (Terminal) (01:06–01:14) | Stil: NeuraFlow'a Geçiş
*   **Görüntü:** CLI/Terminal ekranı. (Karanlık temaya geçişin köprüsüdür).
*   **AE Animasyonu:**
    *   Ekran kaydının arkasına koyu lacivert/siyah gradient bir arka plan (`Solid` + `Ramp`) atılır.
    *   Terminal metni göründüğünde, yazılara çok hafif bir Cam Göbeği (Cyan) `Glow` efekti eklenir (Hacker/AI estetiği).
    *   Alt bant beyaz zemin yerine, parlak mavi kenarlıklı siyah cam (Dark Glassmorphism) bir zemine dönüşür.
*   **Alt Bant Yazısı:** `Dış ağ kapalı — çıkarım aynı doğrulukla çalışıyor`

### Sahne 8 — Kapanış (01:14–01:20) | Stil: Tam NeuraFlow / Dark Glassmorphism
*   **Görüntü:** Koyu Tema (Dark Mode) açık Index (`/`) sayfası.
*   **AE Animasyonu:**
    *   Arka plandaki video `Gaussian Blur` (Bluriness: 40) ile anında flu hale getirilir. Ekran karanlık, gizemli ve derin bir atmosfer kazanır.
    *   `execute_jsx` ile arka plana yavaşça dönen devasa bir mavi aura/ışık hüzmesi (`Fractal Noise` + `Tint` + `Screen` Mode) eklenir.
    *   Ekranın tam merkezinde, 3D uzaydan kameraya doğru 3 ana kelime (Buz beyazı, etrafı hafif mavi parlayan) sırayla, aralarında 0.5 saniye farkla uçarak (Scale/Opacity/Position Z) belirir:
        **KANITLANABİLİR**
        **KARŞILAŞTIRILABİLİR**
        **KURUM İÇİ**
    *   Kelimeler ekrana vururken arka planda hafif partiküller (CC Particle Systems) patlar.
    *   Bu metinlerin hemen altına soluk mavi renkte ince fontla `599 kampanya · %99,3 kesinlik · sıfır dış bağımlılık` yazısı yavaşça belirir.
    *   En alta TEKNOFEST ve BiQuery logoları, içten dışa doğru bir parlama (Glow flash) efektiyle çıkarak videoyu sonlandırır.

---

## BÖLÜM 3: Claude İçin Uygulama Kuralları

1.  **Zamanlama Senkronu:** Ekran kayıtlarının süresi senaryoda (Örn: 00:08 - 00:20) nettir. `add_keyframe` komutlarını atarken `time` değişkenlerini bu çizelgeye milisaniyesi milisaniyesine uydur.
2.  **Yüksek Çözünürlük Koruması:** `create_comp` oluştururken çözünürlüğü mutlaka 1920x1080 (veya kayıtlar 2K ise 2560x1440) tut. Ekran kayıtlarında "No Scroll" kuralı olduğu için, AE kamerasını kaydırırken sub-pixel (küsuratlı) position değerlerinden kaçın, titremeyi önlemek için `Math.round()` mantığıyla hareket et.
3.  **UI/UX Koruması:** Jürinin en çok görmek istediği şey projenin *kendisi*. AE ile eklediğin hiçbir 3D kart, parlama efekti veya alt bant; sistemin tablolarını, oklarını veya çıktı metinlerini **KAPATMAMALIDIR**. Alt bantlar ekranın alt %15'lik kısmına kilitlenmelidir.