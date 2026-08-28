# SmartData BiQuery — 1 Dakikalık Demo Videosu Akışı

> **Süre:** 60 saniye (şartname: maksimum 5 dk, bizden istenen 1 dk).
> **Format:** Ekran kaydı + dış ses (voice-over). Yüz görüntüsü yok.
> **Çözünürlük:** 1920×1080, 30 fps. Tarayıcı tam ekran, yer imleri gizli.
>
> **Şartname 6. bölüm videoda şunların görünmesini istiyor:** kullanıcı arayüzü,
> dashboard, chatbot, metin girdisi verilmesi, modelin ürettiği yapılandırılmış
> çıktı, karşılaştırma sonuçları. **Altısı da aşağıdaki akışta var.**

---

## Videonun tek işi

60 saniyede jüriyi tek bir şeye ikna etmek:

> **"Bu sistem gerçekten çalışıyor ve her çıkarımını kanıtlayabiliyor."**

Bu yüzden akış "özellik turu" değil, **tek bir hikâye**: dağınık bir metin
giriyor → yapılandırılmış veri çıkıyor → karşılaştırılabilir hale geliyor →
ve bunların hiçbiri için veri kurumdan dışarı çıkmıyor.

---

## Zaman çizelgesi (saniye saniye)

| Zaman | Sahne | Ekranda ne var | Dış ses |
|---|---|---|---|
| 00:00–00:08 | **Problem** | Üç banka sitesi hızlı geçiş; aynı bilgi farklı yazımlarda vurgulanıyor | "On katılım bankası, beş yüz doksan dokuz kampanya. Her biri farklı formatta." |
| 00:08–00:20 | **Çıkarım + kanıt** | `/campaigns` → kampanya seç → Çıkarım Kanıtları paneli açılır, zoom | "Sistem metni okuyor ve her değeri çıkarıyor. Ama asıl fark şurada: hangi ifadeden, hangi yöntemle çıkardığını da gösteriyor." |
| 00:20–00:33 | **Karşılaştırma (chatbot)** | `/chat` → şartname sorusu yazılır → tablo + yorum akar | "Doğal dille soruyoruz: Albaraka mı daha avantajlı, Dünya Katılım mı? Cevap tablo ve pazar payı analiziyle geliyor." |
| 00:33–00:43 | **Dashboard** | `/dashboard` → lider kartlar → radar grafiği | "Analist tarafında yedi kriterde lider kampanyalar ve sektör bazlı rekabet haritası." |
| 00:43–00:52 | **Kurum içi kanıt** | Terminal: ağ engelli çıkarım çıktısı | "Ve tamamı kurum içinde çalışıyor. Dış ağı tamamen kapattık; çıkarım aynı doğrulukla devam ediyor." |
| 00:52–01:00 | **Kapanış** | Üç kelime + logo | "Kanıtlanabilir. Karşılaştırılabilir. Kurum içi." |

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
3. Arama kutusuna `konut` yaz — liste anında daralsın (filtrenin hızını göster).
4. Bir konut finansmanı kampanyasına tıkla.
5. Sayfa alt panelde **Çıkarım Kanıtları** tablosu açılır.
6. **Bu tabloya yakınlaş (zoom).** Şu sütunlar net okunmalı:
   `Alan · Metindeki ifade · Değer · Yöntem · Güven`
7. 2 saniye sabit tut — jürinin okumasına izin ver.

**Ekran üstü yazı:** `Her değerin kaynağı görünür`

**Dış ses:**
> "Sistem metni okuyor ve her değeri çıkarıyor. Ama asıl fark şurada: hangi
> ifadeden, hangi yöntemle ve ne güvenle çıkardığını da gösteriyor."

> 💡 **Hazırlık:** Çekimden önce kanıt paneli dolu bir kampanya bulup not alın
> (örn. Albaraka "Dijitale Özel Konut ve Taşıt Finansmanı Kampanyası" —
> `kar_payi_orani = 2.87`, kaynak ifade `"%2,87 'den başlayan"`). Kayıt sırasında
> arayıp bulmaya çalışmayın.

---

## Sahne 3 — Doğal dille karşılaştırma (00:20–00:33)

**Amaç:** Chatbot + karşılaştırma sonucu — şartnamenin iki maddesi tek sahnede.

**Çekim:**
1. `/chat` sayfasına geç. **Banka Çalışanı modu açık kalsın.**
2. Soruyu **yazarken göster** (kopyala-yapıştır yapma; yazma efekti canlılık
   katar, ama hızlandırılmış olabilir):

   > `Albaraka mı daha avantajlı, Dünya Katılım mı?`

3. Gönder. **İlk kelimelerin 0,2 saniyede geldiğini** göster — kesme yapma.
4. Tablo belirdiğinde yakınlaş: iki bankanın satırları net görünsün.
5. Altındaki yorum metninden bir cümle görünür kalsın (pazar payı karşılaştırması).

**Ekran üstü yazı:** `Şartname Senaryo 2 — birebir soru`

**Dış ses:**
> "Doğal dille soruyoruz: Albaraka mı daha avantajlı, Dünya Katılım mı? Cevap,
> tablo ve pazar payı analiziyle birlikte geliyor."

> ⚠️ **Kritik:** Çekimden hemen önce Redis önbelleğini temizleyin
> (`docker exec smartdata-redis redis-cli FLUSHDB`). Önbellekten gelen cevap
> anında belirir ve "önceden hazırlanmış" izlenimi verir. Canlı üretim daha
> inandırıcı.

---

## Sahne 4 — Dashboard (00:33–00:43)

**Amaç:** Şartnamenin "dashboard" maddesi + analist değeri.

**Çekim:**
1. `/dashboard` aç.
2. Üstteki **lider kampanya kartlarında** yavaş yatay kaydırma. Şu yedi kart
   görünsün: `Düşük Kâr Payı · Yüksek Ödül · Uzun Vade · Düşük Masraf ·
   Yüksek Limit · MGM Davet · Nakit İade`
3. Aşağı kaydır → **radar grafiği**. Bir bankanın üzerine gel, tooltip çıksın.
4. Radar grafiğinin **Detay** düğmesine bas — büyütülmüş görünüm.

**Ekran üstü yazı:** `7 kriterde lider kampanyalar · sektör radarı`

**Dış ses:**
> "Analist tarafında yedi kriterde lider kampanyalar ve sektör bazlı rekabet
> haritası."

> 💡 Dışa aktarma düğmelerine (PNG/Excel/PDF) tıklamayın — indirme diyaloğu
> kaydı bozar. Sadece düğmelerin göründüğünden emin olun.

---

## Sahne 5 — Kurum içi kanıt (00:43–00:52) ⭐ **FARKLILAŞTIRICI**

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

## Sahne 6 — Kapanış (00:52–01:00)

**Çekim:**
1. Siyah/koyu zemine geçiş.
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
- [ ] `/campaigns`, `/chat`, `/dashboard` bir kez açılıp yüklendi (ilk yükleme
      gecikmesi kayda girmesin)
- [ ] **Banka Çalışanı modu** açık (analist görünümü daha zengin veri gösterir)
- [ ] Kanıt paneli dolu bir kampanya önceden bulundu ve not alındı
- [ ] Terminal komutu hazır, bir kez denendi

## Ekran

- [ ] Tarayıcı tam ekran (F11), yer imi çubuğu gizli
- [ ] Bildirimler kapalı (Windows odak yardımı açık)
- [ ] Ekran çözünürlüğü 1920×1080
- [ ] Terminal fontu en az 16pt — video sıkıştırmasında okunabilsin
- [ ] Fare imleci vurgulaması açık (izleyici nereye tıkladığınızı görsün)

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
| Zoom | Sahne 2 ve 3'te tabloya yumuşak zoom. Diğer sahnelerde sabit. |
| Altyazı | **Açık altyazı ekleyin** — jüri sesi kısık izleyebilir |
| Ekran üstü yazı | Sahne başına bir tane, en fazla 5 kelime |
| Fazlalık | Ayarlar, filtre menüleri, i18n dil değiştirme **gösterilmeyecek** |

---

# ŞARTNAME UYUM KONTROLÜ

Şartname 6. bölümün videodan istedikleri:

| İstenen | Hangi sahnede | ✓ |
|---|---|---|
| Kullanıcı arayüzü | Sahne 2, 3, 4 | ✅ |
| Dashboard | Sahne 4 | ✅ |
| Chatbot | Sahne 3 | ✅ |
| Metin girdisi verilmesi | Sahne 2 (kampanya metni) + Sahne 3 (soru) | ✅ |
| Modelin ürettiği yapılandırılmış çıktı | Sahne 2 (kanıt tablosu) | ✅ |
| Karşılaştırma sonuçları | Sahne 3 (iki banka) + Sahne 4 (radar) | ✅ |

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
