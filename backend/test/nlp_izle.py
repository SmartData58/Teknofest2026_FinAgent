# -*- coding: utf-8 -*-
"""nlp_izle.py — ADIM 3'ün (bilgi çıkarımı) aktivitesini izler ve denetler.

`pipeline.py` ADIM 3 yalnızca `is_extracted` olmayan kayıtları işler; katalog
bir kez işlendikten sonra adım "yeni kayıt yok" deyip çıkar ve NLP katmanının
GERÇEKTEN ne ürettiği bir daha görünmez. Bu araç o körlüğü kapatır:

  • gerçek `ham_kampanyalar` kayıtlarını alır,
  • `hibrit_cikar` + `semaya_donustur` zincirini AYNEN çalıştırır,
  • ama MongoDB'ye HİÇBİR ŞEY YAZMAZ (salt okunur denetim),
  • kural / LLM katkısını ALAN ALAN ayırır,
  • ürettiğini `islenmis_kampanyalar`'daki KAYITLI hâlle karşılaştırır.

Doluluk ölçüsü "dolu mu" değil "GERÇEKTEN bilgi taşıyor mu" diye sorar:
`sektor` alanı kayıtların hepsinde "Genel" — boş değil ama bilgi de değil.
Bu tür yedek değerler ayrı sayılır, yoksa %100 doluluk yanıltır.

KULLANIM
    python nlp_izle.py                 # 12 kayıt, karışık bankalar
    python nlp_izle.py --adet 30 --detay
    python nlp_izle.py --banka kuveytturk
    python nlp_izle.py --llm-kapali    # yalnızca kural katmanı (API çağrısı yok)
"""
import argparse
import os
import random
import sys
from collections import Counter, defaultdict

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(os.path.dirname(_BURASI))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

sys.stdout.reconfigure(encoding="utf-8")

# Argümanlar IMPORT'TAN ÖNCE okunuyor: hybrid.py `FINAGENT_LLM`i modül
# yüklenirken bir kez okuyup sabitliyor, sonradan set etmek etkisiz kalıyor.
_ap = argparse.ArgumentParser(description="NLP çıkarım katmanını izle ve denetle")
_ap.add_argument("--adet", type=int, default=12)
_ap.add_argument("--banka", default="", help="tek bankaya odaklan (banka kodu)")
_ap.add_argument("--detay", action="store_true", help="alan alan döküm yaz")
_ap.add_argument("--llm-kapali", action="store_true", help="LLM katmanını atla")
_ap.add_argument("--tohum", type=int, default=42)
args = _ap.parse_args()
if args.llm_kapali:
    os.environ["FINAGENT_LLM"] = "0"

from pymongo import MongoClient  # noqa: E402

from backend.nlp.extraction.extractor import semaya_donustur  # noqa: E402
from backend.nlp.extraction.hybrid import hibrit_cikar  # noqa: E402
from backend.nlp.extraction.rule_based import kurallarla_cikar  # noqa: E402

MONGO_URI = os.getenv(
    "MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin"
)
DB_ADI = os.getenv("CAMPAIGN_DB", "smartdata")

# (görünen ad, şema yolu, kategorik mi, yedek/bilgi taşımayan değerler)
IZLENEN_ALANLAR = [
    ("kampanya_turu", "genel_bilgi.kampanya_turu", True,
     {"belirtilmemis", "genel", "diger"}),
    ("hedef_kitle", "genel_bilgi.hedef_kitle", True, set()),
    ("sektor", "genel_bilgi.sektor", True, {"genel"}),
    ("bitis_tarihi", "genel_bilgi.bitis_tarihi", False, set()),
    ("kar_payi_orani", "finansman_detay.kar_payi_orani", False, set()),
    ("vade_ay", "finansman_detay.vade_ay", False, set()),
    ("finansman_tutari", "finansman_detay.finansman_tutari", False, set()),
    ("odul_tutari", "promosyon_detay.odul_tutari", False, set()),
]


def _ic_deger(doc, yol):
    d = doc
    for p in yol.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def _kisa(v, n=30):
    if v is None:
        return "—"
    s = ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
    return s if len(s) <= n else s[: n - 1] + "…"


def _yedek_mi(deger, yedekler):
    """Dolu ama bilgi taşımayan değer mi? ("Genel", "belirtilmemis" ...)"""
    if not yedekler:
        return False
    ham = deger[0] if isinstance(deger, list) and deger else deger
    return str(ham).strip().lower() in yedekler


def main():
    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[DB_ADI]
    sorgu = {}
    if args.banka:
        sorgu = {"$or": [{"banka": args.banka}, {"banka_kodu": args.banka}]}

    hepsi = list(db["ham_kampanyalar"].find(sorgu))
    if not hepsi:
        raise SystemExit("HATA: ham_kampanyalar boş (sorgu: %s)." % sorgu)

    random.seed(args.tohum)
    ornek = random.sample(hepsi, min(args.adet, len(hepsi)))

    print("=" * 78)
    print("NLP ÇIKARIM İZLEME — ham_kampanyalar: %d kayıt, %d tanesi denetleniyor"
          % (len(hepsi), len(ornek)))
    print("LLM katmanı: %s"
          % ("KAPALI (yalnızca kural)" if args.llm_kapali else "AÇIK"))
    print("=" * 78)

    kaynak = Counter()               # (alan, yontem) -> adet
    gercek_dolu = Counter()          # alan -> bilgi taşıyan kayıt sayısı
    yedek_dolu = Counter()           # alan -> yedek değerle dolu kayıt sayısı
    dagilim = defaultdict(Counter)   # kategorik alan -> değer dağılımı
    farklar = defaultdict(list)
    eslesen = 0
    bos_cikarim = []

    for i, doc in enumerate(ornek, 1):
        baslik = doc.get("baslik") or doc.get("kampanya_adi") or ""
        metin = doc.get("ham_metin") or doc.get("metin") or ""

        kural = kurallarla_cikar(baslik, metin) or {}
        tam = hibrit_cikar(baslik, metin) or {}

        llm_alanlari = [a for a, b in tam.items()
                        if getattr(b, "yontem", "regex") == "llm"]
        for alan, bulgu in tam.items():
            kaynak[(alan, getattr(bulgu, "yontem", "regex"))] += 1

        yeni = semaya_donustur(doc, tam)
        kayitli = db["islenmis_kampanyalar"].find_one({"_id": yeni.get("_id")})
        if kayitli:
            eslesen += 1
        if not tam:
            bos_cikarim.append(baslik[:60])

        print("\n%d/%d [%s] %s"
              % (i, len(ornek), (doc.get("banka") or "?").upper(), baslik[:56]))
        print("    kural: %d alan | LLM ekledi: %s" % (len(kural), llm_alanlari or "—"))

        for ad, yol, kategorik, yedekler in IZLENEN_ALANLAR:
            y = _ic_deger(yeni, yol)
            k = _ic_deger(kayitli, yol) if kayitli else None
            if y not in (None, "", [], "-"):
                if _yedek_mi(y, yedekler):
                    yedek_dolu[ad] += 1
                else:
                    gercek_dolu[ad] += 1
            if kategorik:
                for v in (y if isinstance(y, list) else [y]):
                    dagilim[ad][str(v)] += 1
            if kayitli and y != k:
                farklar[ad].append((baslik[:38], k, y))
            if args.detay:
                isaret = " " if (not kayitli or y == k) else "≠"
                print("      %s %-17s yeni=%-32s kayıtlı=%s"
                      % (isaret, ad, _kisa(y, 32), _kisa(k)))

    n = len(ornek)
    print("\n" + "=" * 78)
    print("ALAN DOLULUĞU  (bilgi taşıyan / yedek değer)")
    print("=" * 78)
    for ad, _, _, _ in IZLENEN_ALANLAR:
        g, ye = gercek_dolu[ad], yedek_dolu[ad]
        oran = 100.0 * g / n
        print("  %-17s %3d/%-3d %4.0f%% %-20s%s"
              % (ad, g, n, oran, "#" * int(oran / 5),
                 ("   (+%d yedek değer)" % ye) if ye else ""))

    print("\n" + "=" * 78)
    print("KATEGORİK ALAN DAĞILIMI")
    print("=" * 78)
    for ad in dagilim:
        oge = ", ".join("%s=%d" % (v, c) for v, c in dagilim[ad].most_common(6))
        print("  %-17s %s" % (ad, oge))
        if len(dagilim[ad]) == 1:
            print("      ^ UYARI: tek değer — bu alan hiç ayrıştırmıyor.")

    print("\n" + "=" * 78)
    print("ALAN KAYNAĞI (kural mı, LLM mi?)")
    print("=" * 78)
    for a in sorted({x for x, _ in kaynak}):
        r, l = kaynak[(a, "regex")], kaynak[(a, "llm")]
        print("  %-22s kural=%3d  LLM=%3d" % (a, r, l))
    toplam_llm = sum(v for (a, y), v in kaynak.items() if y == "llm")
    print("\n  LLM toplam katkı: %d alan" % toplam_llm)
    if toplam_llm == 0 and not args.llm_kapali:
        print("  UYARI: LLM hiç katkı yapmadı — servis erişilebilir mi?")

    if bos_cikarim:
        print("\nUYARI: hiç alan çıkarılamayan %d kayıt:" % len(bos_cikarim))
        for b in bos_cikarim[:8]:
            print("     - %s" % b)

    print("\n" + "=" * 78)
    print("KAYITLI VERİYLE KARŞILAŞTIRMA  (%d/%d kayıt islenmis_kampanyalar'da bulundu)"
          % (eslesen, n))
    print("=" * 78)
    if not eslesen:
        print("  UYARI: hiçbir kayıt eşleşmedi — _id şeması değişmiş olabilir,")
        print("         karşılaştırma yapılamadı.")
    elif not farklar:
        print("  Fark yok — depodaki veri mevcut kurallarla aynı.")
    else:
        for ad, liste in sorted(farklar.items(), key=lambda x: -len(x[1])):
            print("\n  %s  (%d/%d kayıtta farklı)" % (ad, len(liste), eslesen))
            for baslik, k, y in liste[:4]:
                print("     %-40s kayıtlı=%-24s → yeni=%s"
                      % (baslik, _kisa(k, 22), _kisa(y, 22)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
