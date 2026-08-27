import re
from dataclasses import dataclass

@dataclass
class AlanBulgusu:
    deger: str
    ham: str
    kural: str

GECERLI_TURLER = {
    "ihtiyac_finansmani",
    "konut_finansmani",
    "tasit_finansmani",
    "finansman_diger",
    "yeni_musteri",
    "mgm_kampanyasi",
    "yatirim_urunu",
    "alisveris_puani",
    "kart_kampanyasi",
    # 27.08.2026: Üye iş yeri indirim kampanyaları ("Arzum'da %15 İndirim",
    # "Etkinlik Biletlerinde 250 TL İndirim") katalogun en kalabalık
    # türlerinden biri (13 kayıt) ama karşılığı olan bir tür yoktu; hepsi
    # `kampanya_turu = None` olarak kalıyordu. `alisveris_puani`ye
    # yazılamazlar — indirim, puan değildir.
    "indirim_kampanyasi",
    # 27.08.2026: saf hediye/promosyon kampanyalari (4 kayit)
    "hediye_promosyon",
}

_R = re.IGNORECASE
_ERKEN_KARAKTER = 250

_KURALLAR: tuple[tuple[str, str, re.Pattern], ...] = (
    # --- FİNANSMAN KAMPANYALARI ---
    (
        "ihtiyac_finansmani",
        "hepsi",
        re.compile(r"ihtiya[çc]\s+(finansman|kart|kredi)", _R),
    ),
    (
        "konut_finansmani",
        "hepsi",
        re.compile(r"(konut|ev)\s+(finansman|kredi)|mortgage", _R),
    ),
    (
        "tasit_finansmani",
        "hepsi",
        re.compile(r"(ta[şs][ıi]t|ara[çc]|oto)\s+(finansman|kredi)", _R),
    ),
    (
        "finansman_diger",
        "hepsi",
        re.compile(
            r"\b(?!(?:ihtiya[çc]|konut|ev|ta[şs][ıi]t|ara[çc]|oto)\b)\w+\s+finansman\b|\bfinansman\b(?<!ihtiyaç finansman)(?<!konut finansman)",
            _R,
        ),
    ),
    # --- KAZANIM & BAĞLILIK KAMPANYALARI ---
    (
        "mgm_kampanyasi",
        "hepsi",
        re.compile(
            # ⚠️ Önceki sürüm "davet et"ten hemen ÖNCE "arkadaşını/yakınını"
            # görmeyi şart koşuyordu; Türkçe ekler ve araya giren kelimeler
            # yüzünden 6 MGM kampanyasının 3'ünü kaçırıyordu:
            #   "Yakınını Davet Et"            -> yak[ıi]n[ıi] + "nı" eki kaldı
            #   "Yakınlarını Kuveyt Türk'e Davet Et" -> araya 2 kelime girdi
            #   "Davet Et, Altın Kazan"        -> özne hiç yazılmamış
            # Artık ek serbest (\w*), araya en fazla 3 kelime girebiliyor ve
            # öznesiz "davet et" yalnızca ödül bağlamıyla birlikte sayılıyor.
            r"(?:arkada[şs]|yak[ıi]n|tan[ıi]d[ıi])\w*\s+(?:\S+\s+){0,3}?"
            r"(?:davet\s+et\w*|davet\s+edin|getir\w*)"
            r"|davet\s+et\w*[\s,.:!-]{0,6}(?:\S+\s+){0,3}?"
            r"(?:kazan\w*|hediye|ödül|odul|alt[ıi]n|bonus)"
            r"|davet\s+et(?:tiğin|tiğiniz)?\s+arkada[şs]"
            # ⚠️ Yalın "davet kod" ARAMAK YANLIŞ POZİTİF ÜRETİYOR: kampanya
            # şartlarında "Bu kampanya diğer davet kodlu kampanyalarla
            # birleştirilemez" diye bir DIŞLAMA cümlesi geçiyor ve harcama
            # kampanyası MGM sanılıyordu. Artık davet kodunun bir EYLEM ya da
            # kazanımla birlikte anılması gerekiyor ("Davet Kodunla Gel").
            r"|davet\s+kod\w*\s+(?:\S+\s+){0,2}?(?:gel\w*|gir\w*|kullan\w*|kazan\w*|ile)\b"
            r"|referans\s+(?:kod|link|bağlant)"
            r"|referans[ıi]n\w*\s+ile"
            r"|getir\s+kazan",
            _R,
        ),
    ),
    (
        "yeni_musteri",
        "baslik",
        re.compile(
            r"mü[şs]teri(si|miz)?\s+ol|yeni\s+.*mü[şs]teri"
            r"|ho[şs]\s*geldin|gelenlere|(türklü|finanslı|katılımlı)\s+ol",
            _R,
        ),
    ),
    # --- YATIRIM & TASARRUF ---
    ("yatirim_urunu", "baslik", re.compile(r"günlük\s+hesap", _R)),
    (
        "yatirim_urunu",
        "erken",
        re.compile(
            r"kat[ıi]l[ıi]?ma?\s+hesab|yat[ıi]r[ıi]m\s+hesab"
            r"|\bbes\b|emeklilik\s+plan|döviz|\bfx\b"
            r"|k[ıi]ymetli\s+maden|gümü[şs]|alt[ıi]n\s+hesab"
            r"|getiri\s+oran|payla[şs][ıi]m\s+oran|kur\s+f[ıi]rsat"
            r"|benzersiz\s+kur|dar\s+makas",
            _R,
        ),
    ),
    # --- HARCAMA & KART KAMPANYALARI ---
    # Not: Öncelik sıralaması düzeltildi; özel kart isimleri/kelimeleri önce kontrol ediliyor.
    (
        "kart_kampanyasi",
        "hepsi",
        re.compile(
            r"\b(?:biz\s+kart|sağlam\s+kart|happy\s+card|albaraka\s+world|vkard|berekett?card"
            r"|kredi\s+kart\w*|banka\s+kart\w*|debit\w*|troy|mastercard|visa"
            r"|qr\s+öde\w*|taksit\w*)\b",
            _R,
        ),
    ),
    (
        # ⚠️ Bu kural daha önce "alisveris_kampanyası" etiketini üretiyordu; o
        #    etiket bu dosyanın kendi GECERLI_TURLER kümesinde YOK. Kimse
        #    kümeyi dayatmadığı için geçersiz etiket sessizce Mongo'ya yazıldı
        #    (23 kayıt) ve arayüzde ham anahtar olarak göründü.
        "alisveris_puani",
        "erken",
        re.compile(
            r"parafpara|worldpuan|puan|\bmil\b|mil'e|\biade\b|bonus"
            r"|kazand[ıi]ran|(harcad[ıi]k[çc]a|yapt[ıi]k[çc]a)\s+kazan"
            # "1.000 TL harca 100 TL kazan" / "Tamamla Kazan" gibi emir kipli
            # kurgular yukarıdaki "harcadıkça kazan" kalıbına uymuyordu.
            r"|harca\w*\s+(?:\S+\s+){0,3}?kazan"
            r"|\btamamla\s+kazan\b"
            # "A101'de 100TL kazan", "Toplam 5.000 TL Harcamana ... kazan",
            # "İlk 250 TL Alışverişine Özel ... iade" gibi iyelik ekli
            # kurgular da kaçıyordu (5 kayıt `belirtilmemis` kalmıştı).
            r"|TL\s*kazan\w*"
            r"|harcaman\w*\s+(?:\S+\s+){0,3}?(?:kazan|iade|hediye)"
            r"|al[ıi][şs]veri[şs]in\w*\s+(?:\S+\s+){0,3}?(?:kazan|iade|hediye)",
            _R,
        ),
    ),
    (
        # EN SONDA: yalnızca yukarıdakilerin hiçbiri tutmadığında devreye
        # girer. Kart kampanyalarının (278 kayıt) sınıfını değiştirmemek için
        # bilerek `kart_kampanyasi`den SONRA duruyor — buradaki hedef, hiçbir
        # türe girmediği için `None` kalan üye iş yeri indirimleri.
        "indirim_kampanyasi",
        "erken",
        re.compile(
            r"\b(?:indirim\w*|iskonto\w*|indirimli)\b"
            r"|%\s*\d+(?:[.,]\d+)?\s*(?:'?ye\s+varan\s+)?indirim",
            _R,
        ),
    ),
    (
        # EN SON KURAL. Ölçüm: başlığında "hediye/promosyon/ödül" geçen 23
        # kampanyanın 19'u zaten daha özel bir türe (MGM, kart, yatırım…)
        # doğru şekilde giriyor. Bu kural en sonda durduğu için onlara
        # DOKUNMAZ; yalnızca hiçbir türe girmeyip `belirtilmemis` kalan
        # saf hediye/promosyon kampanyalarını yakalar
        # ("Fatura Talimatlarınıza Toplam 500 TL Hediye").
        "hediye_promosyon",
        "baslik",
        re.compile(
            r"\bhediye\w*|\bpromosyon\w*|\bödül\w*|\bodul\w*|\bücretsiz\b|\bbedava\b",
            _R,
        ),
    ),
)

_SORU_TURLERI = ("ihtiyac_finansmani", "konut_finansmani", "tasit_finansmani")

def urun_turu_sorusu(soru: str) -> str | None:
    for tur, _, desen in _KURALLAR:
        if tur in _SORU_TURLERI and desen.search(soru or ""):
            return tur
    return None

def kuralla_siniflandir(baslik: str, metin: str) -> AlanBulgusu | None:
    for tur, kapsam, desen in _KURALLAR:
        hedef = baslik or ""
        if kapsam == "erken":
            hedef = f"{baslik or ''} . {(metin or '')[:_ERKEN_KARAKTER]}"
        elif kapsam == "hepsi":
            hedef = f"{baslik or ''} . {metin or ''}"
        e = desen.search(hedef)
        if e:
            # GECERLI_TURLER bu dosyada tanımlıydı ama HİÇBİR YERDE
            # dayatılmıyordu; kural tablosundaki bir yazım kayması doğrudan
            # veritabanına sızabiliyordu. Artık kaymayı sessizce geçirmek
            # yerine burada yakalıyoruz.
            if tur not in GECERLI_TURLER:
                print(f"    ⚠️ Geçersiz kampanya türü etiketi atlandı: {tur!r} "
                      f"(GECERLI_TURLER içinde yok)")
                continue
            cevre = hedef[max(0, e.start() - 30): e.end() + 30].strip()
            return AlanBulgusu(tur, f"...{cevre}...", f"tur_kurali:{tur}")
    return None

def llm_ile_siniflandir(baslik: str, metin: str) -> AlanBulgusu | None:
    return None

def siniflandir(baslik: str, metin: str, llm_aktif: bool = True) -> AlanBulgusu | None:
    bulgu = kuralla_siniflandir(baslik, metin)
    if bulgu is None and llm_aktif:
        bulgu = llm_ile_siniflandir(baslik, metin)
    return bulgu