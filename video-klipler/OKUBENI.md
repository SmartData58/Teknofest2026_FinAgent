# Sahne klipleri — kayıt raporu

Kaynak: `video çekim-render .md`. Dosya adları o dokümandaki isimlendirmeyle birebir.

| Dosya | Süre | Ne var |
|---|---:|---|
| `sahne_02_cikarim_kanit.mp4` | 25,7 sn | /campaigns → Banka Çalışanı → **TÜR filtresi: İhtiyaç** (599→6) → kâr payı dolu satır → Çıkarım Kanıtları → İşlenmiş Metin → **sayfa sonuna kadar** |
| `sahne_03_dashboard_pdf.mp4` | 33,1 sn | /dashboard → Banka Çalışanı → **Tier 1** → iki banka → Rekabet Analizi (trend, radar, yayın süreleri) → PDF üretimi → **üretilen PDF ekranda, 6 sayfa baştan sona** |
| `sahne_05_finansman.mp4` | 22,1 sn | /finansman → Banka Çalışanı → sektör ortalaması kutuları → yön okları → **48 ürünün tamamı sonuna kadar** |
| `sahne_06_katilim_chat.mp4` | 32,0 sn | /katilim-hesap → FinAgent logosu → /chat otomatik analiz (halka + karşılaştırma) → **cevabın sonuna kadar** |
| `sahne_07_chatbot_excel.mp4` | 40,1 sn | /chat Soru 1 (Banka Çalışanı) → Soru 2 (Müşteri) → **Excel indirildi**, her iki cevap sonuna kadar |
| `sahne_09_kapanis_index_dark.mp4` | 35,9 sn | Karanlık tema ana sayfa: hero → Proje Özeti → Hedefler → Takım → **sayfa sonu** |

**Teknik:** 1920×1080 · **30 fps CFR** · H.264 (`preset veryslow`, **CRF 16**, `tune stillimage`) · yuv420p · sessiz.

### Kalite kararı — neden 1080p, neden daha büyük değil

Daha büyük kadraj (2304 / 2560 / 2880) denendi ve **bırakıldı**: içerik sütunu
`max-width` ile sınırlı olduğu için görüntü alanını genişletmek metni
büyütmüyor, yalnızca yanlarda beyaz boşluk açıyor — metnin piksel boyutu her
durumda aynı. Buna karşılık görüntü alanı ile kayıt boyutu farklı olduğunda
Playwright kareyi **ölçekliyor** ve metin gözle görülür şekilde yumuşuyordu.
Bu yüzden görüntü alanı = kayıt boyutu (1920×1080, **hiç ölçekleme yok**) ve
kayıp CRF ile telafi ediliyor. Playwright ~25 fps VFR yazar; ffmpeg `fps=30`
ile sabit 30 fps'e çevriliyor.

Fare imleci kayda düşmüyor (Playwright imleci çizmez) — dokümandaki
"imleç gizli olsun" şartı kendiliğinden sağlanıyor.

### Sayfa sonuna inme

Her sahne, sayfanın **en altına kadar** kübik eğriyle iniyor (`dibe_in`).
Kaydırma animasyonu sayfanın İÇİNDE `requestAnimationFrame` ile çalışıyor;
önceki sürüm her kare için ayrı bir `page.evaluate` yapıyordu ve sürekli
animasyonlu ana sayfada bu kilitlenerek kaydı 18 dakikaya çıkarmıştı.

### Dashboard PDF çıktısı videoda

`sahne_03` artık PDF'i yalnızca indirmiyor, **ekranda gösteriyor**: indirilen
dosya PyMuPDF ile 150 DPI'da PNG'ye çevrilip tek sayfada alt alta diziliyor ve
baştan sona kaydırılıyor. Ekranda görünen, sistemin ürettiği gerçek PDF.
(Headless Chromium `file://…pdf` adresini görüntülemiyor, indirmeye başlıyor —
doğrudan açmak bu yüzden mümkün değil.) Üretilen dosya: `dashboard-raporu.pdf`.

---

## Çekilmeyenler ve nedeni

- **`sahne_01_problem.mp4`** — üç bankanın kendi web sitesi. Dış siteler;
  çerez bantları ve bot korumaları var, otomatik sürmedim. Elle çekilmeli.
- **`sahne_04_belirlenecek.mp4`** — dokümanda içerik boş bırakılmış.
- **`sahne_08_kurum_ici_kanit.mp4`** — terminal kaydı, tarayıcı değil.

## Kurguda bilinmesi gerekenler

1. **Sahne 5 – ok ipucu (tooltip) yok.** Oklar native `title` özniteliği
   kullanıyor; native ipuçlarını tarayıcı çizer ve **ekran kaydına düşmez.**
   Klipte okun kendisi ve hover durumu var. İpucu metnini kurguda çağrı kutusu
   olarak eklemek gerekiyor.
2. **Sahne 7 – 2. soru.** Dokümandaki soru "kuveyttürk'ün konut finansmanı
   oranı nedir?". Finansman ürün verisinde **Kuveyt Türk yok** (Albaraka,
   Dünya, Vakıf, Ziraat var). Sistem uydurmuyor, "kaydımızda yok" deyip diğer
   bankaların konut oranlarını karşılaştırmalı veriyor. Dürüstlük açısından
   güçlü ama tanıtım videosu "yok" cümlesiyle açılıyor. İstenirse soru
   Albaraka'ya çevrilip yeniden çekilebilir.
3. **Sahne 2 – arama kutusu.** `ihtiyac` (ç'siz) yazınca **0 sonuç** dönüyor;
   arama Türkçe karakter duyarlı. Bu yüzden serbest arama yerine TÜR filtresi
   kullanıldı. (Aramada diakritik duyarsızlaştırma ayrı bir iyileştirme.)
4. **Sahne 9 – son kare.** Sayfanın dibinde sohbet aracı "Yapay Zeka
   Hazırlanıyor…" yükleme durumunda görünüyor. Kapanış karesi olarak daha
   erken bir an (Takım bölümü ya da hero) seçilmeli.

## Yeniden çekim

```bash
docker cp cekim.py teknofest2026_finagent-scraper-1:/tmp/cekim.py
docker exec teknofest2026_finagent-scraper-1 python /tmp/cekim.py sahne_05
```

Argümansız çalıştırınca tüm sahneleri çeker. Dönüştürme: `sh /tmp/donustur.sh`.
