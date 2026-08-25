# =============================================================================
# veri_kalite_denetimi.py — ASIL SORUNU ÖLÇER: yapısal alanlar ne kadar BOŞ?
#
# NEDEN BU ARAÇ:
#   Sohbette şu cevaplar çıkıyor ve hepsi "uydurma" gibi görünüyor:
#     • "en yüksek kâr payı oranı %0"
#     • "Kuveyt Türk'e ait kâr payı oranları mevcut değildir"
#     • "kâr payı/faiz oranları %0 olarak sabitlenmiş"
#   Model uydurmuyor. Kendisine verilen `kar_payi` alanı GERÇEKTEN 0.
#   Yani sorun prompt'ta ya da arayüzde değil, VERİDE: kampanya metninde
#   açıkça "%2,99" yazarken yapısal alan boş kalıyor.
#
#   Bu script o boşluğu SAYIYLA gösterir. Özellikle en kritik rakam:
#   "metinde oran geçiyor AMA yapısal alan 0" — yani çıkarımın kaçırdığı kayıt.
#   Bu sayı yüksekse, chatbot tarafında yapılacak hiçbir iyileştirme
#   sonucu düzeltmez; düzeltilmesi gereken yer çıkarım (NLP/regex) katmanıdır.
#
# KULLANIM:
#   docker compose ... exec backend python veri_kalite_denetimi.py
#   python veri_kalite_denetimi.py --ornek 15   # kaçırılan kayıtlardan örnek
# =============================================================================
import argparse
import re
import sys
from collections import defaultdict

try:
    from chatbot.generate_response import (
        _kampanya_kayitlarini_getir, extract_campaign_data,
    )
except Exception as e:
    sys.exit(
        f"chatbot.generate_response içe aktarılamadı: {e}\n"
        "Bu scripti backend konteynerinin içinden (ya da proje kökünden) çalıştırın."
    )

# Metinde bir ORAN geçiyor mu? Türkçe yazımların hepsi:
#   %2,99  /  % 2.99  /  2,99%  /  yüzde 2,99  /  oran: %2,99
_ORAN_METINDE = re.compile(
    r"(?:%\s*\d{1,2}(?:[.,]\d{1,2})?)"
    r"|(?:\d{1,2}(?:[.,]\d{1,2})?\s*%)"
    r"|(?:y[uü]zde\s+\d{1,2}(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)
# Metinde bir TUTAR (TL) geçiyor mu?
_TUTAR_METINDE = re.compile(
    r"\d[\d.,]{2,}\s*(?:tl|try|₺)", re.IGNORECASE
)
# Metinde VADE (ay) geçiyor mu?
_VADE_METINDE = re.compile(r"\d{1,3}\s*(?:ay|taksit)\b", re.IGNORECASE)


def _yuzde(bolum, toplam):
    return (100.0 * bolum / toplam) if toplam else 0.0


def _cubuk(oran, genislik=28):
    dolu = int(round(genislik * oran / 100))
    return "█" * dolu + "·" * (genislik - dolu)


def main():
    ap = argparse.ArgumentParser(description="Kampanya verisi yapısal alan doluluk denetimi")
    ap.add_argument("--ornek", type=int, default=5,
                    help="kaçırılan kayıtlardan kaç örnek gösterilsin (varsayılan 5)")
    a = ap.parse_args()

    print("=" * 74)
    print("  VERİ KALİTE DENETİMİ — yapısal alanlar ne kadar dolu?")
    print("=" * 74)

    ham = _kampanya_kayitlarini_getir()
    if not ham:
        sys.exit("\n❌ MongoDB'den hiç kampanya kaydı okunamadı.")
    kayitlar = [extract_campaign_data(d) for d in ham]
    n = len(kayitlar)
    print(f"\n  Toplam kayıt: {n}\n")

    # --- Genel doluluk
    dolu = {
        "kar_payi": sum(1 for c in kayitlar if c["kar_payi"] > 0),
        "odul": sum(1 for c in kayitlar if c["odul"] > 0),
        "vade": sum(1 for c in kayitlar if c["vade"] > 0),
        "url": sum(1 for c in kayitlar if c["url"] and c["url"] != "-"),
    }
    print("  YAPISAL ALAN DOLULUĞU")
    print("  " + "-" * 70)
    for alan, adet in dolu.items():
        o = _yuzde(adet, n)
        print(f"  {alan:<10} {_cubuk(o)} {adet:>4}/{n}  (%{o:.1f})")

    # --- EN KRİTİK ÖLÇÜM: metinde var ama alanda yok
    print("\n  ÇIKARIMIN KAÇIRDIKLARI (metinde geçiyor, yapısal alan BOŞ)")
    print("  " + "-" * 70)
    kacan = {"kar_payi": [], "odul": [], "vade": []}
    for c in kayitlar:
        metin = f"{c.get('kampanya_adi','')} {c.get('metin','')}"
        if c["kar_payi"] == 0 and _ORAN_METINDE.search(metin):
            kacan["kar_payi"].append(c)
        if c["odul"] == 0 and _TUTAR_METINDE.search(metin):
            kacan["odul"].append(c)
        if c["vade"] == 0 and _VADE_METINDE.search(metin):
            kacan["vade"].append(c)

    for alan, liste in kacan.items():
        bos = n - dolu[alan]
        o = _yuzde(len(liste), bos) if bos else 0.0
        print(f"  {alan:<10} {len(liste):>4} kayıt  "
              f"(boş olanların %{o:.1f}'i aslında metinde bu bilgiyi TAŞIYOR)")

    # --- Banka bazında kar_payi doluluğu (kıyaslama bunun üstünde çalışıyor)
    print("\n  BANKA BAZINDA kar_payi DOLULUĞU")
    print("  " + "-" * 70)
    bankalar = defaultdict(lambda: {"toplam": 0, "dolu": 0})
    for c in kayitlar:
        b = bankalar[c["banka"]]
        b["toplam"] += 1
        if c["kar_payi"] > 0:
            b["dolu"] += 1
    for ad, s in sorted(bankalar.items(), key=lambda x: -x[1]["toplam"]):
        o = _yuzde(s["dolu"], s["toplam"])
        isaret = "  ⚠️ HİÇ ORAN YOK" if s["dolu"] == 0 else ""
        print(f"  {ad:<22} {_cubuk(o, 20)} {s['dolu']:>3}/{s['toplam']:<4} (%{o:.1f}){isaret}")

    # --- Örnekler
    if a.ornek and kacan["kar_payi"]:
        print(f"\n  KAÇIRILAN ORAN ÖRNEKLERİ (ilk {a.ornek})")
        print("  " + "-" * 70)
        for c in kacan["kar_payi"][:a.ornek]:
            metin = f"{c.get('kampanya_adi','')} {c.get('metin','')}"
            bulunan = _ORAN_METINDE.findall(metin)[:3]
            print(f"\n  • {c['banka']} — {c['kampanya_adi'][:52]}")
            print(f"    kayıtlı kar_payi : {c['kar_payi']}")
            print(f"    metinde geçen    : {', '.join(bulunan)}")

    # --- Yorum
    print("\n" + "=" * 74)
    kp_oran = _yuzde(dolu["kar_payi"], n)
    kacan_oran = _yuzde(len(kacan["kar_payi"]), n)
    print("  SONUÇ")
    print("  " + "-" * 70)
    if kp_oran < 20:
        print(f"  ❌ Kayıtların yalnızca %{kp_oran:.1f}'inde kâr payı oranı DOLU.")
        print("     'En düşük/yüksek kâr payı', 'oranları kıyasla', 'oran trendi'")
        print("     türü sorular bu veriyle DOĞRU cevaplanamaz — chatbot tarafında")
        print("     yapılacak hiçbir düzeltme bunu telafi etmez.")
    else:
        print(f"  Kâr payı doluluğu: %{kp_oran:.1f}")
    if kacan_oran >= 5:
        print(f"\n  🔧 EN HIZLI KAZANÇ: kayıtların %{kacan_oran:.1f}'inde oran METİNDE VAR")
        print("     ama yapısal alana yazılmamış. Çıkarım (regex/NLP) katmanı")
        print("     düzeltilirse bu kayıtlar ek veri toplamadan kazanılır.")
    print("=" * 74 + "\n")


if __name__ == "__main__":
    main()