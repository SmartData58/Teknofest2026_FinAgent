# -*- coding: utf-8 -*-
"""
qdrant_payload_kontrol.py — "banka_kodu YOK" uyarısı GERÇEK mi?

/health uyarısı aylardır sürüyor ama indexing.py metadata'ya banka_kodu YAZIYOR.
Bu script tartışmayı bitirir: Qdrant'taki GERÇEK payload'ı olduğu gibi basar.

    python qdrant_payload_kontrol.py

SALT OKUNUR — hiçbir şey yazmaz/silmez.
"""
import json
import sys
from collections import Counter

try:
    from qdrant_client import QdrantClient
except ImportError:
    raise SystemExit("qdrant-client kurulu değil:  pip install qdrant-client")


def _paketi_bul():
    """Bu dosya nereden çalıştırılırsa çalıştırılsın chatbot paketini bul."""
    import os
    from pathlib import Path
    burasi = Path(__file__).resolve().parent
    for aday in (burasi, *burasi.parents):
        if (aday / "chatbot" / "indexing.py").exists():
            if str(aday) not in sys.path:
                sys.path.insert(0, str(aday))
            os.chdir(aday) if False else None
            return
    raise SystemExit("chatbot/ paketi bulunamadı — bu dosyayı proje kökünde çalıştırın.")


_paketi_bul()

try:
    from backend.evren_client import qdrant_ayarlari
except ModuleNotFoundError:
    from chatbot.evren_client import qdrant_ayarlari
from chatbot.indexing import COLLECTION_NAME, BANKA_KODU_YOLU, METADATA_ANAHTARI, payload_alani


def main():
    ayarlar = qdrant_ayarlari()
    print("=" * 78)
    print(f"KOLEKSİYON: {COLLECTION_NAME}   @ {ayarlar.get('url')}:{ayarlar.get('port')}"
          f"  prefix={ayarlar.get('prefix')}")
    print("=" * 78)

    client = QdrantClient(**ayarlar)
    if not client.collection_exists(COLLECTION_NAME):
        print("❌ Koleksiyon YOK. Önce indeksleyin:  python -m chatbot.indexing")
        return 1

    bilgi = client.get_collection(COLLECTION_NAME)
    sayi = bilgi.points_count or 0
    print(f"\nnokta sayısı : {sayi}")
    try:
        vek = bilgi.config.params.vectors
        print(f"vektör ayarı : {vek}")
    except Exception:
        pass

    if sayi == 0:
        print("\n❌ Koleksiyon boş.")
        return 1

    # --- 1. HAM PAYLOAD ---
    noktalar, _ = client.scroll(COLLECTION_NAME, limit=2, with_payload=True, with_vectors=False)
    print("\n" + "-" * 78)
    print("[1] HAM PAYLOAD (ilk kayıt) — anahtarların GERÇEK yerleşimi")
    print("-" * 78)
    p = noktalar[0].payload or {}
    kisaltilmis = json.loads(json.dumps(p, default=str))
    if isinstance(kisaltilmis.get("belge"), str) and len(kisaltilmis["belge"]) > 300:
        kisaltilmis["belge"] = kisaltilmis["belge"][:300] + " …(kısaltıldı)"
    print(json.dumps(kisaltilmis, ensure_ascii=False, indent=2))

    print(f"\n  üst seviye anahtarlar : {sorted(p.keys())}")
    ic = p.get(METADATA_ANAHTARI)
    if isinstance(ic, dict):
        print(f"  '{METADATA_ANAHTARI}' altındaki : {sorted(ic.keys())}")

    ust = p.get("banka_kodu")
    icteki = ic.get("banka_kodu") if isinstance(ic, dict) else None
    print(f"\n  payload['banka_kodu']                -> {ust!r}")
    print(f"  payload['{METADATA_ANAHTARI}']['banka_kodu'] -> {icteki!r}")

    if icteki and not ust:
        print("\n  ✅ TEŞHİS: veri VAR ama İÇ İÇE. Eski /health kontrolü ve eski Qdrant")
        print(f"     filtresi üst seviyeye baktığı için boş sanıyordu. Doğru yol: {BANKA_KODU_YOLU}")
    elif ust:
        print("\n  ℹ️ Alan üst seviyede — LangChain dışı bir yazıcı kullanılmış olmalı.")
    else:
        print("\n  ❌ banka_kodu HİÇBİR YERDE yok — yazma tarafı gerçekten eksik.")
        print("     Yeniden indeksleyin: python -m chatbot.indexing")

    # --- 2. FİLTRE GERÇEKTEN ÇALIŞIYOR MU ---
    print("\n" + "-" * 78)
    print("[2] FİLTRE TESTİ — iki yol da denenip KAÇ nokta eşleştiğine bakılıyor")
    print("-" * 78)
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    ornek_kod = payload_alani(p, "banka_kodu")
    if not ornek_kod:
        print("  (örnek banka kodu bulunamadı, test atlandı)")
    else:
        print(f"  test edilen değer: {ornek_kod!r}\n")
        for yol in ("banka_kodu", BANKA_KODU_YOLU):
            try:
                n = client.count(
                    COLLECTION_NAME,
                    count_filter=Filter(must=[FieldCondition(key=yol, match=MatchValue(value=ornek_kod))]),
                    exact=True,
                ).count
                isaret = "✅" if n else "❌"
                print(f"  {isaret} key={yol!r:26} -> {n} eşleşme")
            except Exception as e:
                print(f"  ⚠️ key={yol!r:26} -> hata: {type(e).__name__}: {e}")
        print("\n  0 eşleşme veren yol, kodun ESKİ hâlinde kullanılan yoldur:")
        print("  bankaya göre filtreli her vektör araması bu yüzden boş dönüyordu.")

    # --- 3. DAĞILIM ---
    print("\n" + "-" * 78)
    print("[3] BANKA DAĞILIMI (tüm koleksiyon taranıyor)")
    print("-" * 78)
    sayac, bos, imlec = Counter(), 0, None
    while True:
        grup, imlec = client.scroll(COLLECTION_NAME, limit=256, offset=imlec,
                                    with_payload=True, with_vectors=False)
        if not grup:
            break
        for n in grup:
            kod = payload_alani(n.payload or {}, "banka_kodu")
            if kod:
                sayac[str(kod)] += 1
            else:
                bos += 1
        if imlec is None:
            break
    for kod, adet in sayac.most_common():
        print(f"  {kod:<22} {adet}")
    if bos:
        print(f"  {'(banka_kodu BOŞ)':<22} {bos}   ⚠️ bu kayıtlar filtreli aramada hiç çıkmaz")
    if not sayac:
        print("  ❌ hiçbir kayıtta banka_kodu yok.")

    # --- 4. İÇERİK ANAHTARI ---
    print("\n" + "-" * 78)
    print("[4] İÇERİK ANAHTARI")
    print("-" * 78)
    if "belge" in p:
        print("  ✅ 'belge' var — sohbet tarafı content_payload_key='belge' okuyor, uyumlu.")
    else:
        print(f"  ❌ 'belge' YOK (bulunanlar: {sorted(p.keys())}) -> arama sonuçları BOŞ içerik döner.")

    print("\n" + "=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())