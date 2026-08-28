# SmartData BiQuery — Video Çekim ve Render Kılavuzu

> **Süre:** 60 saniye (şartname: maksimum 5 dk, bizden istenen 1 dk).
> **Format:** Ekran kaydı. Yüz görüntüsü yok.
> **Çözünürlük & Ölçek:** Yüksek çözünürlük (1920×1080 / 2K), 30 fps. Tarayıcı tam ekran (F11), yer imleri gizli. **Kritik Kural:** Sayfalar dikey kaydırma (scroll) yapılmadan, yüksek çözünürlükte tüm bileşenleriyle **tek karede bir bütün olarak** çekilecektir.
>
> **Şartname 6. bölüm videoda şunların görünmesini istiyor:** kullanıcı arayüzü,
> dashboard, chatbot, metin girdisi verilmesi, modelin ürettiği yapılandırılmış
> çıktı, karşılaştırma sonuçları. **Altısı da aşağıdaki akışta mevcuttur.**

---

## Videonun Ana Amacı

Video, TEKNOFEST şartnamesine tam uyumlu, tutarlı ve profesyonel bir tanıtım videosu olarak 60 saniyede jüriyi şu temel gerçeğe ikna etmeyi hedefler:

> **"Bu sistem şartnameye tam uyumlu, tutarlı bir şekilde çalışıyor ve her çıkarımını kanıtlayabiliyor."**

Bu doğrultuda video rastgele bir "özellik turu" değil, **tutarlı bir ürün hikâyesi** sunar: dağınık metin giriyor → yapılandırılmış veri çıkıyor → karşılaştırılabilir hale geliyor → ve bunların hiçbiri için veri kurumdan dışarı çıkmıyor.

---

## Zaman Çizelgesi ve Video Dosya İsimleri

Kurgu ve montaj sürecinde karışıklığı önlemek için çekilen her sahne aşağıdaki dosya isimleriyle kaydedilmelidir:

| Zaman | Sahne | Video Dosya Adı (Klip) | Ekranda Ne Var |
|---|---|---|---|
| 00:00–00:08 | **Sahne 1 — Problem** | `sahne_01_problem.mp4` | Üç banka sitesi hızlı geçiş; aynı bilgi farklı yazımlarda sarı vurgu ile işaretleniyor |
| 00:08–00:20 | **Sahne 2 — Çıkarım + Kanıt** | `sahne_02_cikarim_kanit.mp4` | `/campaigns` → Albaraka seç → Çıkarım Kanıtları paneli & İşlenmiş Metin |
| 00:20–00:30 | **Sahne 3 — Dashboard** | `sahne_03_dashboard_pdf.mp4` | `/dashboard` → müşteri/çalışan modları, Tier 1, PDF çıktısı |
| 00:30–00:36 | **Sahne 4 — (Boş)** | `sahne_04_belirlenecek.mp4` | _(Belirlenecek)_ |
| 00:36–00:44 | **Sahne 5 — Finansman** | `sahne_05_finansman.mp4` | `/finansman` → müşteri/çalışan görünümü, yön okları tooltip |
| 00:44–00:54 | **Sahne 6 — Katılım & AI** | `sahne_06_katilim_chat.mp4` | `/katilim-hesap` → FinAgent logo tıkla → Chat metrik ve öneriler |
| 00:54–01:06 | **Sahne 7 — Chatbot & Excel** | `sahne_07_chatbot_excel.mp4` | `/chat` → Soru 1 (Çalışan), Soru 2 (Müşteri) + Excel rapor çıktısı |
| 01:06–01:14 | **Sahne 8 — Kurum İçi Kanıt** | `sahne_08_kurum_ici_kanit.mp4` | Terminal: ağ engelli çıkarım çıktısı |
| 01:14–01:20 | **Sahne 9 — Kapanış** | `sahne_09_kapanis_index_dark.mp4` | Dark mode Index sayfası + Kapanış metinleri & logolar |

---

# SAHNE SAHNE ÇEKİM TALİMATLARI

---

## Sahne 1 — Problem (00:00–00:08)
*   **Dosya Adı:** `sahne_01_problem.mp4`
*   **Amaç:** Sekiz saniyede veri dağınıklığını hissettirmek.

**Çekim:**
1. Üç sekmede üç bankanın kampanya sayfası açık olsun (Albaraka, Kuveyt Türk, Ziraat Katılım).
2. Sekmeler arası hızlı geçiş (her biri ~2 sn).
3. Her sayfada kâr payı oranının geçtiği yer **sarı vurgu** ile işaretlensin (kurguda eklenecek). Vurgulanacak farklılık: biri `%1,89`, biri `% 1.89`, biri `yüzde 1,89` yazıyor.

**Ekran üstü yazı:** `10 banka · 599 kampanya · her biri farklı format`

---

## Sahne 2 — Çıkarım ve Kanıt (00:08–00:20) ⭐ **VİDEONUN KALBİ**
*   **Dosya Adı:** `sahne_02_cikarim_kanit.mp4`
*   **Amaç:** Şartnamenin "metin girdisi → yapılandırılmış çıktı" maddesini ve özgün kanıt özelliğini göstermek.

**Çekim:**
1. `http://localhost:3000/campaigns` açık. Tablo dolu (599 kampanya).
2. **Sağ üstten "Banka Çalışanı" moduna geç** (analist görünümü açık olsun).
3. Arama kutusuna `ihtiyac` yaz — liste anında daralsın (filtrenin hızını göster).
4. Listenin en üstündeki **Albaraka** kampanyasını seç / tıkla.
5. Sayfa alt panelde **Çıkarım Kanıtları** tablosu açılır (`Alan · Metindeki ifade · Değer · Yöntem · Güven` sütunları görünür).
6. Çıkarım kanıtlarının altındaki **Kampanya İşlenmiş Metni** panelini de aç (orijinal metin ile çıkarılan verilerin eşleşmesini göster).
7. 2 saniye sabit tut — jürinin okumasına izin ver.

**Ekran üstü yazı:** `Her değerin kaynağı görünür`

---

## Sahne 3 — Dashboard (00:20–00:30)
*   **Dosya Adı:** `sahne_03_dashboard_pdf.mp4`
*   **Amaç:** Şartnamenin "dashboard" maddesi, müşteri/analist modları ve PDF raporlama çıktısını göstermek.

**Çekim:**
1. `/dashboard` sayfasını **Müşteri Görünümü** ile aç ve sayfayı göster.
2. Sağ üstten **Banka Çalışanı** moduna geç.
3. Filtrelerden **Tier 1** seçimini yap.
4. Sayfa kaydırma yapılmadan tek ekranda bir bütün olarak sergilenir.
5. "FinAgent'a Sor" butonunun yanındaki **PDF Çıktısı** butonuna tıkla ve PDF raporunu üret.
6. Üretilen PDF çıktısını baştan aşağıya kaydırarak kaydet / göster.

**Ekran üstü yazı:** `Dinamik Dashboard · Tier 1 Analizi · Anlık PDF Raporlama`

---

## Sahne 4 — (Belirlenecek / Boş)
*   **Dosya Adı:** `sahne_04_belirlenecek.mp4`

_Bu sahne içeriği birazdan doldurulacaktır._

---

## Sahne 5 — Finansman Karşılaştırma (00:36–00:44) ⭐
*   **Dosya Adı:** `sahne_05_finansman.mp4`
*   **Amaç:** Finansman ürünlerinin karşılaştırılması, müşteri ve analist görünümü farkı ile sektör ortalamasına göre yön göstergelerini (oklar) sergilemek.

**Çekim:**
1. `/finansman` sayfasını **Müşteri Görünümü** ile aç ve sayfayı göster.
2. Sağ üstten **Banka Çalışanı** görünümüne geç.
3. Tabloda kaydırma yapılmadan bütüncül görünümde kalınır.
4. Kâr payı / maliyet sütunundaki aşağı/yukarı yön gösteren oklardan birinin üzerine gel (hover yap).
5. Okun açıklama kutucuğu (tooltip - sektör ortalamasına göre durum) net bir şekilde görünene kadar fareyi üzerinde sabit tut ve bekle.

**Ekran üstü yazı:** `Finansman Karşılaştırması · Sektör Ortalaması ve Yön Göstergeleri`

---

## Sahne 6 — Katılım Hesabı ve FinAgent AI Entegrasyonu (00:44–00:54) ⭐
*   **Dosya Adı:** `sahne_06_katilim_chat.mp4`

**Çekim:**
1. `/katilim-hesap` sayfasına doğrudan **Banka Çalışanı** görünümü ile gir.
2. Katılım hesabı ürünlerinden/kampanyalarından birinin üzerine gel.
3. Yanındaki **FinAgent logosuna** tıkla (doğrudan `/chat` sayfasına aktarır).
4. Chat sayfasının otomatik analiz sonucunda çıktı metnini, karşılaştırma metriklerini ve önerilerini üretmesini bekle.
5. 2 saniye sabit tut.

**Ekran üstü yazı:** `Katılım Hesabı · FinAgent AI Chat Entegrasyonu`

---

## Sahne 7 — Doğal Dille Karşılaştırma (Chatbot) (00:54–01:06)
*   **Dosya Adı:** `sahne_07_chatbot_excel.mp4`
*   **Amaç:** Chatbot + karşılaştırma sonucu — çalışan ve müşteri modlarında analiz, metrikler, öneriler ve Excel raporlama çıktısını sergilemek.

**Çekim:**
**1. Soru (Banka Çalışanı Modu):**
1. `/chat` sayfasına geç. **Banka Çalışanı modu açık kalsın.**
2. 1. soruyu yazarken göster:
   > `Albaraka mı daha avantajlı, Dünya Katılım mı?`
3. Gönder.
4. Modelin ürettiği analiz çıktısını, karşılaştırma metriklerini ve önerilerini vermesini bekle.
5. 2 saniye sabit tut.

**2. Soru (Müşteri Modu & Excel Çıktısı):**
6. Sayfayı yenile (refresh) ve sağ üstten **Müşteri Moduna** geç.
7. 2. soruyu yazıp gönder:
   > `kuveyttürk'ün konut finansmanı oranı nedir?`
8. Modelin metin çıktısını, metriklerini ve önerilerini üretmesini bekle.
9. Cevabın altındaki **Excel Çıktısı** butonuna tıkla ve Excel raporunu al / göster.
10. 2 saniye sabit tut.

**Ekran üstü yazı:** `Doğal Dil Analizi · Metrikler & Öneriler · Anlık Excel Çıktısı`

---

## Sahne 8 — Kurum İçi Kanıt (01:06–01:14) ⭐ **FARKLILAŞTIRICI**
*   **Dosya Adı:** `sahne_08_kurum_ici_kanit.mp4`
*   **Amaç:** On-Prem kriterini (%20) kanıt olarak göstermek.

**Çekim:**
1. Tarayıcıdan **terminale geç** (tam ekran, büyük font — en az 16pt).
2. Önceden hazırlanmış komutu çalıştır. Ekranda şu görünmeli:

```
--- LLM YOK, DIŞ AĞ ENGELLİ ---
kar_payi_orani : 1.89
bitis_tarihi   : 2026-12-31
kampanya_turu  : konut_finansmani
normalizasyon  : %1,89 -> 1.89 | 50.000 TL -> 50000.0 | 120 aya kadar -> 120
```

3. Çıktıyı 3 saniye sabit tut.

**Ekran üstü yazı:** `Dış ağ kapalı — çıkarım aynı doğrulukla çalışıyor`

---

## Sahne 9 — Kapanış (01:14–01:20)
*   **Dosya Adı:** `sahne_09_kapanis_index_dark.mp4`

**Çekim:**
1. Sahne 1–8 boyunca kullanılan beyaz temadan, **Karanlık Tema (Dark Mode)** açık olan **Index (Ana Sayfa - `/`)** sayfasına geçiş yapılır.
2. Üç kelime sırayla belirir: **Kanıtlanabilir · Karşılaştırılabilir · Kurum içi**
3. Altında tek satır: `599 kampanya · %99,3 kesinlik · sıfır dış bağımlılık`
4. En altta proje + takım adı, TEKNOFEST ve BiQuery logoları.

---

# ÇEKİM ÖNCESİ HAZIRLIK

## Sistem
- [ ] Dört konteyner ayakta ve `healthy` (`docker ps`)
- [ ] Redis önbelleği temizlendi → cevaplar canlı üretilsin
- [ ] `/campaigns`, `/chat`, `/dashboard`, `/finansman`, `/katilim-hesap` ve `/` (index) bir kez açılıp yüklendi (ilk yükleme gecikmesi kayda girmesin)
- [ ] **Banka Çalışanı modu** açık (analist görünümü daha zengin veri gösterir)
- [ ] Kanıt paneli dolu bir kampanya önceden bulundu ve not alındı
- [ ] Terminal komutu hazır, bir kez denendi

## Ekran, Çözünürlük ve Tema
- [ ] **Bütüncül Görünüm (Kaydırma Yok):** Sayfalar aşağı/yukarı kaydırma yapılmadan, tüm tablo ve grafikleri tek bakışta bir bütün olarak gösterecek yüksek çözünürlük ve ölçekte ayarlanmalıdır.
- [ ] **Tema:** Sahne 1'den Sahne 8'e kadar **Beyaz Tema (Açık Mod)** kullanılacak; Sahne 9 kapanışında **Karanlık Tema (Koyu Mod) Index sayfası** kullanılacak
- [ ] Tarayıcı tam ekran (F11), yer imi çubuğu gizli
- [ ] Bildirimler kapalı (Windows odak yardımı açık)
- [ ] Ekran çözünürlüğü yüksek (1920×1080 veya 2K)
- [ ] Terminal fontu en az 16pt — video sıkıştırmasında okunabilsin
- [ ] Fare imleci kapalı (ekran kaydı programı ayarlarından fare imleci ve vurgulaması doğrudan gizlenmeli / kapatılmalıdır)

## Dosya İsimlendirme ve Kayıt
- [ ] Çekilen tüm video klipleri montajda hızlı ve hatasız eşleşme için belirlenen standart isimlerle (`sahne_01_problem.mp4`, `sahne_02_cikarim_kanit.mp4`, vb.) kaydedilmelidir.

---

# KURGU NOTLARI

Kurgu ve montaj sürecinde [kurgu.md](kurgu.md) dosyasındaki talimatları takip ediniz.

---

# ŞARTNAME UYUM KONTROLÜ

Şartname 6. bölümün videodan istedikleri:

| İstenen | Hangi Sahnede | Durum |
|---|---|---|
| Kullanıcı arayüzü | Sahne 2, 3, 5, 7 | ✅ |
| Dashboard | Sahne 3 | ✅ |
| Chatbot | Sahne 6, 7 | ✅ |
| Metin girdisi verilmesi | Sahne 2 (kampanya metni) + Sahne 7 (soru) | ✅ |
| Modelin ürettiği yapılandırılmış çıktı | Sahne 2 (kanıt tablosu) | ✅ |
| Karşılaştırma sonuçları | Sahne 3 (radar) + Sahne 5, 6 + Sahne 7 (iki banka) | ✅ |

