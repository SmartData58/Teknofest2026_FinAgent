# -*- coding: utf-8 -*-
"""
test_dayaniklilik.py — Servisler çöktüğünde sistem ne yapıyor? (chaos testi)

Kodun her yerinde try/except var ama bunların GERÇEKTEN işe yarayıp yaramadığı
hiç denenmedi. Bu script servisleri TEK TEK durdurur, her durumda bir soru
sorar ve şunlara bakar:

  • İstek 500 dönüyor mu, yoksa cevap üretiliyor mu?
  • Cevap boş mu kalıyor?
  • Kullanıcıya teknik çöp (Traceback, KeyError, connection refused) sızıyor mu?
  • Sonsuza kadar asılı kalıyor mu?
  • Servis geri açılınca sistem kendine geliyor mu?

⚠️ BU SCRIPT DOCKER KONTEYNERLERİNİ DURDURUR. Onay bayrağı olmadan hiçbir şey
durdurmaz, sadece ne yapacağını yazar:

    python test_dayaniklilik.py                  # KURU ÇALIŞTIRMA (hiçbir şey durdurmaz)
    python test_dayaniklilik.py --onayla         # gerçekten durdurup test eder
    python test_dayaniklilik.py --onayla --sec qdrant,redis
    python test_dayaniklilik.py --liste          # servisleri ve beklentileri göster

GÜVENLİK: Durdurulan her konteyner, test başarısız olsa da, Ctrl+C ile kesilse
de `finally` bloğunda geri başlatılır. Yine de canlı/demo ortamında çalıştırma.
"""
import argparse
import json
import os
import subprocess
import sys
import time

# --- test_api.py'deki istek fonksiyonunu yeniden kullan ----------------------
# (dosya adı sende "testapi.py" olabilir — ikisini de deniyoruz)
_BURASI = os.path.dirname(os.path.abspath(__file__))
if _BURASI not in sys.path:
    sys.path.insert(0, _BURASI)

istek_gonder = None
for _modul in ("test_api", "testapi"):
    try:
        istek_gonder = __import__(_modul).istek_gonder
        break
    except Exception:
        continue
if istek_gonder is None:
    raise SystemExit(
        "test_api.py (veya testapi.py) bulunamadı — bu script onun istek "
        "fonksiyonunu kullanıyor. İki dosyayı aynı klasöre koy."
    )

VARSAYILAN_URL = "http://localhost:8003/api/chat"
VARSAYILAN_HEALTH = "http://localhost:8003/health"

# =============================================================================
# SERVİSLER
#
# konteyner : `docker ps` çıktısındaki NAMES sütunu
# soru      : servis kapalıyken sorulacak, o servise EN ÇOK ihtiyaç duyan soru
# beklenti  : insan diliyle, kabul edilebilir bozulma nedir
# =============================================================================
SERVISLER = [
    {
        "ad": "qdrant",
        "konteyner": "smartdata-qdrant",
        "soru": "Kuveyt Türk'ün kampanya koşulları hakkında ne biliyorsun?",
        "beklenti": "Vektör arama çalışmaz. Cevap yine gelmeli (Mongo tablosu veya "
                    "'elimde bilgi yok' demeli); istek patlamamalı.",
    },
    {
        "ad": "redis",
        "konteyner": "smartdata-redis",
        "soru": "ödüllü kampanyaları listele",
        "beklenti": "Önbellek devre dışı kalır, her istek baştan hesaplanır. "
                    "Cevap ve tablo normal gelmeli.",
    },
    {
        "ad": "mongodb",
        "konteyner": "smartdata-mongodb",
        "soru": "en yüksek ödüllü kampanyaları listele",
        "beklenti": "Tablo üretilemez. Cevap yine gelmeli — ya Qdrant metninden "
                    "ya da 'veri bulunamadı' diyerek. Kesinlikle 500 dönmemeli.",
    },
    {
        "ad": "llm",
        "konteyner": "teknofest2026_finagent-llm-1",
        "soru": "Kuveyt Türk kampanyalarını listele",
        "beklenti": "Yapay zeka yorumu üretilemez. Tablo YİNE de gelmeli "
                    "(Mongo'dan geliyor, LLM'e bağlı değil) ve kullanıcıya "
                    "anlaşılır bir uyarı gösterilmeli — boş ekran olmamalı.",
    },
    {
        "ad": "embedding",
        "konteyner": "teknofest2026_finagent-embedding-1",
        "soru": "kampanya şartları neler",
        "beklenti": "Sorgu vektörlenemez -> vektör arama boş döner. Cevap yine "
                    "gelmeli, istek patlamamalı.",
    },
]

# Kullanıcıya ASLA sızmaması gereken teknik çöp
SIZINTI_KALIPLARI = [
    "Traceback", "KeyError", "AttributeError", "ConnectionError", "ConnectionRefused",
    "connection refused", "ServerSelectionTimeoutError", "500 Internal Server Error",
    "httpx.", "pymongo.", "qdrant_client", "redis.exceptions",
]


def docker(*args, sessiz=True):
    """docker komutu çalıştırır; (basarili, cikti) döner."""
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=90)
        if not sessiz:
            print(f"      $ docker {' '.join(args)} -> {r.returncode}")
        return r.returncode == 0, (r.stdout or r.stderr).strip()
    except FileNotFoundError:
        return False, "docker komutu bulunamadı (PATH'te değil)"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def konteyner_var_mi(ad):
    ok, cikti = docker("ps", "-a", "--format", "{{.Names}}")
    return ok and ad in cikti.split()


def calisiyor_mu(ad):
    ok, cikti = docker("ps", "--format", "{{.Names}}")
    return ok and ad in cikti.split()


def health_oku(url, zaman_asimi=10):
    try:
        import requests
        r = requests.get(url, timeout=zaman_asimi)
        return r.status_code, r.json()
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def soru_sor(url, soru, zaman_asimi):
    """Tek bir soru gönderir; (sonuc, hata) döner."""
    try:
        return istek_gonder(url, soru, [], "tr", "analist", zaman_asimi), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def sonucu_degerlendir(sonuc, hata):
    """Servis kapalıyken kabul edilebilir mi? (sorunlar listesi döner)"""
    sorunlar = []
    if hata:
        sorunlar.append(f"İSTEK PATLADI: {hata}")
        return sorunlar

    metin = (sonuc.get("metin") or "").strip()
    ham = sonuc.get("ham") or ""
    if not metin and not sonuc.get("chart"):
        sorunlar.append("cevap TAMAMEN BOŞ (ne metin ne tablo)")
    for kalip in SIZINTI_KALIPLARI:
        if kalip.lower() in ham.lower():
            sorunlar.append(f"TEKNİK ÇÖP SIZDI: {kalip!r} kullanıcıya görünüyor")
            break
    return sorunlar


def servis_testi(servis, url, zaman_asimi, onayla):
    print(f"\n{'='*78}\nSERVİS: {servis['ad']}  ({servis['konteyner']})")
    print(f"  beklenti: {servis['beklenti']}")
    print(f"  soru    : {servis['soru']!r}")

    if not onayla:
        print("  🟡 KURU ÇALIŞTIRMA — konteyner durdurulmadı. Gerçek test için --onayla ver.")
        return None

    if not konteyner_var_mi(servis["konteyner"]):
        print(f"  ⚠️ ATLANDI: '{servis['konteyner']}' adlı konteyner yok. "
              f"`docker ps` ile adı kontrol edip --konteyner ile düzeltebilirsin.")
        return None

    onceden_calisiyordu = calisiyor_mu(servis["konteyner"])
    durduruldu = False
    try:
        print(f"  ⏸️  durduruluyor...")
        ok, cikti = docker("stop", servis["konteyner"])
        if not ok:
            print(f"  ❌ durdurulamadı: {cikti}")
            return None
        durduruldu = True
        time.sleep(2)

        baslangic = time.time()
        sonuc, hata = soru_sor(url, servis["soru"], zaman_asimi)
        gecen = round(time.time() - baslangic, 1)
        sorunlar = sonucu_degerlendir(sonuc, hata)

        if sonuc:
            chart = sonuc.get("chart")
            print(f"  ↳ {gecen}sn | tablo: {(chart or {}).get('type', 'yok')} "
                  f"({len((chart or {}).get('labels', []))} satır) | "
                  f"metin: {len(sonuc.get('metin') or '')} krktr")
            onizleme = (sonuc.get("metin") or "").replace("\n", " ")[:160]
            print(f"  ↳ cevap: {onizleme}")
        for s in sorunlar:
            print(f"  → {s}")
        print(f"  {'✅ NAZİKÇE BOZULDU' if not sorunlar else '❌ SORUNLU'}")
        return {"servis": servis["ad"], "sure": gecen, "sorunlar": sorunlar,
                "metin": (sonuc or {}).get("metin", ""),
                "tablo_satir": len(((sonuc or {}).get("chart") or {}).get("labels", []))}
    finally:
        # 🛡️ Ne olursa olsun konteyneri geri aç.
        if durduruldu and onceden_calisiyordu:
            print("  ▶️  geri başlatılıyor...")
            docker("start", servis["konteyner"])
            time.sleep(3)


def main():
    ap = argparse.ArgumentParser(description="Servis çökme dayanıklılığı testi")
    ap.add_argument("--url", default=VARSAYILAN_URL)
    ap.add_argument("--health", default=VARSAYILAN_HEALTH)
    ap.add_argument("--onayla", action="store_true",
                    help="konteynerleri GERÇEKTEN durdur (yoksa kuru çalıştırma)")
    ap.add_argument("--sec", default="", help="sadece bu servisler (virgülle): qdrant,redis,...")
    ap.add_argument("--zaman-asimi", type=float, default=240.0)
    ap.add_argument("--konteyner", default="", help="ad=konteyner çiftleri: qdrant=my-qdrant,redis=my-redis")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--kayit", default="")
    args = ap.parse_args()

    # Konteyner adı ezmeleri
    for parca in filter(None, args.konteyner.split(",")):
        if "=" in parca:
            ad, kt = parca.split("=", 1)
            for s in SERVISLER:
                if s["ad"] == ad.strip():
                    s["konteyner"] = kt.strip()

    if args.liste:
        for s in SERVISLER:
            print(f"  {s['ad']:<10} {s['konteyner']:<38} {s['beklenti'][:60]}")
        return 0

    secili = SERVISLER
    if args.sec:
        adlar = {a.strip().lower() for a in args.sec.split(",")}
        secili = [s for s in SERVISLER if s["ad"] in adlar]
        if not secili:
            print("Seçime uyan servis yok. --liste ile bakabilirsin.")
            return 1

    print("=" * 78)
    print(f"DAYANIKLILIK TESTİ | {args.url}")
    print(f"Mod: {'GERÇEK (konteynerler durdurulacak)' if args.onayla else 'KURU ÇALIŞTIRMA'}")
    print("=" * 78)

    # --- 1. TEMEL DURUM: her şey açıkken çalışıyor mu? ---
    print("\n[TEMEL] Sistem sağlıklıyken bir soru soruluyor...")
    kod, veri = health_oku(args.health)
    print(f"  /health -> {kod} {json.dumps(veri, ensure_ascii=False)[:180] if isinstance(veri, dict) else veri}")
    sonuc, hata = soru_sor(args.url, "ödüllü kampanyaları listele", args.zaman_asimi)
    if hata or not (sonuc.get("metin") or sonuc.get("chart")):
        print(f"  ❌ TEMEL DURUM BAŞARISIZ ({hata or 'boş cevap'}) — "
              f"sistem zaten çalışmıyor, chaos testine geçmenin anlamı yok.")
        return 1
    print(f"  ✅ temel durum iyi ({sonuc['sure']}sn, "
          f"{len((sonuc.get('chart') or {}).get('labels', []))} satır tablo)")

    # --- 2. SERVİSLERİ TEK TEK DÜŞÜR ---
    kayitlar = []
    for servis in secili:
        r = servis_testi(servis, args.url, args.zaman_asimi, args.onayla)
        if r:
            kayitlar.append(r)

    if not args.onayla:
        print(f"\n{'='*78}\nKuru çalıştırma bitti. Gerçek test için:  "
              f"python {os.path.basename(__file__)} --onayla\n{'='*78}")
        return 0

    # --- 3. TOPARLANMA: her şey geri açıldı mı? ---
    print(f"\n{'='*78}\n[TOPARLANMA] Servisler geri açıldı, sistem kendine geldi mi?")
    time.sleep(5)
    kod, veri = health_oku(args.health)
    print(f"  /health -> {kod}")
    sonuc, hata = soru_sor(args.url, "ödüllü kampanyaları listele", args.zaman_asimi)
    toparlandi = not hata and bool(sonuc.get("chart") or sonuc.get("metin"))
    print(f"  {'✅ toparlandı' if toparlandi else '❌ TOPARLANAMADI — elle kontrol et: docker ps'}")

    basarisiz = sum(1 for k in kayitlar if k["sorunlar"])
    print(f"\n{'='*78}")
    print(f"SONUÇ: {len(kayitlar)-basarisiz}/{len(kayitlar)} servis nazikçe bozuldu"
          f"{' | TOPARLANMA SORUNU' if not toparlandi else ''}")
    print("=" * 78)

    if args.kayit:
        with open(args.kayit, "w", encoding="utf-8") as f:
            json.dump({"servisler": kayitlar, "toparlandi": toparlandi}, f,
                      ensure_ascii=False, indent=2)
        print(f"Kayıt yazıldı: {args.kayit}")

    return 1 if (basarisiz or not toparlandi) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ KESİLDİ — durdurulmuş konteyner kalmış olabilir, kontrol et:")
        print("   docker ps -a --format '{{.Names}}\\t{{.Status}}'")
        sys.exit(130)