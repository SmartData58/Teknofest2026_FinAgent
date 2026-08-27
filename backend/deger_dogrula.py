# -*- coding: utf-8 -*-
"""
deger_dogrula.py — Dashboard'daki SAYILARI kaynak metinle karşılaştırır.

⚠️ SALT OKUNUR: hiçbir şey yazmaz, silmez, güncellemez.

NEDEN:
  "En Düşük Tahsis Ücreti" panelinde şunlar görünüyordu:
      Türkiye Finans  ... 4,2 TL        (iki kampanyada AYNI)
      Kuveyt Türk     ... 36,376 TL     (iki kampanyada AYNI)
      Vakıf Katılım   ... 75 TL   <- kampanya adı: "%75 Komisyon indirimi"
  Bir tahsis ücretinin 4,2 TL olması gerçekçi değil; 75 ise büyük olasılıkla
  metindeki "%75" yüzdesinin TL sanılması. Ama bunlar TAHMİN. Bu araç tahmini
  ölçüye çevirir: her sayının kaynak metinde GERÇEKTEN nasıl geçtiğini gösterir.

NE YAPAR (uydurmaz, yalnızca gösterir):
  1. Yapısal alandaki sayıyı alır.
  2. Kampanyanın ham metninde o sayıyı arar ve ÇEVRESİNDEKİ metni basar.
  3. Şüphe işaretlerini bayraklar:
       • YOK        : sayı metinde hiç geçmiyor (nereden geldi?)
       • YUZDE      : metinde yalnızca "%" ile geçiyor (oran, TL değil)
       • TEKRAR     : aynı bankada birden çok kampanyada AYNI değer
       • KUCUK      : tahsis ücreti için gerçekçi olmayacak kadar küçük
  4. Kaynak URL'yi basar — bankanın sayfasından gözle teyit edebilesiniz.

KULLANIM:
    python deger_dogrula.py                      # tahsis_ucreti (varsayılan)
    python deger_dogrula.py --alan kar_payi_orani
    python deger_dogrula.py --alan odul_tutari --limit 30
    docker compose ... exec backend python deger_dogrula.py
"""
import argparse
import os
import re
from collections import defaultdict
from pymongo import MongoClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _get_mongo_uri() -> str:
    if os.getenv("MONGO_URI"):
        return os.getenv("MONGO_URI")
    user = os.getenv("MONGO_USER", "admin")
    password = os.getenv("MONGO_PASSWORD", "")
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    if password:
        return f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
    return f"mongodb://{host}:{port}/?authSource=admin"

MONGO_URI = _get_mongo_uri()

# alan adı -> (belgedeki yol, insan okunur ad, gerçekçi alt sınır)
# Alt sınır yalnızca "şüpheli" işareti içindir; veriyi DEĞİŞTİRMEZ.
ALANLAR = {
    "tahsis_ucreti":   ("finansman_detay.tahsis_ucreti",   "Tahsis Ücreti (TL)", 50.0),
    "kar_payi_orani":  ("finansman_detay.kar_payi_orani",  "Kâr Payı (%)",       None),
    "odul_tutari":     ("promosyon_detay.odul_tutari",     "Ödül (TL)",          None),
    "vade_ay":         ("finansman_detay.vade_ay",         "Vade (Ay)",          None),
}


def ic_al(belge, yol):
    """'a.b.c' yolundan değer okur."""
    x = belge
    for p in yol.split("."):
        if not isinstance(x, dict):
            return None
        x = x.get(p)
    return x


def ham_metin(belge):
    parcalar = [
        (belge.get("genel_bilgi") or {}).get("kampanya_adi") or "",
        (belge.get("genel_bilgi") or {}).get("metin") or "",
        belge.get("ham_metin") or "",
        str(belge.get("kosullar") or ""),
        (belge.get("finansman_detay") or {}).get("masraf_bilgi") or "",
    ]
    return " ".join(str(p) for p in parcalar if p)


def sayi_kaliplari(deger):
    """Bir sayının metinde geçebileceği yazımları üretir.

    Türkçe metinlerde aynı sayı '4,2' / '4.2' / '4,20' / '36.376' / '36376'
    gibi yazılabiliyor. Tek bir biçim aramak, gerçekte VAR olan bir sayıyı
    'yok' diye işaretlemeye yol açardı — bu yüzden birden çok yazım aranıyor.
    """
    kaliplar = set()
    try:
        f = float(deger)
    except (TypeError, ValueError):
        return kaliplar
    tam = int(f)
    # tam sayıysa: 36376 ve 36.376 (binlik ayraçlı)
    if abs(f - tam) < 1e-9:
        s = str(tam)
        kaliplar.add(s)
        if len(s) > 3:
            kaliplar.add(f"{tam:,}".replace(",", "."))
            kaliplar.add(f"{tam:,}")
    # ondalıklı: 4.2 -> '4,2' ve '4.2' ve '4,20'
    s2 = ("%g" % f)
    kaliplar.add(s2)
    kaliplar.add(s2.replace(".", ","))
    if "." in s2:
        tam_k, ond = s2.split(".")
        kaliplar.add(f"{tam_k},{ond.ljust(2, '0')}")
    return {k for k in kaliplar if k}


def cevre(metin, kalip, pencere=55):
    """Sayının metindeki ilk geçtiği yerin çevresini döndürür."""
    i = metin.find(kalip)
    if i < 0:
        return None
    bas = max(0, i - pencere)
    son = min(len(metin), i + len(kalip) + pencere)
    parca = metin[bas:son].replace("\n", " ")
    return ("…" if bas > 0 else "") + parca + ("…" if son < len(metin) else "")


def yuzde_mi(metin, kalip):
    """Sayı metinde YALNIZCA yüzde olarak mı geçiyor?

    '%75' ya da '75%' ya da 'yüzde 75' biçimlerinden biriyse ve TL/lira
    bağlamında hiç geçmiyorsa, bu sayının TL alanına yazılması hatalıdır.
    """
    yuzde_desen = re.compile(
        rf"(%\s*{re.escape(kalip)}\b)|(\b{re.escape(kalip)}\s*%)"
        rf"|(y[üu]zde\s+{re.escape(kalip)}\b)", re.IGNORECASE)
    tl_desen = re.compile(rf"\b{re.escape(kalip)}\s*(tl|try|₺|lira)\b", re.IGNORECASE)
    return bool(yuzde_desen.search(metin)) and not tl_desen.search(metin)


def _aday_veritabanlari(ist):
    """URI'de db adı olmayabilir; olası adları sırayla dener.

    Öncelik: MONGO_DB_NAME -> URI'deki ad (varsa) -> bilinen adlar ->
    sunucudaki diğer veritabanları.
    """
    adaylar = []
    cevre = os.getenv("MONGO_DB_NAME")
    if cevre:
        adaylar.append(cevre)
    try:
        varsayilan = ist.get_default_database()
        if varsayilan is not None:
            adaylar.append(varsayilan.name)
    except Exception:
        pass                      # URI'de db adı yok — normal, devam
    adaylar += ["smartdata", "finagent"]
    try:
        adaylar += [d for d in ist.list_database_names()
                    if d not in ("admin", "config", "local")]
    except Exception:
        pass
    # sırayı koruyarak tekrarları at
    return list(dict.fromkeys(adaylar))


def _koleksiyon_bul(ist, tercih_edilen, yol):
    """Aranan alanı GERÇEKTEN içeren koleksiyonu bulur.

    Yalnızca "var mı" değil, "içinde bu alan dolu kayıt var mı" diye bakıyor:
    aynı adda boş bir koleksiyon varsa ona takılıp 'veri yok' demesin.
    """
    denenenler = []
    for db_adi in _aday_veritabanlari(ist):
        db = ist[db_adi]
        try:
            kol_adlari = db.list_collection_names()
        except Exception:
            continue
        # tercih edilen önce, sonra diğerleri
        sirali = ([tercih_edilen] if tercih_edilen in kol_adlari else []) + \
                 [k for k in kol_adlari if k != tercih_edilen]
        for k in sirali:
            try:
                adet = db[k].count_documents({yol: {"$nin": [None, "", 0]}}, limit=1)
            except Exception:
                continue
            denenenler.append(f"{db_adi}.{k}")
            if adet:
                print(f"  📂 Koleksiyon: {db_adi}.{k}\n")
                return db[k]
    raise SystemExit(
        f"\n❌ '{yol}' alanı dolu hiçbir koleksiyon bulunamadı.\n"
        f"   Denenen: {', '.join(denenenler) or '(hiçbiri)'}\n"
        "   MONGO_URI / MONGO_DB_NAME değerlerini kontrol edin."
    )


def main():
    ap = argparse.ArgumentParser(description="Yapısal sayıları kaynak metinle karşılaştırır")
    ap.add_argument("--alan", default="tahsis_ucreti", choices=sorted(ALANLAR))
    ap.add_argument("--limit", type=int, default=20, help="kaç kayıt gösterilsin")
    ap.add_argument("--koleksiyon", default="islenmis_kampanyalar")
    ap.add_argument("--sadece-supheli", action="store_true", help="yalnızca bayraklı kayıtlar")
    a = ap.parse_args()

    yol, etiket, alt_sinir = ALANLAR[a.alan]

    ist = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)

    # 🛠️ HATA DÜZELTMESİ: burada `ist.get_default_database() or ist["smartdata"]`
    # yazıyordu. get_default_database(), URI'de veritabanı adı YOKSA None
    # DÖNDÜRMEZ — ConfigurationError FIRLATIR. Bu yüzden `or` yedeği hiçbir
    # zaman çalışmadı ve script, bağlantı adresinde db adı bulunmayan her
    # kurulumda (bizimki dahil: .../?authSource=admin) çöküyordu.
    #
    # Ayrıca koleksiyon adı ortama göre değişebiliyor (islenmis_kampanyalar /
    # kampanyalar), veritabanı adı da (smartdata / finagent). Sabit isim
    # varsaymak yerine, aranan alanı GERÇEKTEN içeren koleksiyonu buluyoruz.
    kol = _koleksiyon_bul(ist, a.koleksiyon, yol)

    kayitlar = []
    for b in kol.find({}):
        d = ic_al(b, yol)
        if d in (None, "", 0):
            continue
        try:
            d = float(d)
        except (TypeError, ValueError):
            continue
        if d <= 0:
            continue
        gb = b.get("genel_bilgi") or {}
        kayitlar.append({
            "banka": b.get("banka_kodu") or gb.get("banka_id") or b.get("banka_adi") or "-",
            "ad": gb.get("kampanya_adi") or b.get("baslik") or "-",
            "deger": d,
            "metin": ham_metin(b),
            "url": gb.get("kaynak_url") or b.get("url") or "-",
        })

    if not kayitlar:
        raise SystemExit(f"\n'{yol}' alanı hiçbir kayıtta dolu değil.\n")

    # Aynı bankada tekrar eden değerleri bul (sabit/varsayılan olma şüphesi)
    sayac = defaultdict(int)
    for k in kayitlar:
        sayac[(k["banka"], k["deger"])] += 1

    kayitlar.sort(key=lambda k: k["deger"])
    print("=" * 78)
    print(f"  DEĞER DOĞRULAMA — {etiket}   ({len(kayitlar)} dolu kayıt)")
    print("=" * 78)
    print("  Her satırda: yapısal alandaki sayı  vs  ham metinde geçtiği yer.\n")

    bayrak_sayaci = defaultdict(int)
    gosterilen = 0
    for k in kayitlar:
        bayraklar = []
        kaliplar = sayi_kaliplari(k["deger"])
        bulunan_kalip, baglam = None, None
        for kal in sorted(kaliplar, key=len, reverse=True):
            b = cevre(k["metin"], kal)
            if b:
                bulunan_kalip, baglam = kal, b
                break

        if bulunan_kalip is None:
            bayraklar.append("YOK")
        elif yuzde_mi(k["metin"], bulunan_kalip):
            bayraklar.append("YUZDE")
        if sayac[(k["banka"], k["deger"])] > 1:
            bayraklar.append(f"TEKRAR x{sayac[(k['banka'], k['deger'])]}")
        if alt_sinir is not None and k["deger"] < alt_sinir:
            bayraklar.append("KUCUK")

        for b in bayraklar:
            bayrak_sayaci[b.split()[0]] += 1
        if a.sadece_supheli and not bayraklar:
            continue
        if gosterilen >= a.limit:
            continue
        gosterilen += 1

        isaret = ("  ⚠️ " + " | ".join(bayraklar)) if bayraklar else "  ✓"
        print(f"  {k['banka']:<16} {k['deger']:>12,.2f}{isaret}")
        print(f"     kampanya : {k['ad'][:64]}")
        if baglam:
            print(f"     metinde  : {baglam}")
        else:
            print("     metinde  : (bu sayı ham metinde HİÇ geçmiyor)")
        if k["url"] and k["url"] != "-":
            print(f"     kaynak   : {k['url']}")
        print()

    print("=" * 78)
    print("  ÖZET")
    print("  " + "-" * 74)
    print(f"  Dolu kayıt          : {len(kayitlar)}")
    for ad, aciklama in (
        ("YOK",    "sayı ham metinde hiç geçmiyor — nereden geldiği belirsiz"),
        ("YUZDE",  "metinde yalnızca YÜZDE olarak geçiyor — TL alanına yazılmış"),
        ("TEKRAR", "aynı bankada birden çok kampanyada aynı değer"),
        ("KUCUK",  f"{etiket} için gerçekçi olmayacak kadar küçük"),
    ):
        if bayrak_sayaci.get(ad):
            print(f"  {ad:<20}: {bayrak_sayaci[ad]:>4}  ({aciklama})")
    if not bayrak_sayaci:
        print("  Şüpheli kayıt yok — sayılar kaynak metinle tutarlı.")
    else:
        print("\n  Bayraklı kayıtların kaynak URL'lerini açıp bankanın kendi")
        print("  sayfasındaki değerle karşılaştırın; nihai teyit odur.")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()