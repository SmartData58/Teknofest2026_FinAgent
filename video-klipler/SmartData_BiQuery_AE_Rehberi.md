# SmartData BiQuery — After Effects MCP Kurgu ve Render Rehberi

Bu doküman, Claude ve `Dakkshin/after-effects-mcp` entegrasyonu kullanılarak "SmartData BiQuery" projesinin ekran kaydı tabanlı TEKNOFEST tanıtım videosunun kurgusunu, görsel efektlerini (vurgular, zoom, geçişler) ve metin animasyonlarını oluşturmak için gerekli tüm talimatları içermektedir.

Videonun amacı: Jüriyi **"Bu sistem şartnameye tam uyumlu, tutarlı bir şekilde çalışıyor ve her çıkarımını kanıtlayabiliyor"** gerçeğine 70 saniye içinde ikna etmektir.

---

## 1. Genel Sanat Yönetimi ve Sekans / Proje Ayarları

*   **Sekans (Sequence / Composition) Ayarı:** **1080p @ 30 fps** (`1920×1080` çözünürlük, `30.00 fps` kare hızı, `Square Pixels 1.0`, `Progressive`). Ekran kayıtları ve final render çıktısıyla tam 1-e-1 uyum için sabittir.
*   **Temel Renk Paleti (Açık Tema - Sahneler 1-6):**
    *   **Alt Bant (Lower Thirds) Arka Planı:** Koyu Lacivert/Kurumsal Mavi (`#0A192F`) veya Yarı saydam siyah (`#000000`, %70 Opacity).
    *   **Metin (Typography):** Saf Beyaz (`#FFFFFF`). Font: Roboto, Inter veya Segoe UI.
    *   **Vurgu (Highlight) Rengi:** Fosforlu Sarı (`#FFE600`). Mode: `Multiply` (Çoğalt).
*   **Temel Renk Paleti (Koyu Tema - Kapanış Sahnesi):**
    *   **Arka Plan:** Koyu Antrasit/Siyah (`#121212` veya `#0A0A0A`).
    *   **Metin:** Beyaz (`#FFFFFF`) ve Kurumsal Mavi Vurgular.
*   **Hareket Dinamiği (Motion):** Gösterişten uzak, net, profesyonel. Kamera (Zoom) hareketlerinde `Easy Ease` (F9) ile yumuşak duruşlar. Ekran yazılarında basit `Fade In/Out`.

---

## 2. After Effects MCP (Dakkshin) Kullanım Yönergeleri

Claude, bu projede ekran kayıtlarını (Footage) işlemek ve üzerine motion graphics eklemek için şu komutları kullanmalıdır:

*   **`create-composition`**: `width: 1920, height: 1080, frameRate: 30` ile ana kurgu kompozisyonunu oluşturmak için.
*   **`setLayerProperties`**:
    *   Ekran kayıtlarının (video dosyalarının) `startTime` (başlangıç) ve görünürlük sürelerini (trim) ayarlamak için.
    *   Sahne 2'deki gibi videoya **Zoom in/out** yapmak için video katmanının `scale` ve `position` değerlerine müdahale etmek için.
    *   Alt yazılar için zemin (Shape Layer) opasitelerini ayarlamak için.
*   **`setLayerKeyframe`**: Sarı vurgu (Highlight) animasyonları ve ekran içi kamera (Scale/Position) yakınlaştırmaları için yumuşak keyframe'ler (Ease In/Out) atamak için.
*   **`run-script`**: Şekil katmanlarının (Shape Layers) Blend Mode'unu (Harmanlama Modu) `Multiply` yapmak, metinlere `Drop Shadow` eklemek veya Gaussian Blur uygulamak gibi gelişmiş özellikler için ExtendScript (JSX) çalıştırmak için.

---

## 3. Sahne Sahne Kurgu ve Animasyon Akışı (Timeline)

> **ÖNEMLİ KURAL:** Aşağıdaki tüm sahnelerde, belirtilen "Ekran Yazısı" metinleri, ekranın sol alt köşesine (jürinin UI'ı görmesini engellemeyecek bir "Safe Zone"a) kurumsal, yarı saydam bir zemin üzerinde `Fade In/Fade Out` (%0 -> %100 -> %0) animasyonu ile eklenecektir.

### Sahne 1 — Problem (00:00–00:08)
*   **Görüntü (Footage):** Üç banka sitesi arası hızlı geçiş.
*   **AE & MCP Görevi (Sarı Vurgu):**
    *   Ekranda kâr payı oranlarının geçtiği yerlere (`%1,89`, `% 1.89`, `yüzde 1,89`) bir `Shape Layer` (Rectangle) çiz.
    *   Rengini `#FFE600` yap. `run-script` ile Blend Mode'unu `Multiply` yap.
    *   `setLayerKeyframe` ile X eksenindeki `Scale` değerini %0'dan %100'e (soldan sağa çiziliyormuş gibi) anime et.
*   **Ekran Yazısı:** `10 banka · 599 kampanya · her biri farklı format`

### Sahne 2 — Çıkarım ve Kanıt (00:08–00:20) [VİDEONUN KALBİ]
*   **Görüntü (Footage):** `/campaigns` sayfasında Albaraka seçilir, Çıkarım Kanıtları paneli açılır.
*   **AE & MCP Görevi (Kamera Zoom):**
    *   Alt panel açıldığı anda video katmanının `Scale` değerini `setLayerKeyframe` ile %100'den %125'e çıkart.
    *   Eşzamanlı olarak `Position` değerini alt paneli (Çıkarım Kanıtları) ortalayacak şekilde kaydır.
    *   Hareket `Ease Out` ile yumuşakça dursun. Jürinin okuyabilmesi için zoom halinde sabit kalsın.
*   **Ekran Yazısı:** `Her değerin kaynağı görünür`

### Sahne 3 — Dashboard (00:20–00:30)
*   **Görüntü (Footage):** `/dashboard` ekranında filtreleme, aşağı kaydırma ve PDF raporlama çıktısı.
*   **AE & MCP Görevi:** Akıcı kurgu, görüntüye müdahale yok. Sadece metin animasyonu eklenir.
*   **Ekran Yazısı:** `Dinamik Dashboard · Tier 1 Analizi · Anlık PDF Raporlama`

### Sahne 4 — Finansman & Katılım (00:30–00:42)
*   **Görüntü (Footage):** `/finansman` tablosundaki yön okları (tooltip hover) ve `/katilim-hesap` ekranı gösterilir.
*   **AE & MCP Görevi:**
    *   Kullanıcı yön okunun (tooltip) üzerinde durduğunda, vurguyu artırmak için etrafı çok hafif karart (Opacity'si düşük siyah bir maske veya Adjustment Layer ile).
*   **Ekran Yazısı (İlk 6 sn):** `Finansman Karşılaştırması · Sektör Ortalaması ve Yön Göstergeleri`
*   **Ekran Yazısı (Son 6 sn):** `Katılım Hesabı · FinAgent AI Chat Entegrasyonu`

### Sahne 5 — Karşılaştırma / Chatbot (00:42–00:54)
*   **Görüntü (Footage):** `/chat` ekranında sorular yazılır, tablolar/yorumlar akar. Excel çıktısı alınır.
*   **AE & MCP Görevi:** UI arayüzü çok detaylı olduğu için metinlerin üstü kesinlikle kapanmamalıdır. Temiz bir alt bant eklenir.
*   **Ekran Yazısı:** `Doğal Dil Analizi · Metrikler & Öneriler · Anlık Excel Çıktısı`

### Sahne 6 — Kurum İçi Kanıt / Terminal (00:54–01:02)
*   **Görüntü (Footage):** Tam ekran Terminal kaydı (Dış ağ kapalı çıkarım logları).
*   **AE & MCP Görevi:** Terminal siyah ekran olduğu için, ekran üstü yazısının zeminini kaldır veya yüksek kontrast sağlayacak ince beyaz bir çizgi (stroke) ile destekle. Görüntüyü sabit tut.
*   **Ekran Yazısı:** `Dış ağ kapalı — çıkarım aynı doğrulukla çalışıyor`

### Sahne 7 — Kapanış (01:02–01:10)
*   **Görüntü (Footage):** Karanlık Tema (Dark Mode) açık olan Index (`/`) sayfasına geçiş.
*   **AE & MCP Görevi (Tipografi ve Bitiş):**
    *   Arka plan videosuna `Gaussian Blur` ekleyerek (run-script ile) netliğini boz.
    *   Ekranın ortasına büyük/kalın fontlarla sırayla üç kelimeyi `Fade In` ve hafif `Scale` (YUKARI) ile getir:
        1. **Kanıtlanabilir** (0.5s bekle)
        2. **Karşılaştırılabilir** (0.5s bekle)
        3. **Kurum içi**
    *   Hemen altına daha küçük bir fontla alt başlık `Fade In` ile girer: `599 kampanya · %99,3 kesinlik · sıfır dış bağımlılık`
    *   En alt kısma TEKNOFEST ve BiQuery logolarını yerleştir (`Opacity` %0 -> %100).

---

## 4. Şartname Uyum Kontrolü (Jüri Odağı)

Kurgu esnasında aşağıdaki maddelerin ekranda net okunabildiğinden emin ol (Zoom veya süre uzatma gerekirse inisiyatif kullan):

| İstenen | Hangi Sahnede | Kontrol Edilecek Detay |
|---|---|---|
| Kullanıcı arayüzü | Sahne 2, 3, 4, 5 | Arayüz temiz mi? Yazılar kapanmış mı? |
| Dashboard | Sahne 3 | Grafiklerin yüklenişi net görülüyor mu? |
| Chatbot | Sahne 4, 5 | Prompt ve dönen cevap okunuyor mu? |
| Metin girdisi verilmesi | Sahne 2, 5 | Input kutusu kadrajda mı? |
| Yapılandırılmış çıktı | Sahne 2 | Çıkarım paneli zoomu yeterli mi? |
| Karşılaştırma sonuçları | Sahne 3, 4, 5 | Oklar ve tablolar algılanıyor mu? |

---

## 5. Claude İçin Teknik Kurgu Notları

*   **Zamanlama (Sync):** Video birleştirme işleminde, metin katmanlarının (`inPoint` ve `outPoint` değerleri) verilen senaryo saniyeleriyle birebir eşleşmesine dikkat et.
*   **Minimalizm:** Bu bir yazılım demosu, sinematik bir fragman değil. Jüri UI'ı görmek ister. Alt bantları her zaman ekranın alt %15'lik kısmına "Safe Zone"a yerleştir.
*   **Vurgular:** Sahne 1'deki `Multiply` (Sarı marker efekti) opaklığını %80-90 civarında tut, altındaki siyah metnin kontrastını bozmasına izin verme.