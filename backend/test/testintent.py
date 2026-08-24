# -*- coding: utf-8 -*-
"""Niyet + görselleştirme kararı senaryo testleri.

Ekran kaydındaki 4 mesaj ve TR/EN varyantları. Çalıştırma:
    python test_intent.py
"""
import sys, os

# 🛠️ `chatbot` paketini nerede olursa olsun bul: bu dosyanın klasörü, üst
# klasörleri ve her birinin altındaki "backend" klasörü denenir. Böylece test
# dosyası proje kökünde de, backend\ altında da, backend\chatbot\ altında da
# çalışır — hangi klasörden çağrıldığından bağımsız olarak.
def _paketi_bul():
    burasi = os.path.dirname(os.path.abspath(__file__))
    adaylar = []
    for ust in range(4):
        kok = burasi
        for _ in range(ust):
            kok = os.path.dirname(kok)
        adaylar.append(kok)
        adaylar.append(os.path.join(kok, "backend"))
    for aday in adaylar:
        if os.path.isfile(os.path.join(aday, "chatbot", "intent.py")):
            return aday
    return None

_KOK = _paketi_bul()
if _KOK and _KOK not in sys.path:
    sys.path.insert(0, _KOK)
elif not _KOK:
    raise SystemExit(
        "HATA: 'chatbot' paketi bulunamadi. Bu dosyayi projenin backend klasorune "
        "(ya da backend\\chatbot icine) koyup tekrar calistir."
    )

from chatbot.intent import niyet_bul, Mesaj, gorsel_limiti

GECMIS = [
    Mesaj("user", "can you list me interest rate of the banks"),
    Mesaj("assistant", "Based on the campaign data provided..."),
]

# (soru, gecmis, dil, beklenen_gorsel, beklenen_limit(musteri), not)
SENARYOLAR = [
    # --- Ekran kaydındaki 4 mesaj ---
    ("can you list me interest rate of the banks", (), "en", "tablo", 10,
     "EN liste isteği -> tablo (eskiden hiçbir şey gelmiyordu)"),
    ("bana para ödülü olan tüm kampanyaları listeler misin", GECMIS, "tr", "tablo", 10**6,
     "'listeler misin' + 'tüm' -> tablo, TÜM kayıtlar (eskiden tablo hiç gelmiyordu)"),
    ("bana para ödülü olan tüm kampanyaları grafik olarak verir misin", GECMIS, "tr", "grafik", 10**6,
     "açık grafik isteği -> grafik"),
    ("Kuveyt Türk ve diğer rakiplerle kıyaslandığında bu kampanyada hangi segmentlerde daha yüksek getiri sağlıyor?",
     GECMIS, "tr", None, 3,
     "YORUM sorusu -> grafik/tablo YOK (eskiden kâr payı grafiği çiziyordu)"),

    # --- Liste / tablo istekleri (TR ekli hâller) ---
    ("kampanyaları göster", (), "tr", "tablo", 10, "ek almış 'göster'"),
    ("Kuveyt Türk kampanyalarını detaylandır", (), "tr", "tablo", 10, "detaylandır"),
    ("ödülleri düşükten yükseğe sıralasana", (), "tr", "tablo", 10, "ek almış 'sırala'"),
    ("150 tanesini listele", (), "tr", "tablo", 150, "açık sayı limiti"),
    ("grafiq olaraqta veri r misn", (), "tr", "grafik", 10, "yazım hatalı grafik isteği"),

    # --- İngilizce ---
    ("show me the campaigns with the highest reward", (), "en", "tablo", 10, "EN show/highest"),
    ("compare the profit rates of the banks", (), "en", "tablo", 3, "EN karşılaştırma -> kısa özet tablo"),
    ("which banks have the lowest profit rate?", (), "en", "tablo", 3, "EN superlative"),
    ("draw a chart of the rewards", (), "en", "grafik", 10, "EN grafik isteği"),
    ("hello", (), "en", None, 3, "EN selamlama -> statik"),
    ("who can apply to this campaign?", GECMIS, "en", None, 3, "EN yorum sorusu -> görsel yok"),

    # --- Yorum / açıklama soruları (görsel ÜRETİLMEMELİ) ---
    ("Bu kampanyalara başvurmak için hangi koşulları karşılamam gerekiyor?", GECMIS, "tr", None, 3, "koşullar"),
    ("Bu kampanyaya kimler başvurabilir?", GECMIS, "tr", None, 3, "kimler"),
    ("Neden bu oran diğerlerinden düşük?", GECMIS, "tr", None, 3, "neden"),
    ("kampanya mevzuat hesaplama fonksiyonunu pythonda nasıl yazarım", (), "tr", None, 3, "kod sorusu"),

    # --- Normal veri sorusu -> 3 satırlık özet tablo ---
    ("Kuveyt Türk'ün kâr payı oranı ne durumda?", (), "tr", "tablo", 3, "normal veri sorusu -> 3 satır özet"),
    ("Merhaba", (), "tr", None, 3, "selamlama"),

    # --- Ağır imla hataları: bulanık (fuzzy) kök eşleştirme ---
    ("bana kmpanyalri lsitele", (), "tr", "tablo", 10, "harf düşmüş liste isteği -> bulanık eşleşme"),
    ("grafk olarak ver", (), "tr", "grafik", 10, "harf düşmüş grafik isteği"),
    ("kimlere bu kampanya uygulanir", (), "tr", None, 3, "bulanık katman YANLIŞ eşleşme yapmamalı"),
    ("bu kampanya nasil calisiyor", (), "tr", None, 3, "yorum sorusu, bulanık tetiklenmemeli"),
]


def calistir():
    hata = 0
    for soru, gecmis, dil, beklenen_gorsel, beklenen_limit, aciklama in SENARYOLAR:
        n = niyet_bul(soru, gecmis, dil=dil)
        limit = gorsel_limiti(soru, n.gorsel, "musteri")
        ok_g = n.gorsel == beklenen_gorsel
        ok_l = limit == beklenen_limit
        isaret = "✅" if (ok_g and ok_l) else "❌"
        if not (ok_g and ok_l):
            hata += 1
        print(f"{isaret} [{dil}] {soru[:62]!r}")
        print(f"      niyet={n.tur:14s} gorsel={str(n.gorsel):7s} (beklenen {beklenen_gorsel}) "
              f"limit={limit} (beklenen {beklenen_limit}) banka={n.banka_kodu} aciklayici={n.aciklayici}")
        print(f"      → {aciklama}")
    print("\n" + ("TÜM SENARYOLAR GEÇTİ ✅" if hata == 0 else f"{hata} SENARYO BAŞARISIZ ❌"))
    return hata


if __name__ == "__main__":
    sys.exit(1 if calistir() else 0)