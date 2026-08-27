# FinAgent — Karma Persona Testi

**Hedef:** `http://localhost:8003/api/chat`  
**Senaryo:** 100  
**Genel başarı:** 1128/1169 (96%)

| Persona | Kategori | n | Puan | Başarı |
|---|---|---:|---:|---:|
| analist | coklu_kiyas | 12 | 204/204 | 100% |
| analist | gecerlilik | 5 | 48/50 | 96% |
| analist | konumlanma | 10 | 114/130 | 88% |
| analist | metrik | 8 | 95/96 | 99% |
| analist | piyasa | 10 | 128/130 | 98% |
| analist | sinir | 2 | 16/16 | 100% |
| musteri | anlama | 10 | 103/110 | 94% |
| musteri | banka_sorusu | 8 | 80/80 | 100% |
| musteri | gecerlilik | 6 | 58/66 | 88% |
| musteri | kampanya_arama | 14 | 140/140 | 100% |
| musteri | sayisal | 6 | 53/54 | 98% |
| musteri | sinir | 3 | 26/27 | 96% |
| musteri | tavsiye | 6 | 63/66 | 95% |

## Bulgular

### [musteri/anlama] murabaha nedir
- analist jargonu: ['veri seti']
- doğrudan hitap yok (siz/kazanç/başvuru)

> Murabaha, elimdeki mevcut kampanya verilerinde yer alan bir tanım veya açıklama değildir. Elimdeki kayıtlar sadece Albaraka Türk'ün Kırtasiye, Şubesiz Umre Finansmanı, Sadakat Programı ve Limitsiz İMM Sigortası gibi belirli kampanyalarına dair detayları içermektedir.

Bu nedenle, murabaha kavramının ne olduğunu veya nasıl çalıştığını açıklamak elimdeki veri seti kapsamında mümkün değildir. Sadece 

### [musteri/anlama] kampanyadan yararlanmak için ne gerekiyor
- analist jargonu: ['veri seti']
- görsel gelmemeliydi (table)

> Kampanyalardan yararlanmak için elimdeki kayıtlarda belirtilen spesifik başvuru koşulları (örneğin minimum harcama tutarı, belirli bir işlem sayısı veya vade süresi) maalesef yer almıyor; bu detaylar mevcut veri setinde bulunmuyor. Ancak elimdeki verilere göre Albaraka Türk'ün "Akaryakıt Kampanyası" ile 1.500 TL, "Ağustos Ayına Özel Fatura Kampanyası" ile ise 500 TL ödül kazanma fırsatı mevcut. Bu

### [musteri/tavsiye] param olsa nereye yatırmalıyım
- somut tutar/oran yok

> Ben bir yapay zeka asistanıyım ve yatırım/finansal tavsiye veremem. Ancak bankaların güncel kampanya, oran ve masraf bilgilerini sizin için karşılaştırıp listeleyebilirim.

### [musteri/tavsiye] hangi bankayı tercih etmeliyim
- cevap çok uzun (2219 krktr > 2200)

> Hangi bankayı tercih etmeniz, öncelikli ihtiyacınızın yüksek nakit ödül mü yoksa uzun vadeli finansman mı olduğuna göre değişir; ancak elimdeki kayıtlara göre en yüksek tekil ödül fırsatını **Hayat Finans** sunmaktadır. Özellikle "Arkadaşını Davet Et, Avantajlı Hesapla Kazanmaya Başla" kampanyasıyla 10.000 TL, "Biz Kart Arkadaşını Getir & Kazan" kampanyasıyla ise 25.000 TL'ye varan nakit ödül kaza

### [musteri/tavsiye] bu kampanya değer mi
- somut tutar/oran yok

> Ben bir yapay zeka asistanıyım ve yatırım/finansal tavsiye veremem. Ancak bankaların güncel kampanya, oran ve masraf bilgilerini sizin için karşılaştırıp listeleyebilirim.

### [musteri/gecerlilik] bu kampanyalar hâlâ geçerli mi
- doğrudan hitap yok (siz/kazanç/başvuru)
- somut tutar/oran yok

> Elimdeki kayıtlara göre, bahsettiğiniz kampanyaların geçerlilik tarihleri 2026 yılını kapsamaktadır. Hayat Finans'ın "Bana Bunu Al İş Ortağım ile Troy Mağazalarında Finansman Fırsatı" kampanyası 31 Ağustos 2026 tarihine kadar, Kuveyt Türk'ün "E-Ticaret, E-İhracat ve Tekno Girişimcilere Özel Fırsat" ve "E-Ticaret Pazaryeri Satıcılarına Özel Vade Farksız 3 Taksit" kampanyaları ise 31 Aralık 2026 tar

### [musteri/gecerlilik] yakında biten kampanya var mı
- somut tutar/oran yok

> Elimdeki kampanya verilerinde, bitiş tarihi henüz gelmemiş ve "yakında bitecek" olarak işaretlenmiş aktif bir kampanya bulunmamaktadır.

Mevcut kayıtlarım, süresi dolmuş 77 kampanyanın listesini içeriyor ve bu listede gösterilen örnekler (Albaraka Türk'ün Togg Finansmanı, Türkiye Finans'ın Banka ve Kamu Çalışanlarına Özel İhtiyaç Finansmanı) tamamen sona ermiş durumdadır. Bu nedenle, şu an için ba

### [musteri/gecerlilik] süresi dolmak üzere olan fırsatlar neler
- analist jargonu: ['veri seti']

> Elimdeki kampanya verilerinde, süresi dolmak üzere olan fırsatların tam listesini ve bitiş tarihlerini içeren detaylı bir kayıt bulunmamaktadır.

Veri setinde toplam 107 geçerli kampanya olduğunu ve bunlardan 65 tanesinin 14 gün içinde biteceğini, en yakınının ise 2 gün sonra sona ereceğini biliyorum; ancak hangi bankanın hangi kampanyasının bu sürece dahil olduğunu gösteren isimler elimdeki örnek

### [musteri/gecerlilik] kampanya ne zaman bitiyor
- doğrudan hitap yok (siz/kazanç/başvuru)
- somut tutar/oran yok

> Merhaba, elimdeki kayıtlarda yer alan Kuveyt Türk kampanyalarının bitiş tarihleri şöyledir: Kuveyt Türk'ün Konyalı Saat ile ilgili kampanyası 31.12.2026 tarihinde, E-Ticaret ve Tekno Girişimcilere özel Marqby fırsatı da aynı tarih olan 31.12.2026'da sona erecektir. Ayrıca İmza mağazaları için sunulan vade farksız taksit kampanyası ile Civil resmi web sitesi kampanyaları da 31.12.2026 tarihine kada

### [musteri/gecerlilik] hangi kampanyalar bu ay sona eriyor
- somut tutar/oran yok

> Elimdeki kampanya verilerinde, hangi kampanyaların bu ayın son gününde sona erdiğine dair spesifik tarih bilgisi bulunmamaktadır; verilerde sadece 14 gün içinde bitecek olan kampanyaların genel sayısı (65 adet) ve en yakın bitiş süresinin 2 gün olduğu bilgisi yer almaktadır.

Sizin için mevcut kayıtlarda en yakında bitecek fırsatları öne çıkarabilirim; örneğin Kuveyt Türk'ün "Evlenecek Olan veya Y

### [musteri/sayisal] en uzun vade kaç ay
- somut tutar/oran yok

> Elimdeki kampanya verilerinde en uzun vade süresi 48.0 aydır. Bu süre, Kuveyt Türk'ün "Evlenecek Olan veya Yeni Evli Çiftlere Kuveyt Türk'ten Müjde Evlilik Paketi" adlı ihtiyaç finansmanı kampanyasında uygulanmaktadır.

Toplamda 107 geçerli kampanya arasında bu vade süresi en yüksek seçenektir ve ortalamayı (6.61 ay) tek başına oldukça yukarı çekmektedir; yani tipik bir kampanya vadesi 48 aydan ço

### [analist/piyasa] sektörde pazar payları nasıl dağılıyor
- tablo gelmedi

> Elimdeki kampanya verilerinde sektör genelindeki pazar payı dağılımı, piyasa analizleri veya rakamsal pazar payı istatistikleri bulunmamaktadır. Mevcut kayıtlarım sadece belirli bankaların belirli dönemlerdeki kampanya detaylarını (örneğin Albaraka Türk'ün "Payını Sen Seç Finansmanı" veya Kuveyt Türk'ün e-ticaret satıcılarına yönelik "Vade Farksız 3 Taksit" kampanyası gibi) içermektedir ve bu veri

### [analist/konumlanma] biz Albaraka Türk'üz, sektördeki konumumuz ne
- boşluk/eksik analizi yok

> Albaraka Türk, katılım bankacılığı sektöründe toplam 234 aktif kampanya içinde %19.2'lik pazar payıyla (45 kampanya) Kuveyt Türk'ten sonra ikinci sırada yer almaktadır. Bu konum, sektör lideri Kuveyt Türk'ün %45.7'lik (107 kampanya) hakimiyeti karşısında, rakiplerinizden (Emlak Katılım %16.7, Vakıf Katılım %10.3) belirgin bir şekilde önde olduğunuzu göstermektedir.

Kampanya yapınıza baktığımızda,

### [analist/konumlanma] Emlak Katılım olarak hangi kategorilerde eksiğiz
- pay/sıralama rakamı yok

> Elimdeki kampanya verilerinde, Emlak Katılım Bankası'nın hangi kategorilerde "eksiği" olduğu veya hangi alanlarda hizmet vermediğine dair doğrudan bir analiz, karşılaştırma raporu veya eksiklik listesi bulunmamaktadır. Mevcut veriler sadece bankanın aktif olarak sunduğu dört spesifik kampanyayı (Emekli Müşterilere Özel Ayrıcalıklar, Debit Kart Nakit İade, Paraf Harcama Hediye ve Biletinial İndirim

### [analist/konumlanma] Hayat Finans hangi alanlarda büyüyebilir
- boşluk/eksik analizi yok

> Elimdeki mevcut kampanya verileri, Hayat Finans'ın sadece belirli ürün ve hizmet alanlarında müşteriye yönelik fırsatlar sunduğunu göstermektedir; ancak bu veriler bankanın genel stratejik büyüme hedefleri, pazar payı analizleri veya geleceğe yönelik yatırım planları hakkında teknik bir öngörü veya tavsiye içermemektedir. Verilerde öne çıkan alanlar, Xiaomi ürünleri için sunulan 3 aya varan %0 kâr

### [analist/konumlanma] TOM Katılım'ın pazar konumunu değerlendir
- boşluk/eksik analizi yok

> Elimdeki kampanya verilerinde TOM Katılım'ın genel pazar konumu, piyasa payı, rakiplerine göre sıralaması veya stratejik konumlandırması hakkında nicel veya nitel bir analiz bilgisi bulunmamaktadır. Verilerde sadece TOM Katılım'ın sunduğu belirli ürün ve kampanya detayları yer almaktadır.

Mevcut kayıtlara göre TOM Katılım, hedef kitle olarak hem mevcut müşterilere hem de yeni müşterilere yönelik 

### [analist/konumlanma] Dünya Katılım'ın portföy açığı nerede
- cevap yüzeysel (819 krktr < 900)
- pay/sıralama rakamı yok

> Elimdeki kampanya verilerinde Dünya Katılım Bankası'nın portföy açığına dair herhangi bir bilgi veya finansal analiz raporu bulunmamaktadır. Mevcut verilerim sadece Itopya, Schafer ve ADV mağazalarındaki vade farksız taksit fırsatları ile "Davet Et, Altın Kazan" referans programı gibi belirli kart ve müşteri kazanım kampanyalarına odaklanmaktadır.

Bankanın genel portföy yapısı, risk yönetimi veya

### [analist/konumlanma] Emlak Katılım'ın güçlü ve zayıf yönlerini çıkar
- boşluk/eksik analizi yok

> Elimdeki kampanya verilerine göre Emlak Katılım Bankası'nın mevcut portföyündeki güçlü yönleri, özellikle emekli segmentine yönelik özel finansman ve kâr paylaşım avantajları ile yeni müşteri kazanımına odaklanan yüksek nakit iade kampanyalarıdır. Emekli müşteriler için sunulan "Emekli Müşterilerimize Özel Ayrıcalıklar" kampanyasında, bireysel finansman taleplerinde liste fiyatlarından %5 indiriml

### [analist/konumlanma] Vakıf Katılım için 3 somut aksiyon öner
- boşluk/eksik analizi yok

> Elimdeki kampanya verilerine göre Vakıf Katılım için mevcut müşteri portföyünü harekete geçirecek üç somut aksiyon önerisi şunlardır: İlk olarak, idefix platformundaki alışveriş hacmini artırmak amacıyla VKart TROY kampanyasını öne çıkarmalı; 1.000 TL ve üzeri harcamalarda 200 TL indirim sağlayan bu fırsatla, kullanıcıların "TROY200TL" kodunu kullanarak toplamda 3.000 TL'ye varan indirim kazanması

### [analist/metrik] kâr payı oranlarını listele
- tabloda tek banka (1 satır)

> Elimdeki kampanya verilerinde sadece Kuveyt Türk'ün "Taksitlio'da Yeni Müşterilere Özel Kuveyt Türk Alışveriş Finansmanı Fırsatı" adlı kampanyası için %2.99 kâr payı oranı kayıtlıdır.

Sektördeki diğer 6 katılım bankası (Albaraka Türk, Emlak Katılım, Vakıf Katılım, Hayat Finans, TOM Katılım ve Dünya Katılım) için kâr payı oranı verisi bulunmamaktadır; bu bankaların 233 kampanyasının tamamında ilgi

### [analist/gecerlilik] süresi dolmuş kampanyalar hangileri
- pay/sıralama rakamı yok

> Elimdeki kayıtlara göre süresi dolmuş kampanyalar arasında en yüksek vade süresine sahip olan, Albaraka Türk'ün "Togg Finansmanı" kampanyasıdır ve bu kampanya 48.0 ay vade sunmaktadır.

Sektördeki süresi dolmuş 77 kampanyanın tamamı üzerinden yapılan analizde, vade verisi bulunan 53 kampanyanın ortalaması 8.66 ay iken, en düşük vade 2.0 ay olarak kaydedilmiştir; bu durum ortalamanın tek bir yüksek

### [musteri/sinir] merhaba
- doğrudan hitap yok (siz/kazanç/başvuru)

> Merhaba! Katılım bankacılığı kampanyaları ve finansman ürünleri hakkında nasıl yardımcı olabilirim?

