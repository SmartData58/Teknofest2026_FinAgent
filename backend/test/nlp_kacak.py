# -*- coding: utf-8 -*-
"""nlp_kacak.py — ÇIKARILMASI GEREKİRKEN ÇIKARILMAYAN alanları bulur.

`nlp_denetle.py` çıkarılanın DOĞRU olup olmadığına bakar (precision).
Bu araç ters soruyu sorar: metinde apaçık duran bir bilgi alana YAZILMAMIŞ mı
(recall)? İkisi ayrı hata sınıfı ve ikincisi çok daha sinsi — hiçbir kusur
üretmediği için denetimden temiz geçer, yalnızca tablo boş görünür.

Somut örnek: `kar_payi_orani` 391 kaydın yalnızca 8'inde doluydu ve denetim
"kusur yok" diyordu. Oysa kural sırası yüzünden gerçekçi ifadelerin yarısı
kaçıyordu ("Harcamalarınızı %2,99 kâr payı oranıyla…" nakit iade sayılıyordu).

Yöntem: her alan için metinde GÜÇLÜ bir gösterge aranır. Gösterge varsa ve alan
boşsa kayıt "kaçak" olarak raporlanır; ayrıca göstergenin yakaladığı sayı ile
alandaki değer karşılaştırılır (uyuşmuyorsa "sapma" olarak işaretlenir).

SALT OKUNUR — hiçbir şey yazmaz.

KULLANIM
    python nlp_kacak.py
    python nlp_kacak.py --alan kar_payi_orani --ornek 12
"""
import argparse
import os
import re
import sys
from collections import Counter

from pymongo import MongoClient

sys.stdout.reconfigure(encoding="utf-8")

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise SystemExit("HATA: MONGO_URI yok — bu betiği backend konteynerinde çalıştır.")
DB_ADI = os.getenv("MONGO_DB_NAME") or os.getenv("CAMPAIGN_DB") or "smartdata"

_S = re.IGNORECASE

# (alan adı, şema yolu, gösterge deseni, yakalanan grubun sayıya çevrilmesi)
# Gösterge desenleri BİLEREK dar: amaç "olabilir"i değil, "kesin var"ı bulmak.
GOSTERGELER = [
    ("kar_payi_orani", "finansman_detay.kar_payi_orani",
     re.compile(r"%\s*(\d{1,2}(?:[.,]\d+)?)\s*(?:'?\w+)?\s*"
                r"(?:k[âa]r\s*pay|k[âa]r\s*oran)"
                r"|(?:k[âa]r\s*pay\w*|k[âa]r\s*oran\w*)[^%.]{0,40}%\s*(\d{1,2}(?:[.,]\d+)?)", _S)),
    ("vade_ay", "finansman_detay.vade_ay",
     re.compile(r"(\d{1,3})\s*(?:ay|aya)\s*(?:varan|kadar)?\s*vade"
                r"|vade\w*\s*(\d{1,3})\s*ay", _S)),
    ("taksit", "finansman_detay.taksit",
     re.compile(r"(\d{1,3})\s*(?:ay|aya)?\s*(?:varan|kadar)?\s*taksit", _S)),
    # ⚠️ "kredi" tek başına gösterge OLAMAZ: kampanya metinlerinin neredeyse
    # tamamında "kredi kartı" geçiyor ve bu, harcama eşiklerini finansman
    # tutarı sanmaya yol açıyordu (9 sahte "kaçak"). Kart bağlamı dışlanıyor;
    # ayrıca tutarın "kadar/varan" gibi bir tavan ifadesiyle ya da doğrudan
    # finansman kelimesiyle anılması aranıyor.
    ("finansman_tutari", "finansman_detay.finansman_tutari",
     re.compile(r"([\d.]{3,12}|\d{1,4}\s*(?:bin|milyon))\s*TL[^.]{0,25}"
                r"(?:'?ye\s+(?:kadar|varan)\s+)?"
                r"(?:finansman|kredi(?!\s*kart))"
                r"|(?:finansman|kredi(?!\s*kart))[^.]{0,25}?"
                r"([\d.]{3,12}|\d{1,4}\s*(?:bin|milyon))\s*TL", _S)),
    # ⚠️ Kampanya metinleri hem BİRİM BAŞINA hem TOPLAM ödülü yazıyor
    # ("her harcamaya 50 TL, toplamda 200 TL Worldpuan"). Çıkarıcı bilerek
    # TOPLAMI alıyor; gösterge ilk eşleşmeyi alırsa doğru çıkarımı "sapma"
    # diye raporlar. Bu yüzden önce "toplam" kalıbı aranıyor (bkz. _oncelikli).
    # "toplam X TL" tek başına ödül göstergesi DEĞİL: metinlerde harcama
    # eşiği olarak da geçiyor ("sepet toplamı 2.000 TL ve üzeri", "toplamda
    # 150.000 TL ve üzeri hak ediş"). Bu yüzden toplam kalıbının ardından
    # eşik ifadesi gelmemesi ve bir ödül kelimesiyle anılması aranıyor.
    ("odul_tutari", "promosyon_detay.odul_tutari",
     re.compile(r"toplam(?:da|[ıi])?\s*([\d.]{2,12})\s*TL"
                r"(?!\s*(?:ve\s+üzeri|ve\s+\d|arası|üzeri))"
                r"[^.]{0,40}?(?:hediye|ödül|iade|indirim|parafpara|worldpuan|chippara)"
                # "2.000 TL üzeri alışverişlerde %15 indirim" bir EŞİKtir;
                # ardından eşik ifadesi gelen tutar ödül sayılmamalı.
                r"|([\d.]{2,12})\s*TL(?!\s*(?:ve\s+)?(?:üzeri|üstü|arası|altı))"
                r"[^.]{0,30}"
                r"(?:hediye|ödül|iade|indirim|parafpara|worldpuan|chippara)", _S)),
    ("nakit_iade_yuzde", "promosyon_detay.nakit_iade_yuzde",
     re.compile(r"%\s*(\d{1,2}(?:[.,]\d+)?)[^%.]{0,30}"
                r"(?:nakit\s*iade|cashback)"
                r"|(?:nakit\s*iade|cashback)[^%.]{0,30}%\s*(\d{1,2}(?:[.,]\d+)?)", _S)),
    ("bitis_tarihi", "genel_bilgi.bitis_tarihi",
     re.compile(r"\d{1,2}[./]\d{1,2}[./]\d{4}"
                r"|\d{1,2}\s+(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|"
                r"ağustos|eylül|ekim|kasım|aralık)\s+\d{4}", _S)),
]


def _ic(doc, yol):
    d = doc
    for p in yol.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def _sayi(ham):
    """'2,99' / '100.000' / '250 bin' -> float"""
    if not ham:
        return None
    s = str(ham).strip().lower()
    carpan = 1
    if "milyon" in s:
        carpan, s = 1_000_000, s.replace("milyon", "")
    elif "bin" in s:
        carpan, s = 1_000, s.replace("bin", "")
    s = s.strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s) * carpan
    except ValueError:
        return None


def _ilk_grup(m):
    for g in m.groups():
        if g:
            return g
    return m.group(0)


def main():
    ap = argparse.ArgumentParser(description="Kaçırılan çıkarımları bul")
    ap.add_argument("--alan", default="", help="tek alana odaklan")
    ap.add_argument("--ornek", type=int, default=6, help="alan başına gösterilecek örnek")
    ap.add_argument("--koleksiyon", default="islenmis_kampanyalar")
    ap.add_argument("--ham", action="store_true",
                    help="islenmis_kampanyalar yerine ham_kampanyalar'dan CANLI "
                         "çıkarım yaparak ölç (boru hattı sürerken kullanışlı; "
                         "hiçbir şey YAZMAZ)")
    ap.add_argument("--llm-kapali", action="store_true",
                    help="--ham ile: yalnızca kural katmanı (API çağrısı yok)")
    args = ap.parse_args()

    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[DB_ADI]

    if args.ham:
        # Boru hattı ADIM 3'ü henüz koşmamış olabilir; kuralları ham metne
        # doğrudan uygulayıp şema belgesini bellekte üretiyoruz. Mongo'ya
        # yazılmadığı için sürmekte olan boru hattını etkilemez.
        if args.llm_kapali:
            os.environ["FINAGENT_LLM"] = "0"
        from backend.nlp.extraction.extractor import semaya_donustur
        from backend.nlp.extraction.hybrid import hibrit_cikar

        hamlar = list(db["ham_kampanyalar"].find())
        if not hamlar:
            raise SystemExit("HATA: ham_kampanyalar boş.")
        kayitlar = []
        for h in hamlar:
            bulgular = hibrit_cikar(h.get("baslik", ""), h.get("ham_metin", "")) or {}
            kayitlar.append(semaya_donustur(h, bulgular))
    else:
        kayitlar = list(db[args.koleksiyon].find())
        if not kayitlar:
            raise SystemExit(f"HATA: {args.koleksiyon} boş.")

    print("=" * 82)
    print("KAÇAK ÇIKARIM DENETİMİ — %d kayıt" % len(kayitlar))
    print("Soru: metinde bilgi VAR mı ama alan BOŞ mu?")
    print("=" * 82)

    ozet = []
    for ad, yol, desen in GOSTERGELER:
        if args.alan and args.alan != ad:
            continue

        kacaklar, sapmalar, dolu, gosterge_var = [], [], 0, 0
        for d in kayitlar:
            g = d.get("genel_bilgi") or {}
            metin = (g.get("kampanya_adi") or "") + " " + (g.get("metin") or "")
            deger = _ic(d, yol)
            if deger not in (None, "", []):
                dolu += 1
            # Desende birden çok alternatif varsa ilk eşleşme her zaman en
            # doğru olan değildir; öncelikli alternatif (ör. "toplamda X TL")
            # metnin ilerisinde olabilir. Tüm eşleşmeler taranıp, ilk grubu
            # dolu olan (öncelikli alternatif) varsa o tercih ediliyor.
            eslesmeler = list(desen.finditer(metin))
            if not eslesmeler:
                continue
            # bitis_tarihi deseninde yakalama grubu yok; groups() ile güvenli.
            m = next((e for e in eslesmeler if e.groups() and e.group(1)),
                     eslesmeler[0])
            gosterge_var += 1
            kanit = re.sub(r"\s+", " ", metin[max(0, m.start() - 40): m.end() + 40]).strip()
            if deger in (None, "", []):
                kacaklar.append((g.get("banka_id"), (g.get("kampanya_adi") or "")[:42], kanit))
            elif ad != "bitis_tarihi":
                beklenen = _sayi(_ilk_grup(m))
                if beklenen is not None and abs(float(deger) - beklenen) > 0.01:
                    sapmalar.append((g.get("banka_id"), (g.get("kampanya_adi") or "")[:42],
                                     deger, beklenen, kanit))

        ozet.append((ad, dolu, gosterge_var, len(kacaklar), len(sapmalar)))

        print("\n" + "-" * 82)
        print("%s | dolu: %d/%d | metinde gösterge: %d | KAÇAK: %d | sapma: %d"
              % (ad, dolu, len(kayitlar), gosterge_var, len(kacaklar), len(sapmalar)))
        print("-" * 82)
        for banka, adi, kanit in kacaklar[: args.ornek]:
            print("  ✗ [%s] %s" % (banka, adi))
            print("      metin: …%s…" % kanit[:120])
        if len(kacaklar) > args.ornek:
            print("  … (+%d kaçak daha)" % (len(kacaklar) - args.ornek))
        for banka, adi, v, bek, kanit in sapmalar[: args.ornek]:
            print("  ≠ [%s] %s | alan=%s metin=%s" % (banka, adi, v, bek))
            print("      metin: …%s…" % kanit[:120])
        if len(sapmalar) > args.ornek:
            print("  … (+%d sapma daha)" % (len(sapmalar) - args.ornek))

    print("\n" + "=" * 82)
    print("ÖZET")
    print("=" * 82)
    print("  %-20s %8s %10s %8s %8s" % ("alan", "dolu", "gösterge", "kaçak", "sapma"))
    for ad, dolu, gv, k, s in ozet:
        oran = ("%.0f%%" % (100.0 * (gv - k) / gv)) if gv else "—"
        print("  %-20s %8d %10d %8d %8s   yakalama: %s"
              % (ad, dolu, gv, k, s, oran))
    return 0


if __name__ == "__main__":
    sys.exit(main())
