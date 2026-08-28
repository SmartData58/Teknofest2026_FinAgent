# Sahne klipleri — kayıt raporu

Kaynak: `video çekim-render .md`. Dosya adları o dokümandaki isimlendirmeyle birebir.

| Dosya | Süre | Ne var |
|---|---:|---|
| `sahne_02_cikarim_kanit.mp4` | 21,0 sn | /campaigns → Banka Çalışanı → **TÜR filtresi: İhtiyaç** (599→6) → kâr payı dolu satır → Çıkarım Kanıtları + İşlenmiş Metin |
| `sahne_03_dashboard_pdf.mp4` | 21,9 sn | /dashboard → Banka Çalışanı → **Tier 1** → iki banka seçimi → Rekabet Analizi (trend, radar, yayın süreleri) → **PDF indirildi** |
| `sahne_05_finansman.mp4` | 14,6 sn | /finansman → Banka Çalışanı → sektör ortalaması kutuları + ürün kartlarında yön okları |
| `sahne_06_katilim_chat.mp4` | 31,3 sn | /katilim-hesap → FinAgent logosu → /chat otomatik analiz (halka grafik + karşılaştırma tablosu) |
| `sahne_07_chatbot_excel.mp4` | 42,9 sn | /chat Soru 1 (Banka Çalışanı) → Soru 2 (Müşteri) → **Excel indirildi** |
| `sahne_09_kapanis_index_dark.mp4` | 29,4 sn | Karanlık tema ana sayfa: hero → Proje Özeti → Sistem Mimarisi |

**Teknik:** 1920×1080, **30 fps CFR**, H.264 / yuv420p, sessiz.
Playwright ~25 fps VFR yazıyor; ffmpeg `fps=30` ile sabit 30 fps'e çevrildi.
Fare imleci kayda düşmüyor (Playwright imleci çizmez) — dokümandaki
"imleç gizli olsun" şartı kendiliğinden sağlanıyor.

## Çekilmeyenler ve nedeni

- **`sahne_01_problem.mp4`** — üç bankanın kendi web sitesi. Dış siteler;
  çerez bantları ve bot korumaları var, otomatik çekmedim. Elle çekilmeli.
- **`sahne_04_belirlenecek.mp4`** — dokümanda içerik boş bırakılmış.
- **`sahne_08_kurum_ici_kanit.mp4`** — terminal kaydı, tarayıcı değil.
  Komut hazır, ekranda çalıştırılıp çekilmeli.

## Kurguda bilinmesi gerekenler

1. **Sahne 5 – ok ipucu (tooltip).** Oklar native `title` özniteliği kullanıyor;
   native ipuçlarını tarayıcı çizer ve **ekran kaydına düşmez.** Klipte okun
   kendisi ve hover durumu var, ipucu metni yok. Doküman "ipucu net görünene
   kadar bekle" diyor — bunu kurguda çağrı kutusu (callout) olarak eklemek
   gerekiyor. Metin: sektör ortalamasına göre düşük/yüksek durumu.
2. **Sahne 7 – 2. soru.** Dokümandaki soru "kuveyttürk'ün konut finansmanı oranı
   nedir?". Finansman ürün verisinde **Kuveyt Türk yok** (4 banka var: Albaraka,
   Dünya, Vakıf, Ziraat). Sistem bunu saklamıyor, "kaydımızda yok" deyip diğer
   bankaların konut oranlarını karşılaştırmalı olarak veriyor. Dürüstlük açısından
   güçlü ama tanıtım videosunda "yok" cümlesiyle açılıyor. İstenirse soru
   Albaraka'ya çevrilip yeniden çekilebilir.
3. **Sahne 2 – arama kutusu.** `ihtiyac` (ç'siz) yazınca **0 sonuç** dönüyor;
   arama Türkçe karakter duyarlı. Bu yüzden serbest arama yerine TÜR filtresi
   kullanıldı. (Arama tarafında diakritik duyarsızlaştırma ayrı bir iyileştirme.)
4. **Kadraj.** Doküman "kaydırma olmadan tek karede bütün sayfa" istiyor.
   Ölçüldü: içerik sütunu `max-width` ile sınırlı, yani görüntü alanını
   genişletmek sadece yanlarda beyaz boşluk açıyor. 2880×1620'de her şey sığıyor
   ama sütun kadrajın %53'ünü doldurup metin okunmaz hale geliyordu. Seçilen
   denge **2304×1296 → 1920×1080** (%69 dolgu); taşan 300–400 px kübik eğriyle
   yumuşak kaydırılıyor.

## Yeniden çekim

```bash
docker cp cekim.py teknofest2026_finagent-scraper-1:/tmp/cekim.py
docker exec teknofest2026_finagent-scraper-1 python /tmp/cekim.py sahne_05
```

Argümansız çalıştırınca tüm sahneleri çeker.
