import re
from dataclasses import dataclass

from backend.nlp.normalizasyon import (date,duration,money,percentage)


@dataclass
class AlanBulgusu:
    deger: object   # normalize değer (float/int/date/str)
    ham: str        # metindeki orijinal ifade (kanıt)
    kural: str      # bulan kuralın adı


def _pencere(metin: str, baslangic: int, bitis: int, genislik: int = 50) -> str:
    """Eşleşmenin çevresinden ±genislik karakterlik bağlam penceresi keser."""
    return metin[max(0, baslangic - genislik): bitis + genislik].lower()


# -----------------------------------------------------------------------------
# ORANLAR: kâr payı mı, indirim mi?
# -----------------------------------------------------------------------------
_YUZDE = re.compile(r"(?:%|yüzde)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%", re.IGNORECASE)

_INDIRIM_IPUCLARI = ("indirim", "iskonto")
_KARPAYI_IPUCLARI = ("kâr payı", "kar payı", "oran")
_KARPAYI_ACIK = ("kâr pay", "kar pay", "paylaşım")
_KARPAYI_NEGATIF = ("iade", "ödül", "odul", "kazan", "mil", "puan",
                     "bonus", "çekiliş", "komisyon")


def oranlari_cikar(metin: str) -> dict[str, AlanBulgusu]:
    sonuclar: dict[str, AlanBulgusu] = {}

    for find_yuzde in _YUZDE.finditer(metin):
        pencere_get = _pencere(metin, find_yuzde.start(), find_yuzde.end())

        # DÜZELTME 1: modülün kendisi değil, içindeki fonksiyon çağrılıyor
        yuzde_get = percentage.yuzde_normalize(find_yuzde.group())

        # DÜZELTME 2: normalize edilemeyen eşleşme varsa atla, devam et
        if yuzde_get is None:
            continue

        if any(kelime in pencere_get for kelime in _INDIRIM_IPUCLARI):
            
            sonuclar.setdefault(
                "indirim_orani",
                AlanBulgusu(yuzde_get, find_yuzde.group(), "yuzde+indirim_baglami"))

        elif any(kelime in pencere_get for kelime in _KARPAYI_IPUCLARI):
            if (not any(kn in pencere_get for kn in _KARPAYI_NEGATIF)
                    or any(a in pencere_get for a in _KARPAYI_ACIK)):
                sonuclar.setdefault(
                    "kar_payi_orani",
                    AlanBulgusu(yuzde_get, find_yuzde.group(), "yuzde+oran_baglami"))

    return sonuclar


_VADE_ADAYI = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:ay|yıl|yil|sene)[a-zçğıöşü]*", re.IGNORECASE)

def pencere_sonrasi(metin:str,bitis:int,genislik:int=25):
    return metin[bitis: bitis + genislik]

def vade_cikar(metin:str) -> dict[str,AlanBulgusu]:
    for vade_iter in _VADE_ADAYI.finditer(metin):
        ifade=vade_iter.group()
        sonrasi=pencere_sonrasi(metin, vade_iter.end())

        vade_mi=(
            re.search(r"(?:aya|yıla|yila|seneye)\s*$", ifade, re.IGNORECASE)
            and sonrasi.strip().startswith("kadar")
        ) or sonrasi.strip().startswith(("vade", "kadar"))
        if vade_mi:
            deger=duration.vade_normalize(ifade)
            if deger is not None:
                return {"vade_ay": AlanBulgusu(deger, ifade, "sayi+birim+vade_baglami")}
    return {}
# -----------------------------------------------------------------------------
# TAKSİT: "3 taksit", "5 taksit fırsatı"
# -----------------------------------------------------------------------------
_TAKSIT = re.compile(r"(\d+)\s*taksit", re.IGNORECASE)


def taksit_cikar(metin: str) -> dict[str, AlanBulgusu]:
    esles = _TAKSIT.search(metin)
    if esles:
        return {"taksit_sayisi": AlanBulgusu(int(esles.group(1)), esles.group(), "sayi+taksit")}
    return {}


# -----------------------------------------------------------------------------
# TARİHLER: aralık ("22.10.2025 - 31.12.2026") veya bitiş ("31 Aralık 2026'ya kadar")
# -----------------------------------------------------------------------------

_TARIH_ARALIGI = re.compile(
    r"(\d{1,2}[./]\d{1,2}[./]\d{4})\s*-\s*(\d{1,2}[./]\d{1,2}[./]\d{4})")
_BITIS_TARIHI = re.compile(
    # "31 Aralık 2026 tarihine kadar" / "31.12.2026'ya kadar geçerli"
    r"((?:\d{1,2}\s+[a-zçğıöşü]+\s+\d{4}|\d{1,2}[./]\d{1,2}[./]\d{4}))"
    r"[a-z' ]{0,15}kadar",
    re.IGNORECASE)

def tarihleri_cikar(metin:str)->dict[str,AlanBulgusu]:
    bulgular:dict[str,AlanBulgusu]={}

    eslesen_deger=_TARIH_ARALIGI.search(metin)

    if eslesen_deger:
        baslangic,bittis=date.tarih_normalize(eslesen_deger.group(1)),date.tarih_normalize(eslesen_deger.group(2))

        if baslangic:
            bulgular["baslangic_tarihi"]=AlanBulgusu(baslangic,eslesen_deger.group(),"tarih_araligi")

        if bittis:
            bulgular["bitis_tarihi"]=AlanBulgusu(bittis,eslesen_deger.group(),"tarih_araligi")

        return bulgular

    eslesen_deger=_BITIS_TARIHI.search(metin)
    if eslesen_deger:
        bittis=date.tarih_normalize(eslesen_deger.group(1))
        if bittis:
            bulgular["bitis_tarihi"]=AlanBulgusu(bittis,eslesen_deger.group(),"tarih_bittis")
    return bulgular


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
    re.IGNORECASE)

def masraf_cikar(metin: str) -> dict[str, AlanBulgusu]:
    esles = _MASRAF_YOK.search(metin)
    if esles:
        cumle = esles.group().strip()
        return {
            # tahsis_ucreti=0.0: "masrafsız" bilgisinin sayısal karşılığı
            "tahsis_ucreti": AlanBulgusu(0.0, cumle, "masraf_yok_kalibi"),
            "masraf_bilgisi": AlanBulgusu(cumle, cumle, "masraf_yok_kalibi"),
        }
    for esles in _UCRETSIZ_HIZMET.finditer(metin):
        cumle = esles.group().strip()
        if _BANKA_HIZMETI.search(cumle) and "sms" not in cumle.lower():
            return {"masraf_bilgisi": AlanBulgusu(cumle, cumle, "ucretsiz_hizmet_kalibi")}
    return {}




_HEDEF_KALIPLARI = [
    ("maas_musterisi", re.compile(r"maaş\s+müşteri\w*|maaş[ıi]n[ıi]\s+taş[ıi]yan", re.IGNORECASE)),
    ("segment", re.compile(
        r"esnaf|çiftçi|şah[ıi]s\s+firma\w*|işletme\s+sahi\w*|işletmelere|işletmeniz\w*"
        r"|KOBİ|emekli|öğrenci", re.IGNORECASE)),
    ("yeni_musteri", re.compile(r"yeni\s+müşteri\w*|müşteri\s+ol(?:an|acak|up)\w*", re.IGNORECASE)),
    ("mevcut_musteri", re.compile(r"mevcut\s+müşteri\w*|müşterilerimize\s+özel", re.IGNORECASE)),
]
# Eşleşmenin cümlesinde dışlama dili varsa o eşleşme HEDEFLEME değildir:
# "müşteri ilişiğini sonlandırıp YENİDEN müşteri olan bireyler kampanyadan
# YARARLANAMAZ" (Hayat k69) yeni_musteri kanıtı sayılmıştı.
_HEDEF_DISLAMA = re.compile(r"yararlanamaz|katılamaz|dahil\s+değil", re.IGNORECASE)


def hedef_kitle_cikar(metin: str) -> dict[str, AlanBulgusu]:
    for etiket, desen in _HEDEF_KALIPLARI:
        for esles in desen.finditer(metin):
            oncesi = metin[max(0, esles.start() - 15): esles.start()].lower()
            sonrasi = metin[esles.end(): esles.end() + 120]
            # "Mevcut veya Yeni müşterilerimiz" = kitle sınırlaması YOK
            # (Hayat k65 yeni_musteri sanılmıştı) → bu eşleşme atlanır.
            if etiket == "yeni_musteri" and ("mevcut veya" in oncesi
                                             or "yeniden" in oncesi):
                continue
            # Eşleşmeyi izleyen ~120 karakterde dışlama fiili varsa bu bir
            # "kimler yararlanamaz" cümlesidir → atla, sonraki eşleşmeye bak.
            if _HEDEF_DISLAMA.search(sonrasi):
                continue
            return {"hedef_kitle": AlanBulgusu(etiket, esles.group(), f"hedef+{etiket}")}
    return {}


# -----------------------------------------------------------------------------
# ANA GİRİŞ NOKTASI
# -----------------------------------------------------------------------------
def kurallarla_cikar(baslik: str, metin: str) -> dict[str, AlanBulgusu]:
    """Başlık + metinden tüm alanları kural tabanlı çıkarır.

    Başlık ve metin BİRLEŞTİRİLİR: pilot veride kâr payı oranı bazen yalnız
    başlıkta geçiyor ("...%1,99 Oran Fırsatı!" başlıkta, metinde yok).

    Dönen sözlükte yalnızca BULUNAN alanlar olur; boş alanlar hibrit
    sistemde LLM katmanına devredilir (hybrid.py — sonraki adım).
    """
    tam_metin = f"{baslik or ''} . {metin or ''}"

    bulgular: dict[str, AlanBulgusu] = {}
    # Her çıkarıcı bağımsız çalışır; sonuçlar tek sözlükte birleşir.
    # update: sözlüğe diğer sözlüğün çiftlerini ekler.
    bulgular.update(oranlari_cikar(tam_metin))
    bulgular.update(vade_cikar(tam_metin))
    bulgular.update(taksit_cikar(tam_metin))
    bulgular.update(masraf_cikar(tam_metin))
    bulgular.update(tarihleri_cikar(tam_metin))
    bulgular.update(hedef_kitle_cikar(tam_metin))
    return bulgular