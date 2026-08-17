# =============================================================================
# urun_kurallari.py — ÜRÜN Sayfaları için Alan Çıkarımı (34. adım)
# =============================================================================
#
# NEDEN KAMPANYA KURALLARI KULLANILMIYOR? (rule_based.py dururken)
# ----------------------------------------------------------------
# Denendi ve ÖLÇÜLDÜ (2026-07-21, Kuveyt Türk ürün sayfaları). Kampanya için
# kalibre edilmiş kurallar ürün metninde SESSİZCE YANLIŞ değer üretti:
#   - Konut Finansmanı → kar_payi_orani = 75.0
#     Kaynak cümle: "...malik olduğu en az bir konut bulunması durumunda
#     kullanabileceği finansman tutarı %75 ORANINDA AZALMAKTADIR." Bu bir
#     düşürme oranı; "oran" ipucu kâr payı sanmıştı.
#   - Araç/Eğitim Finansmanı → kar_payi_orani = 0.0
#     Kaynak: boş hesaplama widget'ının "%0" placeholder'ı (artık ön işlemede
#     siliniyor — cleaner.hesap_araci_sil).
#   - Eğitim Finansmanı → masraf_muafiyet_tutari = 1.194,41 TL
#     Kaynak: örnek ödeme planındaki TOPLAM KÂR PAYI tutarı.
# Sebep yapısal: kampanya metni bir VAAT dilidir ("%1,99 oranla 12 ay"),
# ürün metni bir KÜNYE dilidir ("azami vade 120 ay", "tahsis ücreti tutarın
# binde beşi") ve yanında ürünü ANLATAN uzun bir düzyazı taşır. Aynı desenler
# iki dilde aynı şeyi ifade etmiyor.
#
# TASARIM İLKESİ — ÇAPALI (ANCHORED) KURALLAR:
# Kampanya tarafı "yüzdeyi bul, çevresine bakıp alan ata" der (metin kısa,
# yüzde az). Ürün tarafında bu ters çalışır: sayfada onlarca yüzde var (SSS,
# düzyazı, oran tabloları). Bu yüzden ürün kuralları TERSTEN kurulur: önce
# ALANIN ADI aranır ("tahsis ücreti", "maksimum finansman tutar oranları"),
# sonra o çapanın PENCERESİNDE sayı aranır. Çapa yoksa alan NULL kalır.
# "Eksik > yanlış" (18. adım) ilkesinin ürün tarafındaki uygulaması.
#
# ÇIKARILAN ALANLAR (db.models.Urun kolonlarıyla birebir):
#   urun_turu, azami_vade_ay, azami_finansman_orani, tahsis_ucreti_orani
# =============================================================================

import re

from nlp.classification.campaign_classifier import siniflandir
from nlp.extraction.rule_based import AlanBulgusu
from nlp.normalization.percentage import yuzde_normalize

# -----------------------------------------------------------------------------
# ÜRÜN TÜRÜ: bankanın KENDİ taksonomisi (URL kategorisi) birinci kaynaktır
# -----------------------------------------------------------------------------
# Ürün sayfasının adresi zaten sınıflandırılmış bilgi taşıyor:
#   /kendim-icin/finansmanlar/konut-finansmanlari/konut-finansmani
# Bunu metinden tahmin etmeye çalışmak, elimizdeki kesin veriyi olasılıksal
# bir sürece yeniden ürettirmek olurdu (chatbot'ta LLM'e sıralama sordurmama
# kararının aynısı). Kural > model, veri > tahmin.
KATEGORI_TUR_ESLEME = {
    "konut-finansmanlari": "konut_finansmani",
    "arac-finansmanlari": "tasit_finansmani",
    "ihtiyac-finansmanlari": "ihtiyac_finansmani",
    # Alışveriş finansmanı taksonomide karşılıksız: kampanya tarafındaki
    # "alisveris_puani" ödül kampanyasıdır (puan/iade), bu ise bir FİNANSMAN
    # ürünü. Genel "finansman" kovasına düşer — yeni etiket açmak, kampanya
    # ile ürünün tür kümesini ayırırdı; oysa chatbot ikisini TEK filtreyle
    # tarıyor (urun_turu_sorusu).
    "alisveris-finansmanlari": "finansman",
    # "surdurulebilir-finansmanlar" BİLİNÇLİ OLARAK YOK: bu kategori bir ürün
    # türü değil, bir NİTELİK kovası — içinde Yeşil KONUT Finansmanı da,
    # Sürdürülebilir ARAÇ Finansmanı da, Çatı GES Finansmanı da var.
    # Kategoriye bakıp hepsine tek tür vermek üçünü de yanlış etiketlerdi;
    # bu kategori metin sınıflandırıcısına düşer (aşağıdaki geri düşüş).
}


def urun_turu_belirle(kategori: str | None, baslik: str,
                      metin: str) -> AlanBulgusu | None:
    """Ürün türü: önce URL kategorisi, eşleşme yoksa metin sınıflandırıcısı.

    Geri düşüş yolu, kampanya tarafındaki sınıflandırıcının TA KENDİSİDİR
    (nlp.classification.campaign_classifier) — iki tarafın etiket kümesi
    ayrışmasın diye. LLM kapalı çağrılır: ürün başlıkları kısa ve açıktır
    ("Yeşil Konut Finansmanı"), kural katmanı yetiyor; yetmezse NULL kalması
    yanlış etiketten iyidir.
    """
    if kategori and kategori in KATEGORI_TUR_ESLEME:
        tur = KATEGORI_TUR_ESLEME[kategori]
        return AlanBulgusu(tur, f"URL kategorisi: {kategori}",
                           f"urun_kategorisi:{kategori}")
    return siniflandir(baslik, metin, llm_aktif=False)


# -----------------------------------------------------------------------------
# CÜMLE AYIRMA: çapalı kuralların çalışma birimi
# -----------------------------------------------------------------------------
# Ürün metni düzyazıdır; bir cümlede geçen sayı, komşu cümlenin alanına
# yazılmamalı. Nokta+boşluk yeterli bir ayraç: metin ön işlemeden tek satır
# hâlinde geliyor. Ondalık ayracı olan noktalar ("10.000") sayı içinde
# kaldığı için (?<=\d)\.(?=\d) durumunu dışlamak gerekir.
_CUMLE_AYRACI = re.compile(r"(?<!\d)\.(?:\s+|$)")


def _cumleler(metin: str) -> list[str]:
    return [c.strip() for c in _CUMLE_AYRACI.split(metin or "") if c.strip()]


# -----------------------------------------------------------------------------
# AZAMİ VADE: "120 aya kadar vade", "maksimum 48 ay vade", "en fazla 24 ay"
# -----------------------------------------------------------------------------
# Ürün sayfası tek bir vade ilan etmez, ÜST SINIR ilan eder ve çoğu zaman
# birden fazla alt sınır sayar ("0-5 yaş araçlar için maksimum 48 ay, 6-10
# yaş araçlar için maksimum 36 ay"). Bu yüzden EN BÜYÜĞÜ alınır: ürünün
# "azami vadesi" tanımı gereği en uzun seçenektir.
_VADE_KALIPLARI = (
    re.compile(r"(\d{1,3})\s*ay[ae]?\s+kadar\s+vade", re.IGNORECASE),
    re.compile(r"(?:maksimum|azami|en\s+fazla)\s+(\d{1,3})\s*ay", re.IGNORECASE),
    re.compile(r"(\d{1,3})\s*ay\s+vade\s+ile", re.IGNORECASE),
    re.compile(r"vade(?:si|niz)?\s+(?:en\s+fazla\s+)?(\d{1,3})\s*ay", re.IGNORECASE),
)


def azami_vade_cikar(metin: str) -> dict[str, AlanBulgusu]:
    """Metindeki vade üst sınırlarının EN BÜYÜĞÜ.

    SORU CÜMLELERİ ELENİR: pazarlama metni "36 ay vadeye mi ihtiyaç
    duyuyorsunuz?" diye sorabiliyor (Alışveriş Finansmanı) — bu bir ilan
    değil, retorik. Ürünün gerçek sınırı düz cümlede yazılır.
    """
    en_iyi: tuple[int, str] | None = None
    for cumle in _cumleler(metin):
        if cumle.rstrip().endswith("?"):
            continue
        for desen in _VADE_KALIPLARI:
            for esles in desen.finditer(cumle):
                ay = int(esles.group(1))
                # 600 ay (50 yıl) üstü bir vade gerçekçi değil: yanlış
                # yakalanmış bir sayıdır, alınmaz.
                if 0 < ay <= 600 and (en_iyi is None or ay > en_iyi[0]):
                    en_iyi = (ay, esles.group().strip())
    if en_iyi is None:
        return {}
    return {"azami_vade_ay": AlanBulgusu(en_iyi[0], en_iyi[1], "urun_capa:azami_vade")}


# -----------------------------------------------------------------------------
# TAHSİS ÜCRETİ ORANI: "tahsis ücreti finansman tutarının 0,5%'i (binde beş)"
# -----------------------------------------------------------------------------
# Kampanyada tahsis ücreti TL'dir ("500 TL tahsis ücreti"), üründe ORANDIR.
#
# ÇAPADAN YALNIZ İLERİYE BAKILIR — ilk sürümün ölçülmüş hatası (2026-07-21):
# kural "aynı cümlede yüzde ara" diyordu ve dört üründe (Eğitim, Hac-Umre,
# Seyahat, Tekne) tahsis oranını %4,82 buldu. Kaynak, çapadan ÖNCE gelen örnek
# ödeme planı tablosunun kâr oranı hücresiydi:
#   "...10.000 TL 12 Ay 4,82 % 1.194,41 TL ... 105,4413% Tahsis ücreti,
#    finansman tutarının %0,5'i kadardır."
# Tabloda nokta yok, dolayısıyla cümle ayracı da yok — tablo ile cümle tek
# "cümle" gibi görünüyor. Türkçe'de niteleyen sayı, nitelenen ifadeden SONRA
# gelir ("tahsis ücreti ... tutarının %0,5'i"); kuralı yöne duyarlı yapmak
# hem dilbilgisel hem ölçülmüş olarak doğrudur.
#
# "sigorta ve tahsis ücreti yansıtılmayacaktır" gibi ücretsizlik cümlelerinde
# yüzde olmadığı için kural sessizce eşleşmez (NULL kalır) — muafiyet bilgisi
# masraf_bilgisi alanına düşer, orana 0 yazılmaz (0 "binde sıfır" demektir,
# "ücret alınmıyor" demek değil; ikisini karıştırmak yanlış veri olurdu).
_YUZDE_IFADESI = re.compile(r"(?:%\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%)")
# Pencere 120 karakter: en uzun gerçek örnek "Finansman tahsis ücreti; ticari
# nitelikli finansmanlarda finansman tutarı üzerinden maksimum %1.10" (Arsa
# Finansmanı) 88 karakterde tamamlanıyor. Nokta görülürse pencere orada biter
# ([^.]* ile) — sonraki cümleye taşma imkânsız.
_TAHSIS_ORANI = re.compile(
    r"tahsis\s+ücreti[^.]{0,120}?(%\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%)",
    re.IGNORECASE)


def tahsis_orani_cikar(metin: str) -> dict[str, AlanBulgusu]:
    for esles in _TAHSIS_ORANI.finditer(metin or ""):
        deger = yuzde_normalize(esles.group(1))
        # Tahsis ücreti oranı %10'u aşamaz (mevzuat da çok altında tutar):
        # daha büyük bir sayı, cümlede geçen BAŞKA bir orandır.
        if deger is not None and 0 < deger <= 10:
            return {"tahsis_ucreti_orani": AlanBulgusu(
                deger, esles.group()[:200], "urun_capa:tahsis_orani")}
    return {}


# -----------------------------------------------------------------------------
# AZAMİ FİNANSMAN ORANI: teminat değerine oranla verilebilecek en yüksek pay
# -----------------------------------------------------------------------------
# Konut ürününün en ayırt edici sayısı ve bir TABLO içinde yaşıyor:
#   "Sıfır ve ikinci el konutlar için kullanılabilecek maksimum finansman
#    tutar oranları aşağıdaki tabloda yer almaktadır. Ekspertiz Değeri/Enerji
#    Sınıfı A-B Sınıfı C Sınıfı Diğer 5 milyona kadar konutlar %22,5 %20 ..."
# Tablo düz metne serildiği için hücre ilişkisi (hangi oran hangi sınıfa)
# KAYBOLUYOR. Bu yüzden tek bir sayı iddia edilmez: tablodaki EN YÜKSEK oran
# "azami" olarak alınır — tanım gereği doğru olan tek özet budur, kanıt
# olarak da çapa cümlesi saklanır (kullanıcı tabloyu kaynaktan görebilir).
_ORAN_TABLOSU_CAPASI = re.compile(
    r"(?:maksimum|azami|en\s+fazla)\s+finansman(?:\s+tutar[ıi]?)?\s+oran"
    r"|finansman\s+tutar[ıi]\s+oranlar[ıi]", re.IGNORECASE)
# Çapadan sonraki pencere: ölçülen tablo 5 satır × 3 sütun = 15 oran,
# ~220 karakter. 400 rahat sığdırır, sonraki bölüme taşmaz.
_TABLO_PENCERESI = 400


def azami_finansman_orani_cikar(metin: str) -> dict[str, AlanBulgusu]:
    esles = _ORAN_TABLOSU_CAPASI.search(metin or "")
    if not esles:
        return {}
    pencere = metin[esles.end(): esles.end() + _TABLO_PENCERESI]
    oranlar = [yuzde_normalize(y.group()) for y in _YUZDE_IFADESI.finditer(pencere)]
    oranlar = [o for o in oranlar if o is not None and 0 < o <= 100]
    if not oranlar:
        return {}
    return {"azami_finansman_orani": AlanBulgusu(
        max(oranlar), metin[esles.start(): esles.end() + 120],
        "urun_capa:azami_finansman_orani")}


# -----------------------------------------------------------------------------
# MASRAF BİLGİSİ: ücret/masraf cümlelerinin serbest metin özeti
# -----------------------------------------------------------------------------
# Sayıya indirgenemeyen ama kullanıcıyı ilgilendiren bilgi ("ipotek tesis
# bedeli", "sigorta ve tahsis ücreti yansıtılmayacaktır"). Yorum yapılmaz,
# cümleler OLDUĞU GİBİ taşınır — özetleme LLM işidir ve burada gereksiz risk.
_MASRAF_CAPASI = re.compile(
    r"\b(?:tahsis\s+ücreti|dosya\s+masraf|ipotek\s+tesis|ekspertiz\s+ücret"
    r"|sigorta\s+(?:ücret|bedel)|masrafs[ıi]z|ücretsiz)", re.IGNORECASE)


def masraf_bilgisi_cikar(metin: str) -> dict[str, AlanBulgusu]:
    cumleler = [c for c in _cumleler(metin) if _MASRAF_CAPASI.search(c)]
    if not cumleler:
        return {}
    ozet = ". ".join(cumleler[:3])[:500]
    return {"masraf_bilgisi": AlanBulgusu(ozet, ozet[:200], "urun_capa:masraf")}


# -----------------------------------------------------------------------------
# GİRİŞ NOKTASI
# -----------------------------------------------------------------------------
def urun_kurallarla_cikar(baslik: str, metin: str,
                          kategori: str | None = None) -> dict[str, AlanBulgusu]:
    """Bir ürün sayfasının tüm çapalı kurallarını çalıştırır.

    Dönen sözlüğün anahtarları db.models.Urun kolon adlarıdır (pipeline
    doğrudan setattr eder — kampanya boru hattındaki ALAN_KOLON_ESLEME
    dolaylılığı burada gereksiz: ürün alanları zaten kolon adıyla üretiliyor).
    """
    bulgular: dict[str, AlanBulgusu] = {}
    bulgular.update(azami_vade_cikar(metin))
    bulgular.update(tahsis_orani_cikar(metin))
    bulgular.update(azami_finansman_orani_cikar(metin))
    bulgular.update(masraf_bilgisi_cikar(metin))
    tur = urun_turu_belirle(kategori, baslik, metin)
    if tur:
        bulgular["urun_turu"] = tur
    return bulgular
