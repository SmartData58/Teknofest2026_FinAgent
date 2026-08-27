# -*- coding: utf-8 -*-
"""nlp_etiket_duzelt.py — eski çıkarımlardan kalan geçersiz değerleri düzeltir.

`nlp_izle.py` SALT OKUNUR bir denetçidir; bu betik ise onun bulduğu kusurları
depoda düzeltir. İkisi bilerek ayrı: denetim aracının asla yazmaması gerekir.

DÜZELTİLEN İKİ KUSUR (27.08.2026 denetimi):

  1) `genel_bilgi.kampanya_turu == "alisveris_kampanyası"`  (23 kayıt)
     campaign_classifier.py'deki kural tablosu, aynı dosyanın GECERLI_TURLER
     kümesinde OLMAYAN bir etiket üretiyordu; kümeyi hiçbir yer dayatmadığı
     için geçersiz etiket sessizce Mongo'ya yazıldı. Kural düzeltildi
     (`alisveris_puani`) ve küme artık dayatılıyor. Bu adım geride kalan eski
     kayıtları hizalar. Anlam aynı → BİLGİ KAYBI YOK, geri alınabilir.

  2) `finansman_detay.kar_payi_orani == 98.0`  (2 kayıt)
     Katılma hesabı PAYLAŞIM oranı, finansman KÂR PAYI oranı alanına yazılmış.
     Farklı kavramlar; alanın dolu 8 kaydının 2'si buydu, yani banka kıyas
     tablosundaki "en yüksek kâr payı" değerini bu bozuyordu. llm_extractor
     artık hem bağlamdan hem 50'lik üst sınırdan yakalıyor.
     ⚠️ Bu adım bir DEĞER SİLER (None yapar) — varsayılan olarak KAPALI,
     açmak için `--orani-temizle` ver.

KULLANIM
    python nlp_etiket_duzelt.py                    # önizleme, yazmaz
    python nlp_etiket_duzelt.py --uygula
    python nlp_etiket_duzelt.py --uygula --orani-temizle
"""
import argparse
import os
import sys

from pymongo import MongoClient

sys.stdout.reconfigure(encoding="utf-8")

# Kimlik bilgisi komut satırında değil, ortamda/.env'de durur.
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise SystemExit(
        "HATA: MONGO_URI ortam değişkeni yok.\n"
        "Bu betiği backend konteynerinde çalıştır (.env oradan yükleniyor):\n"
        "  docker exec teknofest2026_finagent-backend-1 python "
        "/app/test/nlp_etiket_duzelt.py --uygula"
    )
DB_ADI = os.getenv("MONGO_DB_NAME") or os.getenv("CAMPAIGN_DB") or "smartdata"

ESKI_TUR, YENI_TUR = "alisveris_kampanyası", "alisveris_puani"
BOZUK_ORAN = 98.0


def main():
    ap = argparse.ArgumentParser(description="Eski geçersiz NLP değerlerini düzelt")
    ap.add_argument("--uygula", action="store_true",
                    help="gerçekten yaz (verilmezse yalnızca önizleme)")
    ap.add_argument("--orani-temizle", action="store_true",
                    help="katılma hesabı paylaşım oranını kar_payi_orani'ndan sil")
    args = ap.parse_args()

    c = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[DB_ADI]["islenmis_kampanyalar"]
    yazma = args.uygula
    print("MOD:", "UYGULA (yazılacak)" if yazma else "ÖNİZLEME (yazılmayacak)")
    print("=" * 70)

    # --- 1) geçersiz tür etiketi -------------------------------------------
    kosul = {"genel_bilgi.kampanya_turu": ESKI_TUR}
    n = c.count_documents(kosul)
    print(f"\n1) kampanya_turu  {ESKI_TUR!r} → {YENI_TUR!r}   ({n} kayıt)")
    for d in c.find(kosul, {"genel_bilgi.kampanya_adi": 1}).limit(5):
        print("     -", (d.get("genel_bilgi", {}).get("kampanya_adi") or "")[:58])
    if n > 5:
        print(f"     ... (+{n - 5} kayıt daha)")
    if yazma and n:
        r = c.update_many(kosul, {"$set": {"genel_bilgi.kampanya_turu": YENI_TUR}})
        print(f"   ✅ güncellenen: {r.modified_count}")

    # --- 2) yanlış kavramdan gelen oran ------------------------------------
    kosul2 = {"finansman_detay.kar_payi_orani": BOZUK_ORAN}
    n2 = c.count_documents(kosul2)
    print(f"\n2) kar_payi_orani {BOZUK_ORAN} → None   ({n2} kayıt)")
    for d in c.find(kosul2, {"genel_bilgi.kampanya_adi": 1, "genel_bilgi.banka_id": 1}):
        g = d.get("genel_bilgi", {})
        print(f"     - [{g.get('banka_id')}] {(g.get('kampanya_adi') or '')[:52]}")
    if not args.orani_temizle:
        print("   ⏭️  atlandı (değer siler; açmak için --orani-temizle)")
    elif yazma and n2:
        r = c.update_many(kosul2, {"$set": {"finansman_detay.kar_payi_orani": None}})
        print(f"   ✅ temizlenen: {r.modified_count}")

    # --- sonuç dağılımı -----------------------------------------------------
    print("\n" + "=" * 70)
    print("kampanya_turu dağılımı:")
    for x in c.aggregate([{"$group": {"_id": "$genel_bilgi.kampanya_turu",
                                      "n": {"$sum": 1}}},
                          {"$sort": {"n": -1}}]):
        print("   %-24s %d" % (x["_id"], x["n"]))

    if not yazma:
        print("\nHiçbir şey yazılmadı. Uygulamak için --uygula ekle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
