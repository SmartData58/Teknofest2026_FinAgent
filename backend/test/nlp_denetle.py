# -*- coding: utf-8 -*-
"""nlp_denetle.py — islenmis_kampanyalar'daki HER kaydı tek tek denetler.

`nlp_izle.py` çıkarımın CANLI davranışını izler (kural mı LLM mi, ne buldu).
Bu araç ise SONUCU denetler: depodaki her kaydın her alanı, kaydın kendi ham
metniyle karşılaştırılır.

En güçlü kontrol KANIT TESTİ'dir: çıkarılan bir sayı, kaynak metinde
gerçekten geçiyor mu? Geçmiyorsa değer ya uydurulmuş ya da yanlış birimden
türetilmiştir. Türkçe sayı yazımı çok biçimli olduğu için (1.250 / 1250 /
1,250 / "1.250 TL" / "40 bin") tüm makul varyantlar üretilip aranır.

Diğer kontroller:
  • aralık   — kâr payı 0-50, vade 1-600, taksit 1-120, tutarlar 1-100M
  • tarih    — bitiş >= başlangıç, süre_gün tutarlı, yıl 2015-2035
  • tutarlılık — başlıktaki konu ile kampanya_turu / sektor çelişiyor mu
  • boşluk   — zorunlu sayılan alanlar boş mu

Çıktı: her kusurlu kayıt için kayıt kimliği, alan, değer ve gerekçe.
SALT OKUNUR — hiçbir şey yazmaz.

KULLANIM
    python nlp_denetle.py                 # tüm kayıtlar, özet + kusur listesi
    python nlp_denetle.py --hepsi         # temiz kayıtları da tek tek yaz
    python nlp_denetle.py --alan kar_payi_orani
    python nlp_denetle.py --json /tmp/kusurlar.json
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

from pymongo import MongoClient

sys.stdout.reconfigure(encoding="utf-8")

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise SystemExit("HATA: MONGO_URI yok — bu betiği backend konteynerinde çalıştır.")
DB_ADI = os.getenv("MONGO_DB_NAME") or os.getenv("CAMPAIGN_DB") or "smartdata"

# ---------------------------------------------------------------- ARALIKLAR
# Üst sınırlar "teorik olarak mümkün" değil, "bu veri kümesinde makul" ölçüsü.
ARALIKLAR = {
    "finansman_detay.kar_payi_orani":    (0.0, 50.0),
    "finansman_detay.vade_ay":           (1, 600),
    "finansman_detay.taksit":            (1, 120),
    "finansman_detay.finansman_tutari":  (1000.0, 100_000_000.0),
    "promosyon_detay.odul_tutari":       (1.0, 10_000_000.0),
    "promosyon_detay.nakit_iade_yuzde":  (0.1, 100.0),
    "promosyon_detay.puan_kazanc":       (1.0, 10_000_000.0),
    "genel_bilgi.sure_gun":              (1, 3650),
}

# Kanıt testi uygulanacak alanlar (metinde geçmesi BEKLENEN sayılar).
KANIT_ALANLARI = [
    "finansman_detay.kar_payi_orani",
    "finansman_detay.vade_ay",
    "finansman_detay.taksit",
    "finansman_detay.finansman_tutari",
    "promosyon_detay.odul_tutari",
    "promosyon_detay.nakit_iade_yuzde",
    "promosyon_detay.puan_kazanc",
]

# Başlıkta şu geçiyorsa kampanya_turu şu OLMAMALI / OLMALI.
TUR_IPUCLARI = [
    (re.compile(r"\bkonut\b|\bev\s+sahib|mortgage|gayrimenkul", re.I), "konut_finansmani"),
    # NOT: burada \t yazmak TAB demektir; "taşıt" için \b gerekiyor.
    (re.compile(r"\bta[şs][ıi]t\b|\botomobil\b|\bara[çc]\s+finansman", re.I), "tasit_finansmani"),
    (re.compile(r"arkada[şs][ıi]n[ıi]\s+davet|\bmgm\b|\bdavet\s+et", re.I), "mgm_kampanyasi"),
]

# ⚠️ Bu ipuçları YALNIZCA başlık TEK BİR sektöre işaret ettiğinde uygulanır.
# Bir başlık iki sektöre birden değebiliyor: "A101 Ekstra'da tüm cep
# telefonlarına 3 Taksit" hem market zincirini hem ürün kategorisini içerir.
# Böyle bir başlıkta tek bir "doğru" sektör dayatmak denetçiyi yanıltıcı yapar
# (çıkarım Teknoloji diyordu ve HAKLIYDI; denetçi Market bekleyip kusur
# sayıyordu). Çok eşleşmeli başlıklarda kontrol atlanıyor.
SEKTOR_IPUCLARI = [
    (re.compile(r"akaryak[ıi]t|benzin|motorin|petrol\s+ofisi|\bopet\b|\bshell\b", re.I),
     "Akaryakıt ve Otomotiv"),
    # "yapı market" bir nalburdur; sektör kuralı onu bilerek Mobilya ve Ev'e
    # koyuyor. Gösterge de aynı ayrımı yapmazsa doğru çıkarımı kusur sayar.
    (re.compile(r"(?<!yapı )(?<!yapi )\bmarket\w*"
                r"|\bg[ıi]da\w*|migros|carrefour|\ba101\b|\bbim\b", re.I),
     "Market ve Gıda"),
    (re.compile(r"u[çc]ak\s+bilet\w*|\botel\w*|tatil\w*|seyahat\w*|turizm\w*", re.I),
     "Seyahat ve Turizm"),
    (re.compile(r"k[ıi]rtasiye\w*|\bokul\w*|e[ğg]itim\w*|üniversite\w*", re.I),
     "Eğitim ve Kırtasiye"),
    (re.compile(r"cep\s+telefon\w*|\bnotebook\b|bilgisayar\w*|elektronik\w*", re.I),
     "Teknoloji ve Elektronik"),
    (re.compile(r"eczane\w*|hastane\w*|sa[ğg]l[ıi]k\s+harcama\w*", re.I),
     "Sağlık"),
    (re.compile(r"restoran\w*|\bkahve\w*", re.I),
     "Restoran ve Yeme-İçme"),
    (re.compile(r"mobilya\w*|do[ğg]ta[şs]|istikbal|bellona|enza\s+home|yata[şs]", re.I),
     "Mobilya ve Ev"),
]


def _ic(doc, yol):
    d = doc
    for p in yol.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def _sayi_varyantlari(sayi):
    """Bir sayının Türkçe metinde geçebileceği tüm makul yazımları üretir."""
    v = set()
    tam = float(sayi)
    kesirsiz = int(round(tam))

    # 2.99 -> "2,99", "2.99", "299"(nadiren bitişik)
    if abs(tam - kesirsiz) > 1e-9:
        s = ("%g" % tam)
        v.add(s)
        v.add(s.replace(".", ","))
        # ⚠️ Sondaki sıfırlı yazım: metinde "%4,20" geçen bir oran alana 4.2
        # olarak yazılıyor; "4,2" araması ise sonraki "0" yüzünden negatif
        # ileri-bakışa takılıp EŞLEŞMİYORDU. Doğru çıkarım kanıtsız sanılıyordu.
        for basamak in (2, 3):
            t = ("%%.%df" % basamak) % tam
            v.add(t)
            v.add(t.replace(".", ","))
    else:
        v.add(str(kesirsiz))
        # binlik ayraçlı: 1250 -> "1.250", "1 250"
        b = "{:,}".format(kesirsiz)
        v.add(b.replace(",", "."))
        v.add(b.replace(",", " "))
        v.add(b.replace(",", ""))
        # "40 bin" / "1,5 milyon" gibi kısaltmalar
        if kesirsiz >= 1000 and kesirsiz % 1000 == 0:
            v.add("%d bin" % (kesirsiz // 1000))
            v.add("%dbin" % (kesirsiz // 1000))
        if kesirsiz >= 1_000_000 and kesirsiz % 1_000_000 == 0:
            v.add("%d milyon" % (kesirsiz // 1_000_000))
        # ondalıklı yazım: 300 -> "300,00"
        v.add("%d,00" % kesirsiz)
        v.add("%d.00" % kesirsiz)
    return {x for x in v if x}


def _metinde_var_mi(sayi, metin):
    if sayi is None or not metin:
        return True          # denetlenemiyor -> kusur sayma
    duz = re.sub(r"\s+", " ", metin)
    for varyant in _sayi_varyantlari(sayi):
        # Sayının içine gömülü eşleşmeyi engelle: "25" -> "1250" içinde sayılmasın.
        # IGNORECASE şart: metinde "250 Bin TL" büyük harfle geçiyor.
        if re.search(r"(?<![\d.,])" + re.escape(varyant) + r"(?![\d.,]*\d)",
                     duz, re.IGNORECASE):
            return True
    return False


def _tarih(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        for f in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(v[:len(f) + 2].strip(), f)
            except ValueError:
                continue
    return None


def kaydi_denetle(d):
    """Tek kaydı denetler; kusur listesi döner: [(alan, deger, gerekce), ...]"""
    kusurlar = []
    g = d.get("genel_bilgi") or {}
    metin = (g.get("metin") or "") + " " + (g.get("kampanya_adi") or "")

    # 1) ARALIK
    for yol, (alt, ust) in ARALIKLAR.items():
        v = _ic(d, yol)
        if v is None:
            continue
        try:
            sayi = float(v)
        except (TypeError, ValueError):
            kusurlar.append((yol, v, "sayıya çevrilemiyor"))
            continue
        if not (alt <= sayi <= ust):
            kusurlar.append((yol, v, f"aralık dışı (beklenen {alt}–{ust})"))

    # 2) KANIT — sayı kaynak metinde geçiyor mu?
    for yol in KANIT_ALANLARI:
        v = _ic(d, yol)
        if v is None:
            continue
        try:
            sayi = float(v)
        except (TypeError, ValueError):
            continue
        if not _metinde_var_mi(sayi, metin):
            kusurlar.append((yol, v, "kaynak metinde geçmiyor (kanıtsız)"))

    # 3) TARİH
    bas, bit = _tarih(g.get("baslangic_tarihi")), _tarih(g.get("bitis_tarihi"))
    if bas and bit and bit < bas:
        kusurlar.append(("genel_bilgi.bitis_tarihi", str(bit)[:10],
                         f"başlangıçtan önce ({str(bas)[:10]})"))
    for ad, t in (("baslangic_tarihi", bas), ("bitis_tarihi", bit)):
        if t and not (2015 <= t.year <= 2035):
            kusurlar.append((f"genel_bilgi.{ad}", str(t)[:10], "yıl makul aralıkta değil"))
    sg = g.get("sure_gun")
    if bas and bit and sg is not None:
        gercek = (bit - bas).days
        if abs(gercek - int(sg)) > 1:
            kusurlar.append(("genel_bilgi.sure_gun", sg,
                             f"tarihlerle tutarsız (hesaplanan {gercek})"))

    # 4) TUTARLILIK — başlık ipucu ile etiket çelişiyor mu?
    baslik = g.get("kampanya_adi") or ""
    tur = g.get("kampanya_turu")
    # Sektörde olduğu gibi: başlık birden çok türe değiyorsa ("Konut ve Taşıt
    # Finansmanı Kampanyası") tek doğru yoktur, kontrol atlanır.
    tur_vuran = [bek for desen, bek in TUR_IPUCLARI if desen.search(baslik)]
    if len(tur_vuran) == 1 and tur != tur_vuran[0]:
        kusurlar.append(("genel_bilgi.kampanya_turu", tur,
                         f"başlık '{tur_vuran[0]}' ima ediyor"))
    sektor = g.get("sektor")
    ipucu_vuran = [bek for desen, bek in SEKTOR_IPUCLARI if desen.search(baslik)]
    # Yalnızca TEK sektöre işaret eden başlıklarda karar dayatılabilir.
    if len(ipucu_vuran) == 1 and sektor != ipucu_vuran[0]:
        kusurlar.append(("genel_bilgi.sektor", sektor,
                         f"başlık '{ipucu_vuran[0]}' ima ediyor"))

    # 5) BOŞLUK
    # `belirtilmemis` bilinçli bir "belirlenemedi" etiketi; null'dan iyidir
    # ama yine de bir çıkarım boşluğudur, o yüzden ayrı gerekçeyle sayılır.
    if not tur:
        kusurlar.append(("genel_bilgi.kampanya_turu", None, "boş"))
    elif tur == "belirtilmemis":
        kusurlar.append(("genel_bilgi.kampanya_turu", tur, "tür belirlenemedi"))
    if not g.get("hedef_kitle"):
        kusurlar.append(("genel_bilgi.hedef_kitle", None, "boş"))

    return kusurlar


def main():
    ap = argparse.ArgumentParser(description="Her kampanya kaydını tek tek denetle")
    ap.add_argument("--hepsi", action="store_true", help="temiz kayıtları da yaz")
    ap.add_argument("--alan", default="", help="yalnızca bu alanı içeren kusurlar")
    ap.add_argument("--json", default="", help="kusurları JSON dosyasına yaz")
    ap.add_argument("--koleksiyon", default="islenmis_kampanyalar",
                    help="denetlenecek koleksiyon (yedek karşılaştırması için)")
    ap.add_argument("--dokum", action="store_true",
                    help="her kayıt için tek satırlık çıkarım dökümü yaz")
    ap.add_argument("--banka", default="", help="dökümü tek bankaya daralt")
    args = ap.parse_args()

    c = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[DB_ADI][args.koleksiyon]
    kayitlar = list(c.find())

    kusurlu = []
    sayac = Counter()
    banka_sayac = defaultdict(Counter)

    # --- DÖKÜM: her kaydın çıkarımını tek satırda göster ------------------
    # Kusur listesi neyin YANLIŞ olduğunu söyler; bu döküm neyin ÇIKARILDIĞINI
    # gösterir, yani sessiz boşlukları (hiçbir kural tetiklenmemiş kayıtlar)
    # gözle taramayı mümkün kılar.
    if args.dokum:
        secili = [d for d in kayitlar
                  if not args.banka
                  or (d.get("genel_bilgi") or {}).get("banka_id") == args.banka]
        secili.sort(key=lambda d: ((d.get("genel_bilgi") or {}).get("banka_id") or "",
                                   (d.get("genel_bilgi") or {}).get("kampanya_adi") or ""))
        print("%-4s %-14s %-46s %-19s %-24s %s"
              % ("#", "banka", "kampanya", "tür", "sektör", "sayısal alanlar"))
        print("-" * 150)
        for i, d in enumerate(secili, 1):
            g = d.get("genel_bilgi") or {}
            f = d.get("finansman_detay") or {}
            p = d.get("promosyon_detay") or {}
            parcalar = []
            for etiket, v in (("oran", f.get("kar_payi_orani")),
                              ("vade", f.get("vade_ay")),
                              ("taksit", f.get("taksit")),
                              ("tutar", f.get("finansman_tutari")),
                              ("ödül", p.get("odul_tutari")),
                              ("iade%", p.get("nakit_iade_yuzde")),
                              ("puan", p.get("puan_kazanc"))):
                if v is not None:
                    parcalar.append("%s=%g" % (etiket, float(v)))
            hk = g.get("hedef_kitle") or []
            kusur_sayisi = len(kaydi_denetle(d))
            print("%-4d %-14s %-46s %-19s %-24s %-42s %s"
                  % (i, (g.get("banka_id") or "?"),
                     (g.get("kampanya_adi") or "(başlıksız)")[:46],
                     str(g.get("kampanya_turu"))[:19],
                     str(g.get("sektor"))[:24],
                     " ".join(parcalar)[:42] or "—",
                     ("⚠%d" % kusur_sayisi) if kusur_sayisi else ""))
            if i % 40 == 0:
                print("   ... (%d/%d)" % (i, len(secili)))
        print("-" * 150)
        print("Toplam %d kayıt döküldü.\n" % len(secili))

    for d in kayitlar:
        ks = kaydi_denetle(d)
        if args.alan:
            ks = [k for k in ks if args.alan in k[0]]
        g = d.get("genel_bilgi") or {}
        if ks:
            kusurlu.append((d["_id"], g.get("banka_id"), g.get("kampanya_adi") or "", ks))
            for alan, _, gerekce in ks:
                sayac[(alan, gerekce.split("(")[0].strip())] += 1
                banka_sayac[g.get("banka_id")][alan] += 1
        elif args.hepsi:
            print("✅ [%s] %s" % (g.get("banka_id"), (g.get("kampanya_adi") or "")[:60]))

    print("=" * 80)
    print("NLP ÇIKTI DENETİMİ — %d kayıt tarandı, %d tanesinde kusur bulundu (%.1f%%)"
          % (len(kayitlar), len(kusurlu), 100.0 * len(kusurlu) / max(1, len(kayitlar))))
    print("=" * 80)

    for _id, banka, ad, ks in kusurlu:
        print("\n[%s] %s" % (banka, ad[:64]))
        print("   %s" % _id)
        for alan, deger, gerekce in ks:
            print("   ✗ %-38s = %-14s → %s" % (alan, str(deger)[:14], gerekce))

    print("\n" + "=" * 80)
    print("KUSUR TÜRÜ DAĞILIMI")
    print("=" * 80)
    for (alan, gerekce), n in sayac.most_common():
        print("  %4d  %-38s %s" % (n, alan, gerekce))

    print("\n" + "=" * 80)
    print("BANKAYA GÖRE KUSUR SAYISI")
    print("=" * 80)
    for banka, ct in sorted(banka_sayac.items(), key=lambda x: -sum(x[1].values())):
        print("  %-16s %3d" % (banka, sum(ct.values())))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([{"id": i, "banka": b, "ad": a,
                        "kusurlar": [{"alan": x, "deger": y, "gerekce": z} for x, y, z in k]}
                       for i, b, a, k in kusurlu], f, ensure_ascii=False, indent=1)
        print("\nJSON yazıldı: %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
