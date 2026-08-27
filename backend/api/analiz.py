"""FinAgent ANALİZ KÖPRÜSÜ — arayüzdeki "FinAgent'a Sor" butonlarının arkası.

🚨 NEDEN VAR — ÖNCEKİ AKIŞIN ÜÇ KUSURU

Dashboard ve Finansman sayfalarındaki butonlar, sohbete gidecek metnin TAMAMINI
tarayıcıda kuruyordu (`dashboard.vue::goToChat`, `finansman.vue::askAiAboutProduct`):

    "Kuveyt Türk için ... Toplam Aktif Kampanya Sayısı: 107, Baskın Kategori:
     Kart (%64,3), Kategori Dağılımı: Konut: 1 adet (Ort. Süre: 6 ay) ...
     Analiz Talebi: Pazar konumunu analiz et."

  1) VERİ DOĞRULANMIYORDU. Bu rakamlar tarayıcının KENDİ sezgisiyle üretiliyor
     (`getCategoryCounts` kampanya ADINDA "konut"/"taşıt" arıyor). Backend'in
     Mongo'daki gerçek `kampanya_turu` alanıyla çakıştığında model, YANLIŞ bir
     rakamı "kesin veri" diye sunulmuş hâlde alıyor ve güvenle tekrarlıyordu.
     Bir bankacılık asistanında en pahalı hata türü budur: yanlış bilgi,
     doğruymuş gibi biçimlendirilmiş olarak geliyor.

  2) SOHBET HATTI DEVRE DIŞI KALIYORDU. 500+ karakterlik bu veri bloğu bir soru
     gibi görünmüyor; niyet motoru (chatbot.intent) onu sınıflandıramıyor,
     dolayısıyla Mongo tablosu/grafiği ÜRETİLMİYOR. Kullanıcı "FinAgent'a Sor"
     diyor ama sohbetin en güçlü tarafını (doğrulanmış tablo + piyasa
     fotoğrafı) hiç görmüyordu.

  3) İKİ AYRI MEKANİZMA. Dashboard `chatStore.setChatData`, Finansman ise
     `sessionStorage`+`finagent_auto_send` kullanıyordu; ikisi de serbest
     kullanıcı metnini (customPrompt) doğrudan prompt'a gömüyordu.

ÇÖZÜM: Arayüz artık metin DEĞİL, YAPILANDIRILMIŞ İSTEK gönderiyor (analiz türü
+ banka kodları / ürün kimliği). Bu uç:
    • banka kodlarını KENDİ verimizle doğruluyor (tanınmayanı reddediyor),
    • rakamları Mongo'dan YENİDEN hesaplıyor (tarayıcının sayısına güvenmiyor),
    • finansman ürününde arayüzün gönderdiği oran/taksit ile kayıtlıyı
      KARŞILAŞTIRIYOR, uyuşmazsa BİZİMKİNİ kullanıp düzeltmeyi raporluyor,
    • sonuçta KISA ve DOĞAL bir soru üretiyor ki `/api/chat` hattı devreye
      girsin ve tabloyu/piyasa analizini kendi doğrulanmış verisinden üretsin.

Yani bu uç cevabı üretmiyor; SORUYU GÜVENLİ HÂLE GETİRİP sohbete devrediyor.
"""
import os
import re
from typing import Any, List, Optional

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from pymongo import MongoClient

from chatbot.intent import (
    BANKA_GORUNEN_ADLARI,
    banka_adi_getir,
    banka_kodu_coz,
    banka_kodu_normalize,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
DB_ADI = os.getenv("CAMPAIGN_DB", "smartdata")

def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    if MONGO_PASSWORD:
        return f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    return f"mongodb://{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

MONGO_URI = _get_mongo_uri()

router = APIRouter(tags=["analiz"])

# Serbest metin sınırı: buton akışında kullanıcı bir SORU yazar, doküman değil.
MAKS_SERBEST_SORU = 400
# En fazla kaç banka aynı anda kıyaslanabilir. Üstü hem tabloyu okunmaz yapıyor
# hem de dengeli dilimde banka başına 1-2 satır bırakıyor (kıyas anlamsızlaşır).
MAKS_BANKA = 6

_ANALIZ_METINLERI = {
    # tek banka
    "rekabet_durumu": "{bankalar} bankasının sektördeki pazar konumunu ve rekabet stratejisini analiz et.",
    "baskin_kategori": "{bankalar} bankasının en yoğun olduğu kampanya kategorisindeki ağırlığını ve hangi kategorilerde büyüme fırsatı olduğunu değerlendir.",
    "trend_analizi": "{bankalar} bankasının kampanya sürelerini ve lansman yoğunluğunu sektör geneliyle karşılaştır.",
    # çok banka
    "karsilastirma": "{bankalar} bankalarının kampanya portföylerini ve pazar rekabetini karşılaştır.",
    "pazar_lideri": "{bankalar} arasında kampanya sayısı ve çeşitlilik bakımından pazar lideri hangisi?",
    "kategori_ayrisim": "{bankalar} bankalarının kategori bazında ortak ve ayrışan kampanya stratejilerini analiz et.",
}

_ANALIZ_METINLERI_EN = {
    "rekabet_durumu": "Analyse the market position and competitive strategy of {bankalar}.",
    "baskin_kategori": "Assess where {bankalar} is concentrated by campaign category and where it has room to grow.",
    "trend_analizi": "Compare campaign durations and launch intensity of {bankalar} against the sector.",
    "karsilastirma": "Compare the campaign portfolios and market competition of {bankalar}.",
    "pazar_lideri": "Among {bankalar}, which one leads on campaign count and variety?",
    "kategori_ayrisim": "Analyse the shared and diverging category strategies of {bankalar}.",
}

# Serbest metinde talimat enjeksiyonu belirtisi. Engellemiyoruz — bu uç zaten
# metni SORU olarak sarmalıyor — ama işaretleyip logluyoruz.
_SUPHELI_METIN = re.compile(
    r"[şs]imdiye kadarki|[öo]nceki .{0,20}talimat|ignore .{0,20}instruction|"
    r"sistem prompt|system prompt|kendini .{0,20}tan[ıi]t|rol[üu]n[üu] de[ğg]i[şs]tir|"
    r"\[s[iİ]stem|###\s*s[iİ]stem|act as",
    re.IGNORECASE,
)


# 🛠️ ARAYÜZ SAYILARI METİN OLARAK GELİYOR.
# Sayfalardaki tablolar kullanıcıya GÖRÜNEN biçimi tutuyor ("%38,50",
# "100.000 TL", "36 Ay") ve butonlar bu değerleri olduğu gibi gönderiyor.
# Modeller ise düz `float` bekliyordu; sonuç 422 "unable to parse string as a
# number" idi. Katılım hesabı butonu bu yüzden HER TIKLAMADA köprüye
# ulaşamayıp sessizce doğrulanmamış yedek prompt'a düşüyordu — yani buton
# duruyor ama arkasındaki doğrulama hiç çalışmıyordu.
# `_sayi()` bu biçimleri zaten çözüyordu; artık modellere bağlı.
def _metinden_sayi(v):
    return _sayi(v) if isinstance(v, str) else v


def _metinden_tamsayi(v):
    s = _sayi(v) if isinstance(v, str) else v
    return int(s) if isinstance(s, float) else s


class FinansmanUrunGirdisi(BaseModel):
    """Finansman sayfasındaki bir satırın kimliği. Rakamlar DOĞRULAMA içindir —
    prompt'a arayüzün değil, BİZİM kayıtlarımızdaki değer yazılır."""
    banka: Optional[str] = None
    urun: Optional[str] = None                 # ihtiyac | konut | tasit
    tutar: Optional[float] = None
    vade: Optional[int] = None
    kar_orani: Optional[float] = None          # arayüzün gösterdiği oran (doğrulanacak)
    aylik_taksit: Optional[str] = None

    @field_validator("tutar", "kar_orani", mode="before")
    @classmethod
    def _sayisal(cls, v):
        return _metinden_sayi(v)

    @field_validator("vade", mode="before")
    @classmethod
    def _vade(cls, v):
        return _metinden_tamsayi(v)


class KatilimHesapGirdisi(BaseModel):
    """Katılım hesapları sayfasındaki bir satırın kimliği."""
    banka: Optional[str] = None
    tutar: Optional[float] = None
    vade: Optional[str] = None
    net_oran: Optional[float] = None
    brut_oran: Optional[float] = None
    net_kar: Optional[str] = None

    @field_validator("tutar", "net_oran", "brut_oran", mode="before")
    @classmethod
    def _sayisal(cls, v):
        return _metinden_sayi(v)

    @field_validator("vade", "net_kar", mode="before")
    @classmethod
    def _metin(cls, v):
        return None if v is None else str(v)


class AnalizIstegi(BaseModel):
    kaynak: str = Field("dashboard", description="dashboard | finansman | katilim_hesap")
    tur: str = Field("karsilastirma", description="analiz türü ya da 'serbest'")
    bankalar: List[str] = Field(default_factory=list)
    urun: Optional[FinansmanUrunGirdisi] = None
    katilim_hesap: Optional[KatilimHesapGirdisi] = None
    soru: Optional[str] = None                 # serbest metin
    dil: str = "tr"


# finansman_urun koleksiyonu KISA banka kodları kullanıyor ("vakif", "ziraat",
# "kuveyt"); kampanya tarafı UZUN kodlar ("vakif_katilim", "kuveytturk").
# Bu eşleme olmadan `banka_adi_getir` adı çözemiyor ve prompt'a ham kod
# yazılıyordu ("vakif'ın 200.000 TL..." gibi).
_KISA_KOD_ESLEME = {
    "vakif": "vakif_katilim",
    "ziraat": "ziraat_katilim",
    "kuveyt": "kuveytturk",
}


def _uzun_kod(ham) -> Optional[str]:
    """Finansman kaydındaki banka kodunu tanınan uzun koda çevirir."""
    if not ham:
        return None
    duz = str(ham).strip().lower()
    return _KISA_KOD_ESLEME.get(duz) or banka_kodu_normalize(duz)


def _tr_sayi(deger: Optional[float], ondalik: int = 0) -> str:
    """Türkçe sayı biçimi: binlik NOKTA, ondalık VİRGÜL.

    Python'un `{:,.0f}` biçimi İngilizce ayraç üretiyor ("200,000") ve Türkçe
    bir cümlede bu, iki yüz bin ile iki yüzü karıştırılabilir hâle getiriyordu.
    """
    if deger is None:
        return "-"
    metin = f"{deger:,.{ondalik}f}"
    return metin.replace(",", "#").replace(".", ",").replace("#", ".")


def _mongo():
    # Paylaşılan havuz: her çağrıda yeni MongoClient kurmak, istek başına
    # bağlantı kurulumu + sunucu keşfi maliyeti demekti (bkz. mongo_baglanti).
    from chatbot.mongo_baglanti import veritabani
    return veritabani(MONGO_URI, DB_ADI, zaman_asimi_ms=5000)


def _sayi(ham: Any) -> Optional[float]:
    """'%3,99' / '11.401,85 TL' / 200000 -> float."""
    if ham is None:
        return None
    if isinstance(ham, (int, float)):
        return float(ham)
    metin = str(ham).replace("%", "").replace("TL", "").replace("₺", "").strip()
    metin = metin.replace(" ", "")
    if not metin or metin.lower() == "none":
        return None

    # 🛠️ BİNLİK NOKTASI ONDALIK SANILIYORDU.
    # Eski kural "virgül varsa Türkçe biçimdir" idi; virgülsüz "100.000 TL"
    # olduğu gibi float()'a gidiyor ve 100.0 çıkıyordu — yüz bin lira, yüz
    # liraya dönüşüyordu. Katılım hesabı köprüsünde tam olarak bu görüldü.
    if "," in metin:
        # Virgül ondalık ayraç; nokta varsa binlik ayraçtır.
        metin = metin.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", metin):
        # Yalnızca nokta var ve rakamları ÜÇERLİ gruplandırıyor -> binlik.
        # ("3.49" gibi gruplamayan hâller ondalık olarak bırakılır.)
        metin = metin.replace(".", "")

    try:
        return float(metin)
    except ValueError:
        return None


def _bankalari_dogrula(istenen: List[str], db) -> tuple:
    """İstenen banka kodlarını KENDİ verimizle doğrular.

    Döner: (kabul_edilen[{kod, ad, kampanya_sayisi}], reddedilen[], uyarilar[])
    """
    kabul, reddedilen, uyarilar = [], [], []
    gorulen = set()

    # Kampanya sayıları tek geçişte — kayıt başına banka kodu çözülüyor.
    sayimlar: dict = {}
    for d in db["islenmis_kampanyalar"].find({}, {"genel_bilgi.banka_id": 1,
                                                 "banka_kodu": 1, "banka_adi": 1,
                                                 "banka": 1}):
        kod = banka_kodu_coz(d)
        if kod:
            sayimlar[kod] = sayimlar.get(kod, 0) + 1

    for ham in istenen[:MAKS_BANKA]:
        kod = banka_kodu_normalize(ham)
        if not kod:
            reddedilen.append(str(ham))
            continue
        if kod in gorulen:
            continue
        gorulen.add(kod)
        adet = sayimlar.get(kod, 0)
        kabul.append({"kod": kod, "ad": BANKA_GORUNEN_ADLARI.get(kod, kod),
                      "kampanya_sayisi": adet})
        if adet == 0:
            uyarilar.append(
                f"{BANKA_GORUNEN_ADLARI.get(kod, kod)} tanınan bir banka ama "
                "kampanya verimizde hiç kaydı yok."
            )

    if len(istenen) > MAKS_BANKA:
        uyarilar.append(
            f"En fazla {MAKS_BANKA} banka kıyaslanabilir; ilk {MAKS_BANKA} tanesi alındı."
        )
    return kabul, reddedilen, uyarilar


def _urunu_dogrula(girdi: FinansmanUrunGirdisi, db) -> tuple:
    """Finansman ürününü kendi kayıtlarımızla karşılaştırır.

    Döner: (kayit | None, duzeltmeler[], uyarilar[])
    """
    duzeltmeler, uyarilar = [], []
    if not girdi or not girdi.banka:
        return None, duzeltmeler, ["Ürün bilgisi eksik geldi."]

    kod = _uzun_kod(girdi.banka)
    if not kod:
        return None, duzeltmeler, [f"'{girdi.banka}' tanınan bir banka değil."]

    # finansman_urun koleksiyonu KISA kodlar kullanıyor ("vakif", "kuveyt");
    # kampanya tarafı uzun kodlar ("vakif_katilim", "kuveytturk"). İkisini de dene.
    kod_adaylari = {kod, girdi.banka.strip().lower()}
    for kisa, uzun in (("vakif", "vakif_katilim"), ("ziraat", "ziraat_katilim"),
                       ("kuveyt", "kuveytturk")):
        if kod == uzun:
            kod_adaylari.add(kisa)

    sorgu: dict = {"banka": {"$in": list(kod_adaylari)}}
    if girdi.urun:
        sorgu["urun"] = girdi.urun
    if girdi.tutar:
        sorgu["finansman_tutari"] = {"$in": [girdi.tutar, str(int(girdi.tutar))]}
    if girdi.vade:
        sorgu["vade"] = {"$in": [girdi.vade, str(girdi.vade)]}

    kayit = db["finansman_urun"].find_one(sorgu)
    if not kayit:
        uyarilar.append(
            "Bu tutar/vade kombinasyonu finansman kayıtlarımızda bulunamadı; "
            "cevap yalnızca kampanya verisine dayanacak."
        )
        return None, duzeltmeler, uyarilar

    bizim_oran = _sayi(kayit.get("kar_orani"))
    if girdi.kar_orani is not None and bizim_oran is not None:
        if abs(float(girdi.kar_orani) - bizim_oran) > 0.01:
            duzeltmeler.append(
                f"Arayüzden gelen kâr oranı %{girdi.kar_orani} idi; kayıtlarımızda "
                f"%{bizim_oran}. Cevapta KAYITLI değer kullanıldı."
            )
            logger.warning(
                f"🔎 Analiz köprüsü — oran uyuşmazlığı: arayüz={girdi.kar_orani} "
                f"kayit={bizim_oran} banka={kod} urun={girdi.urun}"
            )
    return kayit, duzeltmeler, uyarilar


def _emsal_teklifler(kayit: dict, db, limit: int = 5) -> List[dict]:
    """Aynı ürün/tutar/vade için diğer bankaların kayıtlı teklifleri."""
    if not kayit:
        return []
    emsaller = list(db["finansman_urun"].find({
        "urun": kayit.get("urun"),
        "finansman_tutari": kayit.get("finansman_tutari"),
        "vade": kayit.get("vade"),
        "banka": {"$ne": kayit.get("banka")},
    }))
    temiz = []
    for e in emsaller:
        oran = _sayi(e.get("kar_orani"))
        if oran is None:
            continue
        temiz.append({"banka": banka_adi_getir(_uzun_kod(e.get("banka")), e.get("banka")),
                      "oran": oran, "taksit": e.get("aylik_taksit_tutari")})
    return sorted(temiz, key=lambda x: x["oran"])[:limit]


def _serbest_soruyu_temizle(ham: Optional[str]) -> tuple:
    """Kullanıcının yazdığı serbest soruyu güvenli hâle getirir."""
    if not ham:
        return "", []
    soru = " ".join(str(ham).split())[:MAKS_SERBEST_SORU]
    uyarilar = []
    if _SUPHELI_METIN.search(soru):
        uyarilar.append("Serbest metinde talimat benzeri ifade tespit edildi; "
                        "yalnızca soru olarak değerlendirildi.")
        logger.warning(f"🔒 Analiz köprüsü — şüpheli serbest metin: {soru[:120]!r}")
    return soru, uyarilar


@router.post("/api/analiz-koprusu")
async def analiz_koprusu(istek: AnalizIstegi):
    """Arayüz butonundan gelen yapılandırılmış isteği DOĞRULANMIŞ bir soruya çevirir.

    Cevabı bu uç ÜRETMEZ: dönen `prompt` normal `/api/chat` akışına gönderilir,
    böylece tablo, piyasa fotoğrafı ve öneriler sohbetin kendi doğrulanmış
    verisinden üretilir.
    """
    db = _mongo()
    EN = (istek.dil or "tr").lower().startswith("en")

    kabul, reddedilen, uyarilar = _bankalari_dogrula(istek.bankalar, db)
    duzeltmeler: List[str] = []

    serbest, s_uyari = _serbest_soruyu_temizle(istek.soru)
    uyarilar += s_uyari

    if reddedilen:
        uyarilar.append(
            ("Not recognised as banks in our data: " if EN else
             "Verimizde tanınmayan banka(lar): ") + ", ".join(reddedilen)
        )

    adlar = [b["ad"] for b in kabul]
    # ---------------------------------------------------------------- FİNANSMAN
    if istek.kaynak == "finansman" and istek.urun:
        kayit, d2, u2 = _urunu_dogrula(istek.urun, db)
        duzeltmeler += d2
        uyarilar += u2
        if kayit:
            banka_ad = banka_adi_getir(_uzun_kod(kayit.get("banka")), kayit.get("banka"))
            oran = _sayi(kayit.get("kar_orani"))
            tutar = _sayi(kayit.get("finansman_tutari"))
            vade = kayit.get("vade")
            urun_ad = {"ihtiyac": "ihtiyaç", "konut": "konut",
                       "tasit": "taşıt"}.get(kayit.get("urun"), kayit.get("urun"))
            emsal = _emsal_teklifler(kayit, db)

            if EN:
                prompt = (
                    f"Evaluate {banka_ad}'s {urun_ad} financing of "
                    f"{tutar:,.0f} TL over {vade} months at a {oran:.2f}% profit rate "
                    f"(monthly instalment {kayit.get('aylik_taksit_tutari')}) "
                    f"against the other participation banks."
                )
            else:
                prompt = (
                    f"{banka_ad}'ın {_tr_sayi(tutar)} TL tutarındaki {vade} ay vadeli "
                    f"{urun_ad} finansmanını (%{_tr_sayi(oran, 2)} kâr oranı, aylık "
                    f"{kayit.get('aylik_taksit_tutari')} taksit) diğer katılım "
                    f"bankalarının aynı koşuldaki teklifleriyle karşılaştırarak "
                    f"değerlendir."
                )
            if emsal:
                satir = "; ".join(
                    f"{e['banka']} %{_tr_sayi(e['oran'], 2) if not EN else e['oran']:.2f}"
                    if EN else f"{e['banka']} %{_tr_sayi(e['oran'], 2)}"
                    for e in emsal)
                prompt += (
                    f"\n\n(Doğrulanmış emsal teklifler — aynı tutar ve vade, "
                    f"finansman kayıtlarımızdan: {satir}.)"
                    if not EN else
                    f"\n\n(Verified peer offers — same amount and term, from our "
                    f"financing records: {satir}.)"
                )
            if serbest:
                prompt += (f"\n\nEk soru: {serbest}" if not EN
                           else f"\n\nAdditional question: {serbest}")
            return {
                "prompt": prompt,
                "gorunum": "analist",
                "dogrulama": {
                    "gecerli": True, "bankalar": kabul, "reddedilen": reddedilen,
                    "uyarilar": uyarilar, "duzeltmeler": duzeltmeler,
                    "emsal_sayisi": len(emsal),
                },
            }

    # ---------------------------------------------------------------- KATILIM HESAP
    if (istek.kaynak in ("katilim_hesap", "katilim_hesaplari", "katilim") or istek.katilim_hesap) and (istek.katilim_hesap or istek.urun):
        kh = istek.katilim_hesap or istek.urun
        banka_ham = getattr(kh, 'banka', '') or ''
        banka_kod = _uzun_kod(banka_ham) or banka_ham
        banka_ad = banka_adi_getir(banka_kod, banka_ham)
        tutar_val = getattr(kh, 'tutar', None) or 0
        vade_val = getattr(kh, 'vade', '') or ''
        net_oran_val = getattr(kh, 'net_oran', None) or getattr(kh, 'kar_orani', None) or 0
        net_kar_val = getattr(kh, 'net_kar', '') or ''

        if EN:
            prompt = (
                f"Evaluate {banka_ad}'s participation account offer of "
                f"{tutar_val:,.0f} TL with {vade_val} term at a net profit share rate of %{net_oran_val:.2f} "
                f"(estimated net yield {net_kar_val}) against other participation banks and sector averages."
            )
        else:
            prompt = (
                f"{banka_ad}'ın {_tr_sayi(tutar_val)} TL tutarındaki {vade_val} vadeli "
                f"katılım hesabı kâr payı getirisini (%{_tr_sayi(net_oran_val, 2)} net kâr oranı, "
                f"{net_kar_val} net getiri) diğer katılım bankalarıyla ve sektör ortalamasıyla karşılaştırarak analiz et."
            )

        if serbest:
            prompt += (f"\n\nEk soru: {serbest}" if not EN else f"\n\nAdditional question: {serbest}")

        return {
            "prompt": prompt,
            "gorunum": "analist",
            "dogrulama": {
                "gecerli": True,
                "bankalar": kabul if kabul else [{"kod": banka_kod, "ad": banka_ad}],
                "reddedilen": reddedilen,
                "uyarilar": uyarilar,
                "duzeltmeler": duzeltmeler,
            }
        }

    # ---------------------------------------------------------------- DASHBOARD
    if not kabul:
        return {
            "prompt": "",
            "gorunum": "analist",
            "dogrulama": {
                "gecerli": False, "bankalar": [], "reddedilen": reddedilen,
                "uyarilar": uyarilar or [
                    "Doğrulanabilen banka seçilmedi." if not EN
                    else "No verifiable bank was selected."],
                "duzeltmeler": duzeltmeler,
            },
        }

    if len(adlar) == 1:
        banka_metni = adlar[0]
    else:
        banka_metni = ", ".join(adlar[:-1]) + (" ve " if not EN else " and ") + adlar[-1]

    sozluk = _ANALIZ_METINLERI_EN if EN else _ANALIZ_METINLERI
    if istek.tur == "serbest" and serbest:
        prompt = (f"{banka_metni} için: {serbest}" if not EN
                  else f"Regarding {banka_metni}: {serbest}")
    else:
        kalip = sozluk.get(istek.tur) or sozluk["karsilastirma"]
        prompt = kalip.format(bankalar=banka_metni)
        if serbest:
            prompt += (f" Ayrıca: {serbest}" if not EN else f" Also: {serbest}")

    # 🎯 SEÇİM AÇIKÇA YAZILIYOR — kaç banka, hangileri.
    #
    # Kullanıcı dashboard'da 2, 3 ya da 4 banka işaretliyor ve analizin bu
    # seçimi kapsamasını bekliyor. Yalnızca banka adlarını cümle içinde
    # saymak yetmiyordu: model çoğu zaman en büyük bankaya odaklanıp
    # diğerlerini bir cümleyle geçiyordu. Seçimin BÜYÜKLÜĞÜNÜ ve her bankanın
    # tek tek ele alınması gerektiğini isteğin kendisine yazıyoruz — böylece
    # kural, prompt'un en görünür yerinde duruyor.
    if len(adlar) > 1:
        prompt += (
            # ⚠️ BU CÜMLE NİYET MOTORUNDAN GEÇİYOR — kelime seçimi davranışı
            # değiştirir. İlk sürümde "sonra HEPSİNİ yan yana koy" yazıyordu;
            # "hepsini" TUMU_ISTEGI kalıbına uyduğu için satır limiti "tümü"ne
            # çıkıyor ve 4 bankalık kıyas 192 SATIRLIK bir tabloya dönüşüyordu.
            # Aynı sebeple "tüm/bütün/hepsi" ve metrik adları (ödül, vade)
            # burada BİLİNÇLİ olarak kullanılmıyor; ne isteneceğini soru
            # belirlesin, yönerge değil.
            f" Seçili {len(adlar)} bankanın ({banka_metni}) HER BİRİNİ ayrı ayrı "
            f"ele al, hiçbirini atlama: kampanya sayısı ve pazar payı, "
            f"yoğunlaştığı kategoriler, güçlü ve zayıf yönleri. Ardından bu "
            f"bankaları yan yana koyarak sektördeki konumlarını yorumla."
            if not EN else
            f" Cover EACH of the {len(adlar)} selected banks ({banka_metni}) "
            f"separately, skipping none: campaign count and market share, category "
            f"focus, strengths and weaknesses. Then place these banks side by side "
            f"and interpret their position in the sector."
        )

    # 🧭 Rakam GÖMÜLMÜYOR — bilinçli. Kampanya sayısı, pay ve kategori dağılımı
    # sohbet hattında (grafigi_hazirla_mongo_dinamik) TÜM veri üzerinden zaten
    # hesaplanıyor. Buraya bir kez daha yazmak, iki kaynağın ayrışma riskini
    # doğurur — bu projede daha önce tam olarak böyle bir ayrışma yaşandı.
    logger.info(
        f"🔗 Analiz köprüsü: kaynak={istek.kaynak} tur={istek.tur} "
        f"banka={[b['kod'] for b in kabul]} reddedilen={reddedilen}"
    )
    return {
        "prompt": prompt,
        "gorunum": "analist",
        "dogrulama": {
            "gecerli": True, "bankalar": kabul, "reddedilen": reddedilen,
            "uyarilar": uyarilar, "duzeltmeler": duzeltmeler,
        },
    }
