# SmartData BiQuery — 1 Dakikalık Demo Videosu Akışı

> **Süre:** 60 saniye (şartname: maksimum 5 dk, bizden istenen 1 dk).
> **Format:** Ekran kaydı + dış ses (voice-over). Yüz görüntüsü yok.
> **Çözünürlük & Ölçek:** Yüksek çözünürlük (1920×1080 / 2K), 30 fps. Tarayıcı tam ekran, yer imleri gizli. **Kritik Kural:** Sayfalar dikey kaydırma (scroll) yapılmadan, yüksek çözünürlükte tüm bileşenleriyle **tek karede bir bütün olarak** çekilecektir.
>
> **Şartname 6. bölüm videoda şunların görünmesini istiyor:** kullanıcı arayüzü,
> dashboard, chatbot, metin girdisi verilmesi, modelin ürettiği yapılandırılmış
> çıktı, karşılaştırma sonuçları. **Altısı da aşağıdaki akışta var.**

---

## Videonun tek işi ve amacı

Video, TEKNOFEST şartnamesine tam uyumlu, tutarlı ve profesyonel bir tanıtım videosu olarak 60 saniyede jüriyi şu temel gerçeğe ikna etmeyi hedefler:

> **"Bu sistem şartnameye tam uyumlu, tutarlı bir şekilde çalışıyor ve her çıkarımını kanıtlayabiliyor."**

Bu yüzden akış "özellik turu" değil, **tutarlı bir hikâye**: dağınık bir metin
giriyor → yapılandırılmış veri çıkıyor → karşılaştırılabilir hale geliyor →
ve bunların hiçbiri için veri kurumdan dışarı çıkmıyor.

---

## Zaman çizelgesi (saniye saniye)

| Zaman | Sahne | Ekranda ne var | Dış ses |
|---|---|---|---|
| 00:00–00:08 | **Problem** | Üç banka sitesi hızlı geçiş; aynı bilgi farklı yazımlarda vurgulanıyor | "On katılım bankası, beş yüz doksan dokuz kampanya. Her biri farklı formatta." |
| 00:08–00:20 | **Çıkarım + kanıt** | `/campaigns` → kampanya seç → Çıkarım Kanıtları paneli açılır, zoom | "Sistem metni okuyor ve her değeri çıkarıyor. Ama asıl fark şurada: hangi ifadeden, hangi yöntemle çıkardığını da gösteriyor." |
| 00:20–00:30 | **Dashboard** | `/dashboard` → lider kartlar → radar grafiği | "Analist tarafında yedi kriterde lider kampanyalar ve sektör bazlı rekabet haritası." |
| 00:30–00:42 | **Finansman & Katılım** | `/finansman` ve `/katilim-hesap` → müşteri & çalışan görünümü | "Finansman ve kâr payı oranlarında sektör ortalaması ve yön göstergeleri." |
| 00:42–00:54 | **Karşılaştırma (chatbot)** | `/chat` → şartname sorusu yazılır → tablo + yorum akar | "Doğal dille soruyoruz: Albaraka mı daha avantajlı, Dünya Katılım mı? Cevap tablo ve pazar payı analiziyle geliyor." |
| 00:54–01:02 | **Kurum içi kanıt** | Terminal: ağ engelli çıkarım çıktısı | "Ve tamamı kurum içinde çalışıyor. Dış ağı tamamen kapattık; çıkarım aynı doğrulukla devam ediyor." |
| 01:02–01:10 | **Kapanış** | Üç kelime + logo | "Kanıtlanabilir. Karşılaştırılabilir. Kurum içi." |

---

# SAHNE SAHNE ÇEKİM TALİMATLARI

---

## Sahne 1 — Problem (00:00–00:08)

**Amaç:** Sekiz saniyede acıyı hissettir. Uzatma.

**Çekim:**
1. Üç sekmede üç bankanın kampanya sayfası açık olsun (Albaraka, Kuveyt Türk,
   Ziraat Katılım).
2. Sekmeler arası hızlı geçiş (her biri ~2 sn).
3. Her sayfada kâr payı oranının geçtiği yer **sarı vurgu** ile işaretlensin —
   kurguda eklenecek. Vurgulanacak farklılık: biri `%1,89`, biri `% 1.89`,
   biri `yüzde 1,89` yazıyor.

**Ekran üstü yazı:** `10 banka · 599 kampanya · her biri farklı format`

**Dış ses:**
> "On katılım bankası, beş yüz doksan dokuz kampanya. Her biri farklı formatta."

> ⚠️ **Tuzak:** Banka sitelerinde gezinirken çerez pop-up'ları çıkar. Çekimden
> önce sayfaları açıp kapatın.

---

## Sahne 2 — Çıkarım ve Kanıt (00:08–00:20) ⭐ **VİDEONUN KALBİ**

**Amaç:** Şartnamenin "metin girdisi → yapılandırılmış çıktı" maddesini ve bizim
en özgün özelliğimizi aynı anda göstermek.

**Çekim:**
1. `http://localhost:3000/campaigns` açık. Tablo dolu (599 kampanya).
2. **Sağ üstten "Banka Çalışanı" moduna geç** (analist görünümü açık olsun).
3. Arama kutusuna `ihtiyac` yaz — liste anında daralsın (filtrenin hızını göster).
4. Listenin en üstündeki **Albaraka** kampanyasını seç / tıkla.
5. Sayfa alt panelde **Çıkarım Kanıtları** tablosu açılır (`Alan · Metindeki ifade · Değer · Yöntem · Güven` sütunları net okunur).
6. Çıkarım kanıtlarının altındaki **Kampanya İşlenmiş Metni** panelini de aç (orijinal metin ile çıkarılan verilerin eşleşmesini göster).
7. 2 saniye sabit tut — jürinin okumasına izin ver.

**Ekran üstü yazı:** `Her değerin kaynağı görünür`

**Dış ses:**
> "Sistem metni okuyor ve her değeri çıkarıyor. Ama asıl fark şurada: hangi
> ifadeden, hangi yöntemle ve ne güvenle çıkardığını da gösteriyor."

> 💡 **Hazırlık:** Çekimden önce kanıt paneli dolu bir kampanya bulup not alın
> (örn. Albaraka ihtiyac kampanyası" —
> `kar_payi_orani = 2.87`, kaynak ifade `"%2,87 'den başlayan"`). Kayıt sırasında
> arayıp bulmaya çalışmayın.

---

## Sahne 3 — Dashboard (00:20–00:30)

**Amaç:** Şartnamenin "dashboard" maddesi, müşteri/analist modları ve PDF raporlama çıktısını göstermek.

**Çekim:**
1. `/dashboard` sayfasını **Müşteri Görünümü** ile aç ve sayfayı göster.
2. Sağ üstten **Banka Çalışanı** moduna geç.
3. Filtrelerden **Tier 1** seçimini yap.
4. Sayfayı akıcı bir şekilde en alta kadar kaydırarak tüm grafik ve analizleri göster.
5. "FinAgent'a Sor" butonunun yanındaki **PDF Çıktısı** butonuna tıkla ve PDF raporunu üret.
6. Üretilen PDF çıktısını baştan aşağıya kaydırarak kaydet / göster.

**Ekran üstü yazı:** `Dinamik Dashboard · Tier 1 Analizi · Anlık PDF Raporlama`

**Dış ses:**
> "Müşteri ve analist modlarıyla sektör analizi; tek tıkla kurumsal PDF raporlama."

---

## Sahne 4 — (Belirlenecek / Boş)

_Bu sahne içeriği birazdan doldurulacaktır._

---

## Sahne 5 — Finansman Karşılaştırma (00:36–00:44) ⭐

**Amaç:** Finansman ürünlerinin karşılaştırılması, müşteri ve analist görünümü farkı ile sektör ortalamasına göre yön göstergelerini (oklar) sergilemek.

**Çekim:**
1. `/finansman` sayfasını **Müşteri Görünümü** ile aç ve sayfayı göster.
2. Sağ üstten **Banka Çalışanı** görünümüne geç.
3. Tabloda aşağı doğru kaydır.
4. Kâr payı / maliyet sütunundaki aşağı/yukarı yön gösteren oklardan birinin üzerine gel (hover yap).
5. Okun açıklama kutucuğu (tooltip - sektör ortalamasına göre durum) net bir şekilde görünene kadar fareyi üzerinde sabit tut ve bekle.

**Ekran üstü yazı:** `Finansman Karşılaştırması · Sektör Ortalaması ve Yön Göstergeleri`

---

## Sahne 6 — Katılım Hesabı ve FinAgent AI Entegrasyonu (00:42–00:52) ⭐

**Çekim:**
1. `/katilim-hesap` sayfasına doğrudan **Banka Çalışanı** görünümü ile gir.
2. Katılım hesabı ürünlerinden/kampanyalarından birinin üzerine gel.
3. Yanındaki **FinAgent logosuna** tıkla (doğrudan `/chat` sayfasına aktarır).
4. Chat sayfasının otomatik analiz sonucunda çıktı metnini, karşılaştırma metriklerini ve önerilerini üretmesini bekle.
5. 2 saniye sabit tut.

**Ekran üstü yazı:** `Katılım Hesabı · FinAgent AI Chat Entegrasyonu`

---

## Sahne 7 — Doğal dille karşılaştırma (Chatbot) (00:54–01:06)

**Amaç:** Chatbot + karşılaştırma sonucu — çalışan ve müşteri modlarında analiz, metrikler, öneriler ve Excel raporlama çıktısını sergilemek.

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

**Dış ses:**
> "Doğal dille soruyoruz: Albaraka mı daha avantajlı, Dünya Katılım mı? Cevap,
> tablo ve pazar payı analiziyle birlikte geliyor."

> ⚠️ **Kritik:** Çekimden hemen önce Redis önbelleğini temizleyin
> (`docker exec smartdata-redis redis-cli FLUSHDB`). Önbellekten gelen cevap
> anında belirir ve "önceden hazırlanmış" izlenimi verir. Canlı üretim daha
> inandırıcı.

---

## Sahne 8 — Kurum içi kanıt (01:06–01:14) ⭐ **FARKLILAŞTIRICI**

**Amaç:** On-Prem kriterini (%20) iddia olarak değil kanıt olarak göstermek.

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

**Dış ses:**
> "Ve tamamı kurum içinde çalışıyor. Dış ağı tamamen kapattık; çıkarım aynı
> doğrulukla devam ediyor."

> 💡 **Neden bu sahne değerli:** Jüri "on-prem" iddiasını herkesten duyacak.
> Terminal çıktısıyla kanıtlayan tek takım olma ihtimaliniz yüksek. İşlenen
> metin de şartnamenin **kendi örneği** (s.10, A Bankası konut finansmanı) —
> bunu dış seste veya ekran yazısında belirtin.

---

## Sahne 9 — Kapanış (01:14–01:20)

**Çekim:**
1. Sahne 1–8 boyunca kullanılan beyaz temadan, **Karanlık Tema (Dark Mode)** açık olan **Index (Ana Sayfa - `/`)** sayfasına geçiş yapılır.
2. Üç kelime sırayla belirir: **Kanıtlanabilir · Karşılaştırılabilir · Kurum içi**
3. Altında tek satır: `599 kampanya · %99,3 kesinlik · sıfır dış bağımlılık`
4. En altta proje + takım adı, TEKNOFEST ve BiQuery logoları.

**Dış ses:**
> "Kanıtlanabilir. Karşılaştırılabilir. Kurum içi."

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

## Ses

- [ ] Dış ses ayrı kaydedilsin, ekran kaydıyla sonradan birleştirilsin
      (canlı konuşurken tıklama sesleri ve duraksamalar giriyor)
- [ ] Metin **60 saniyeye sığacak şekilde** prova edildi — yukarıdaki dış ses
      metni toplam ~110 kelime, normal tempoda tam oturur
- [ ] Arka plan müziği varsa çok kısık (-25 dB), konuşmayı bastırmasın

---

# KURGU NOTLARI

| Konu | Karar |
|---|---|
| Geçişler | Sert kesme (cut). Efektli geçiş 1 dakikada zaman çalar. |
| Hızlandırma | Yazma ve yükleme anları 1.5–2× hızlandırılabilir; **cevap akışı hızlandırılmasın** (gerçek hız zaten etkileyici) |
| Zoom | Sahne 2 ve 7'de tabloya yumuşak zoom. Diğer sahnelerde sabit. |
| Altyazı | **Açık altyazı ekleyin** — jüri sesi kısık izleyebilir |
| Ekran üstü yazı | Sahne başına bir tane, en fazla 5 kelime |
| Fazlalık | Ayarlar, filtre menüleri, i18n dil değiştirme **gösterilmeyecek** |

---

# ŞARTNAME UYUM KONTROLÜ

Şartname 6. bölümün videodan istedikleri:

| İstenen | Hangi sahnede | ✓ |
|---|---|---|
| Kullanıcı arayüzü | Sahne 2, 3, 5, 7 | ✅ |
| Dashboard | Sahne 3 | ✅ |
| Chatbot | Sahne 6, 7 | ✅ |
| Metin girdisi verilmesi | Sahne 2 (kampanya metni) + Sahne 7 (soru) | ✅ |
| Modelin ürettiği yapılandırılmış çıktı | Sahne 2 (kanıt tablosu) | ✅ |
| Karşılaştırma sonuçları | Sahne 3 (radar) + Sahne 5, 6 + Sahne 7 (iki banka) | ✅ |

---

# EĞER 5 DAKİKAYA ÇIKARILIRSA

Şartname üst sınırı 5 dakika. Süre serbest bırakılırsa şu sahneler eklenir:

| Ek sahne | Süre | İçerik |
|---|---|---|
| Finansman karşılaştırması | 40 sn | `/finansman` — kategori filtreleri, ortalamaya göre ok göstergeleri, "taksit hesaplanmıyor, bankanın değeri kullanılıyor" mesajı |
| Katılım hesabı | 30 sn | Brüt/net oran, stopaj kesintisi, vade sonu toplam |
| Müşteri vs Analist | 40 sn | Aynı soru iki personada yan yana — dil farkı net görünür |
| Rapor dışa aktarma | 30 sn | Chatbot cevabından Excel/PDF/PNG üretimi |
| Boru hattı | 40 sn | `pipeline.py` çalışırken kalite denetimi adımının çıktısı |
| Belge yükleme (OCR) | 30 sn | PDF sürükle-bırak → metin çıkarımı |
