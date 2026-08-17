import re
from dataclasses import dataclass
from typing import Dict 

from nlp.normalizasyon import para_normalize, tarih_normalize, vade_normalize, yuzde_normalize

@dataclass
class AlanBulgusu:
    deger: object                   # Normalize edilmiş değer (float, int, str, list)
    ham_metin: str                  # Normalize edilmiş değer (float, int, str, list)
    kural: str                      # Tetiklenen kural adı
    yontem: str = "regex"           # Jüri izlenebilirliği için yöntem adı
    guven: float = 1.0              # Kural tabanlı çıkarım güven skoru
    kanit_metni: str = ""           # Cümle içi kanıt metni
    baslangic_konum: int | None = None
    bitis_konum: int | None = None
    birim: str = "metin"            # ["percent", "TL", "ay", "adet", "metin", "boolean"]
    
    
def _pencere(metin: str, baslangic: int, bitis:int, genislik: int = 50) -> str:
    """Eşleşmenin çevresinden ±genislik karakterlik bağlam penceresi keser."""
    return metin[max(0, baslangic - genislik): bitis + genislik].lower()






# -----------------------------------------------------------------------------
# ORANLAR: Kâr payı, indirim 
# -----------------------------------------------------------------------------
#k_kar_paylasım_orani -> Katılım bankalarının toplanan fonları (katılma hesapları) işletmesi sonucu elde edilen kârın, banka ile hesap sahibi arasında nasıl bölüşüleceğini gösteren yüzdesel orandır
#nakit_iade_yuzde -> Müşterinin kartlı ödeme sistemleri veya belirli üye işyerleri üzerinden yaptığı harcamalarda, harcama tutarının belirli bir yüzdesinin müşteriye nakit veya bakit olarak geri ödenmesidir.
#indirim_orani_yuzde -> Belirli ürün, hizmet veya üye işyerlerinde yapılan alımlarda, satış bedeli üzerinden uygulanan yüzdesel fiyattan düşme oranıdır.
#sfinansman_kar_orani -> Katılım bankasının müşterisine bir mal veya hizmeti peşin alıp üzerine kâr ekleyerek vadeli satması (Murabaha) veya kiralaması (İcara) işleminde uyguladığı maliyet üzeri kâr marjıdır.


_YUZDE = re.compile(r"(?:%|yüzde)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%", re.IGNORECASE)

_INDIRIM_IPUCLARI = ("indirim", "iskonto")
_KARPAYI_IPUCLARI = ("kâr payı", "kar payı", "oran")
_KARPAYI_ACIK = ("kâr pay", "kar pay", "paylaşım")
_KARPAYI_NEGATIF = ("iade", "ödül", "odul", "kazan", "mil", "puan", "bonus", "çekiliş", "komisyon", "cashback")

def oranlari_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """Metindeki yüzde ifadelerini bağlamına göre oran alanlarına dağıtır."""
    
    bulgular: Dict[str, AlanBulgusu] = {}
    for yuzde_bul in _YUZDE.finditer(metin):
        baslangic, bitis = yuzde_bul.start(), yuzde_bul.end()
        pencere = _pencere(metin, yuzde_bul.start(), yuzde_bul.end())
        yuzde_deger = yuzde_normalize(yuzde_bul.group())
        if yuzde_deger is None:
            continue
        
        if any( kelime in pencere for kelime in _INDIRIM_IPUCLARI):
            bulgular.setdefault(
                "odul_tutari",
                AlanBulgusu(
                    deger= float(yuzde_deger),
                    ham_metin=yuzde_bul.group(),
                    kural="yuzde+indirim_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=baslangic,
                    bitis_konum=bitis,
                    birim="yüzde"
                )
            )
        elif any(kelime in pencere for kelime in _KARPAYI_IPUCLARI):
            if (not any(n in pencere for n in _KARPAYI_NEGATIF)
                    or any(a in pencere for a in _KARPAYI_ACIK)):
                bulgular.setdefault(
                    "kar_payı",
                    AlanBulgusu(
                        deger= float(yuzde_deger),
                        ham_metin=yuzde_bul.group(),
                        kural="yuzde+oran_baglami",
                        kanit_metni=pencere.strip(),
                        baslangic_konum=baslangic,
                        bitis_konum=bitis,
                        birim="yüzde"        
                    )
                )
    return bulgular

# -----------------------------------------------------------------------------
# VADE VE TAKSİT: k_vade_ay, taksit
# -----------------------------------------------------------------------------
_VADE_ADAYI = re.compile(r"\d+(?:[.,]\d+)?\s*(?:ay|yıl|yil|sene)[a-zçğıöşü]*", re.IGNORECASE)
_TAKSIT = re.compile(r"(\d+)\s*(?:ay\s*)?taksit", re.IGNORECASE)


def vade_ve_taksit_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}
    
    #Taksit Sayısı Yakalama
    taksit_bul = _TAKSIT.search(metin)
    if taksit_bul:
        taksit_sayisi = int(taksit_bul.group(1))
        bulgular["taksit"] = AlanBulgusu(
            deger=taksit_sayisi,
            ham_metin=taksit_bul.group(),
            kural="sayi+taksit",
            kanit_metni=_pencere(metin, taksit_bul.start(), taksit_bul.end()),
            baslangic_konum=taksit_bul.start(),
            bitis_konum=taksit_bul.end(),
            birim="adet"
        )
    
    for vade_bul in _VADE_ADAYI.finditer(metin):
        ifade = vade_bul.group()
        baslangic, bitis = vade_bul.start(), vade_bul.end()
        sonrasi = metin[vade_bul.end(): vade_bul.end() + 25].lower().strip()

        vade_mi = (
                    re.search(r"(?:aya|yıla|yila|seneye)\s*$", ifade, re.IGNORECASE)
                    and sonrasi.strip().startswith("kadar")
                ) or sonrasi.strip().startswith(("vade", "kadar"))
        
        if vade_mi:
            deger = vade_normalize(ifade)
            if deger is not None:
                bulgular["vade"] = AlanBulgusu(
                    deger=int(deger),
                    ham_metin=ifade,
                    kural="sayi+birim+vade_baglami",
                    kanit_metni=_pencere(metin, baslangic, bitis),
                    baslangic_konum=baslangic,
                    bitis_konum=bitis,
                    birim="ay"
                )
                break
    return bulgular
        

# -----------------------------------------------------------------------------
# TUTARLAR: k_finansman_tutari, odul_tutari_tl,
#           puan_kazanc, min_harcama_tl, kisi_basi_kazanc, mgm_limit_tl,
#           min_finansman_tutari, maks_finansman_tutari, 
# -----------------------------------------------------------------------------

_TUTAR = re.compile(
    r"(?<![\d.,])(?:\d{1,3}(?:[.]\d{3})+|\d+)(?:,\d+)?\s*(?:bin|milyon)?\s*(?:TL|₺|Türk\s+Liras[ıi])[a-z']*",
    re.IGNORECASE,
)
_ODUL_IPUCLARI = re.compile(
r"\b(?:hediye|ödül|odul|çek|cek|iade|bonus|fırsat|firsat|kampanya)\b", 
    re.IGNORECASE
)
_PUAN_IPUCLARI = re.compile(
    r"\b(?:puan|worldpuan|chip|chip-para|chippara|mil|maxipuan|parafpuan|bonus\s*puan)\b", 
    re.IGNORECASE
)
_MASRAF_IPUCLARI = re.compile(r"\b(?:masraf|ücret|ucret|tahsis|dosya)")
_MASRAF_NEGATIF = re.compile(r"\büyelik|\babonelik")
_FINANSMAN_IPUCLARI = re.compile(r"\b(?:finansman|kredi(?!\s*kart)|limit)")
_FINANSMAN_NEGATIF = re.compile(r"\b(?:indirim|iade|açıl|bakiye)")

_ESIK_SONRASI = re.compile(
    r"^\s*(?:ve\s+)?(?:üzeri|üzerinde|üstü|üstünde|yukarısı|fazlası|altı\b|altında|aşağısı"
    r"|kadar\s+olan\b|aras[ıi]\b|aras[ıi]nda|-\s*\d|harca(?!ma\s+iade))",
    re.IGNORECASE
)

_ESIK_ONCESI = re.compile(r"(?:en\s+az|minimum|asgari)\s*$", re.IGNORECASE)

def tutar_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}
    
    for tutar_bul in _TUTAR.finditer(metin):
        baslangic, bitis = tutar_bul.start(), tutar_bul.end()
        pencere = _pencere(metin, baslangic, bitis, genislik=50)
        
        if _ESIK_SONRASI.match(metin[tutar_bul.end(): tutar_bul.end() + 20]):
            continue
        if _ESIK_ONCESI.search(metin[max(0, tutar_bul.start() - 12): tutar_bul.start()]):
            continue
        
        
        deger = para_normalize(tutar_bul.group())
        if deger is None:
            continue
    
        # Finansman / Kredi Tutarı
        if any(k in pencere for k in _FINANSMAN_IPUCLARI):
            bulgular.setdefault("finansman_tutari",
                AlanBulgusu(
                    deger=deger,
                    ham_metin=tutar_bul.group(),
                    kural="para+k_finansman_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=baslangic,
                    bitis_konum=bitis,
                    birim="TL"
                )
            )
        
        # Minimum Harcama Koşulu
        elif any(k in pencere for k in _ESIK_ONCESI):
            bulgular.setdefault("min_fin_tutar",
                AlanBulgusu(
                    deger=deger,
                    ham_metin=tutar_bul.group(),
                    kural="para+min_harcama_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=baslangic,
                    bitis_konum=bitis,
                    birim="TL"
                )
            )
            
        #  Puan / Worldpuan / Chip-Para
        elif any(k in pencere for k in _PUAN_IPUCLARI):
            bulgular.setdefault("puan_kazanc",
                AlanBulgusu(
                    deger=deger,
                    ham_metin=tutar_bul.group(),
                    kural="para+puan_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=baslangic,
                    bitis_konum=bitis,
                    birim="Puan"
                )                
            )
            
        # Ödül / Nakit İade
        elif any(k in pencere for k in _ODUL_IPUCLARI):
            bulgular.setdefault("odul_tutari",
                AlanBulgusu(
                    deger=deger,
                    ham_metin=tutar_bul.group(),
                    kural="para+odul_baglami",
                    kanit_metni=pencere.strip(),
                    baslangic_konum=baslangic,
                    bitis_konum=bitis,
                    birim="TL"
                ))
            
            
    return bulgular
            
        
# -----------------------------------------------------------------------------
# MASRAF DURUMU: k_tahsis_ucreti, k_masraf_bilgi, standart_masraf_tutari, standart_masraf_bilgisi
# -----------------------------------------------------------------------------

_MASRAF_YOK = re.compile(
    r"[^.!?]*(?:"
    r"masraf\w*\s+al[ıi]nmamaktad[ıi]r|masraf\w*\s+al[ıi]nmaz|masrafs[ıi]z"
    r"|ücret\w*\s+al[ıi]nmamaktad[ıi]r|ücret\w*\s+al[ıi]nmaz"
    r"|banka\s+taraf[ıi]ndan\s+karş[ıi]lan\w+"
    r")[^.!?]*[.!?]?",
    re.IGNORECASE,
)
_UCRETSIZ_HIZMET = re.compile(r"[^.!?]*ücretsiz[^.!?]*[.!?]?", re.IGNORECASE)
_BANKA_HIZMETI = re.compile(
    r"havale|eft|fast\b|komisyon|hesap\s+işletim|para\s+transfer|dosya|tahsis",
    re.IGNORECASE
)

def masraf_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    masraf_bul = _MASRAF_YOK.search(metin)
    if masraf_bul:
        cumle = masraf_bul.group().strip()
        return {
            "tahsis_ucreti": AlanBulgusu(0.0, cumle, "masraf_yok_kalibi"),
            "masraf_bilgi": AlanBulgusu(cumle, cumle, "masraf_yok_kalibi"),
        }
    for masraf_bul in _UCRETSIZ_HIZMET.finditer(metin):
        cumle = masraf_bul.group().strip()
        if _BANKA_HIZMETI.search(cumle) and "sms" not in cumle.lower():
            return {"masraf_bilgi": AlanBulgusu(cumle, cumle, "ucretsiz_hizmet_kalibi")}
    return {}


# -----------------------------------------------------------------------------
# TARİHLER: baslangic_tarihi, bitis_tarihi, sure_gun
# -----------------------------------------------------------------------------

_TARIH_ARALIGI = re.compile(
    r"(\d{1,2}[./]\d{1,2}[./]\d{4})\s*-\s*(\d{1,2}[./]\d{1,2}[./]\d{4})"
)
_BITIS_TARIHI = re.compile(
    r"((?:\d{1,2}\s+[a-zçğıöşü]+\s+\d{4}|\d{1,2}[./]\d{1,2}[./]\d{4}))"
    r"[a-z' ]{0,15}kadar",
    re.IGNORECASE,
)


from datetime import datetime
from typing import Dict

def tarihleri_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}

    tarih_bul = _TARIH_ARALIGI.search(metin)
    if tarih_bul:
        bas, bit = tarih_normalize(tarih_bul.group(1)), tarih_normalize(tarih_bul.group(2))
        if bas:
            bulgular["baslangic_tarihi"] = AlanBulgusu(bas, tarih_bul.group(), "tarih_araligi")
        if bit:
            bulgular["bitis_tarihi"] = AlanBulgusu(bit, tarih_bul.group(), "tarih_araligi")

        # Başlangıç ve bitiş tarihlerinin her ikisi de mevcutsa süreyi hesapla
        if bas and bit:
            # Eğer tarih_normalize string döndürüyorsa datetime'a çevir:
            # bas_dt = datetime.strptime(bas, "%Y-%m-%d")
            # bit_dt = datetime.strptime(bit, "%Y-%m-%d")
            # sure = (bit_dt - bas_dt).days

            # datetime nesnesi dönüyorsa doğrudan çıkar:
            sure = abs((bit - bas).days)
            bulgular["sure_gun"] = AlanBulgusu(sure, tarih_bul.group(), "hesaplanmis_sure")

        return bulgular

    tarih_bul = _BITIS_TARIHI.search(metin)
    if tarih_bul:
        bit = tarih_normalize(tarih_bul.group(1))
        if bit:
            bulgular["bitis_tarihi"] = AlanBulgusu(bit, tarih_bul.group(), "tarih+kadar_kalibi")

    return bulgular


# -----------------------------------------------------------------------------
# HEDEF KİTLE: hedef_kitle
# -----------------------------------------------------------------------------

import re
from typing import Dict

_HEDEF_KALIPLARI = [
    ("maas_musterisi", re.compile(r"maaş\s+müşteri\w*|maaş[ıi]n[ıi]\s+taş[ıi]yan", re.IGNORECASE)),
    ("özel", re.compile(
        r"esnaf|çiftçi|şah[ıi]s\s+firma\w*|işletme\s+sahi\w*|işletmelere|işletmeniz\w*"
        r"|KOBİ|emekli|öğrenci", re.IGNORECASE)),
    #("yeni_musteri", re.compile(r"yeni\s+müşteri\w*|müşteri\s+ol(?:an|acak|up)\w*", re.IGNORECASE)),
    ("yeni_musteri", re.compile(
                r"mü[şs]teri(si|miz)?\s+ol|yeni\s+.*mü[şs]teri|davet"
                r"|ho[şs]\s*geldin|arkada[şs][ıi]n[ıi]\s+getir|yak[ıi]n[ıi]n[ıi]"
                r"|gelenlere|müşteri\s+kazan|kazandır|(türklü|finanslı|katılımlı)\s+ol",
                re.IGNORECASE,
            )),
    ("mevcut_musteri", re.compile(r"mevcut\s+müşteri\w*|müşterilerimize\s+özel", re.IGNORECASE)),
    # 'Tüm müşteriler' için yeni regex deseni:
    ("tum_musteriler", re.compile(r"tüm\s+müşteri\w*|herkes|bütün\s+müşteri\w*", re.IGNORECASE)),
]

_HEDEF_DISLAMA = re.compile(r"yararlanamaz|katılamaz|dahil\s+değil", re.IGNORECASE)


def hedef_kitle_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    bulgular: Dict[str, AlanBulgusu] = {}

    
    # Hedef Kitle Tespiti
    for etiket, desen in _HEDEF_KALIPLARI:
        for esles in desen.finditer(metin):
            oncesi = metin[max(0, esles.start() - 15): esles.start()].lower()
            sonrasi = metin[esles.end(): esles.end() + 120]

            if etiket == "yeni_musteri" and ("mevcut veya" in oncesi or "yeniden" in oncesi):
                continue
            if _HEDEF_DISLAMA.search(sonrasi):
                continue

            bulgular["hedef_kitle"] = AlanBulgusu(
                deger=etiket, ham_metin=esles.group(), kural=f"hedef+{etiket}"
            )
            return bulgular  # İlk geçerli eşleşmede sonucu döndürür

    return bulgular

# -----------------------------------------------------------------------------
# KAMPANYA TÜRÜ
# -----------------------------------------------------------------------------

_KAMPANYA_TURU: tuple[tuple[str, str, re.Pattern], ...] = (
    # 1. İhtiyaç Finansmanı Kampanyası
    (
        "ihtiyac_finansmani_kampanyasi",
        "hepsi",
        re.compile(r"ihtiya[çc]\s+(finansman|kart|kredi)", re.IGNORECASE),
    ),
    # 2. Konut Finansmanı Kampanyası
    (
        "konut_finansmani_kampanyasi",
        "hepsi",
        re.compile(r"(konut|ev)\s+(finansman|kredi)|mortgage", re.IGNORECASE),
    ),
    # 3. Taşıt Finansmanı Kampanyası
    (
        "tasit_finansmani_kampanyasi",
        "hepsi",
        re.compile(r"(ta[şs][ıi]t|ara[çc]|oto)\s+(finansman|kredi)", re.IGNORECASE),
    ),
    # 6. Yatırım Ürünleri Kampanyası
    (
        "yatirim_urunleri_kampanyasi",
        "baslik",
        re.compile(r"günlük\s+hesap", re.IGNORECASE),
    ),
    (
        "yatirim_urunleri_kampanyasi",
        "erken",
        re.compile(
            r"kat[ıi]l[ıi]?ma?\s+hesab|yat[ıi]r[ıi]m\s+hesab"
            r"|\bbes\b|emeklilik\s+plan|döviz"
            r"|k[ıi]ymetli\s+maden|gümü[şs]|alt[ıi]n\s+hesab"
            r"|getiri\s+oran|payla[şs][ıi]m\s+oran|kur\s+f[ıi]rsat"
            r"|benzersiz\s+kur",
            re.IGNORECASE,
        ),
    ),
    # 7. Kart Kampanyası
    (
        "kart_kampanyasi",
        "hepsi",
        re.compile(
            r"taksit|indirim|\bkartl?a?\b|kredi\s+kart|debit|troy"
            r"|mastercard|visacard|qr\s+öde|harcama|parafpara|worldpuan"
            r"|puan|\bmil\b|mil'e|\biade\b|bonus|kazand[ıi]ran"
            r"|(harcad[ıi]k[çc]a|yapt[ıi]k[çc]a)\s+kazan",
            re.IGNORECASE,
        ),
    ),
)
def kategori_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    birlesik = f"{baslik} {metin}"

    for kat_turu, desen in _KAMPANYA_TURU:
        eslesme = desen.search(birlesik)

        if eslesme:
            return {
                "tur": AlanBulgusu(
                    deger=kat_turu,
                    ham_metin=eslesme.group(),
                    kural=f"kampanya_turu_{kat_turu}",
                    kanit_metni=eslesme.group(),
                    baslangic_konum=eslesme.start(),
                    bitis_konum=eslesme.end(),
                    birim="metin"
                )
            }

    return {}

_MGM_KALIBI = re.compile(
    r"davet\s+et|arkadaşı|getir\s+kazan|referans\s+ol|arkadaşını\s+davet", 
    re.IGNORECASE
)

def mgm_cikar(metin: str) -> Dict[str, AlanBulgusu]:
    """
    Metin içinde MGM (Member Get Member / Arkadaşını Getir) kampanyası
    olup olmadığını kontrol eder. Varsayılan olarak 'deger=False' döner.
    """
    eslesme = _MGM_KALIBI.search(metin)
    
    if eslesme:
        return {
            "is_mgm": AlanBulgusu(
                deger=True, 
                ham_metin=eslesme.group(), 
                kural="mgm_kalibi", 
                birim="boolean"
            )
        }
    
    return {
        "is_mgm": AlanBulgusu(
            deger=False, 
            ham_metin="", 
            kural="mgm_kalibi", 
            birim="boolean"
        )
    }





# -----------------------------------------------------------------------------
# ANA GİRİŞ NOKTASI
# -----------------------------------------------------------------------------
def kurallarla_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    """
    Başlık ve metinden tüm alanları yüksek kesinlikli kurallarla çıkarır.
    Yalnızca tespit edilen alanları döndürür. Eksik kalan alanlar hybrid.py
    içinde belirlenip sadece o eksikler için LLM çağrısı yapılır.
    """
    tam_metin = f"{baslik or ''} . {metin or ''}"

    bulgular: dict[str, AlanBulgusu] = {}

    # Çıkarıcıları sırayla çalıştırıp birleştir
    bulgular.update(oranlari_cikar(tam_metin))
    bulgular.update(vade_ve_taksit_cikar(tam_metin))
    bulgular.update(tutar_cikar(tam_metin))
    bulgular.update(tarihleri_cikar(tam_metin))
    bulgular.update(masraf_cikar(tam_metin))
    bulgular.update(hedef_kitle_cikar(tam_metin))
    bulgular.update(kategori_cikar(baslik or "", metin or ""))
    bulgular.update(mgm_cikar(tam_metin))

    return bulgular