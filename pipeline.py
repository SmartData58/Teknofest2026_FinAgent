import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def log(msg: str):
    print(f"\n==========================================")
    print(f"🚀 [PIPELINE] {msg}")
    print(f"==========================================")


def run_step_1_seed():
    log("ADIM 1: Banka Seed İşlemi Başlatılıyor...")

    try:
        from backend.db.seed_banks import seed_bankalar
        seed_bankalar()
    except ModuleNotFoundError:
        try:
            from seed import seed_bankalar
            seed_bankalar()
        except Exception as e:
            print(f"❌ Seed çalıştırma hatası: {e}")
            sys.exit(1)


def run_step_2_runner(banka: str = None, hepsi: bool = False):
    log("ADIM 2: Scraper Verileri Toplanıyor...")

    try:
        from scraper.runner import main as runner_main

        # Scraper runner'ının beklediği sys.argv simülasyonu
        if hepsi:
            sys.argv = ["runner.py", "--hepsi"]
        elif banka:
            sys.argv = ["runner.py", banka]

        runner_main()
    except Exception as e:
        print(f"❌ Scraper / Runner çalıştırma hatası: {e}")
        sys.exit(1)


def run_step_3_extraction():
    log("ADIM 3: LLM & Kural Tabanlı Bilgi Çıkarımı Yapılıyor...")
    try:
        from backend.nlp.extraction.extractor import temiz_verilerden_bilgi_cikar
        temiz_verilerden_bilgi_cikar()
    except Exception as e:
        print(f"❌ Bilgi Çıkarım (Extractor) hatası: {e}")
        sys.exit(1)


def _vektorleme_sonucunu_raporla(adet: int):
    """⚠️ adet==0 ARTIK SADECE 'MongoDB boştu' anlamına gelir.

    Eskiden auto_init_qdrant() her hatayı yutup 0 döndüğü için, embedding
    servisi çöktüğünde ya da Qdrant'a yazılamadığında da bu mesaj basılıyor ve
    pipeline "🎉 TÜM PIPELINE BAŞARIYLA TAMAMLANDI" diyerek çıkış kodu 0
    veriyordu. Üstelik mesajın "Qdrant koleksiyonu değiştirilmedi" kısmı da
    yanlıştı: force_recreate=True koleksiyonu EN BAŞTA siler (kütüphane
    kaynağından doğrulandı), dolayısıyla yarıda kalan bir çalıştırma boş/yarım
    bir koleksiyon bırakabiliyordu. indexing.py artık hatayı yükseltiyor.
    """
    if adet == 0:
        print(
            "⚠️ MongoDB'de vektörlenecek kampanya bulunamadı; Qdrant koleksiyonuna\n"
            "   hiç dokunulmadı (silme de yapılmadı).\n"
            "   Kontrol: python mongo_durum.py"
        )
    else:
        print(f"✅ {adet} kampanya Qdrant'a vektörlendi.")


def _adim4_http_ile_calistir():
    """'chatbot' paketi yerel olarak import edilemedi — muhtemelen pipeline.py,
    sohbet servisinin (main.py + chatbot/) çalıştığı container'dan AYRI bir
    container'da/pakette çalışıyor. Kanıt: ADIM 1-3, backend.* ve scraper.*
    modüllerini sorunsuz import edebiliyor ama chatbot.* hiç bulunamıyor — yani
    bu ortamda o paket dosya sisteminde bile yok, bir PYTHONPATH ayarı bunu
    çözmez.

    Bu durumda aynı işi, sohbet servisinin sunduğu POST /admin/reindex ucunu
    HTTP üzerinden çağırarak yaptırıyoruz (container sınırını import değil ağ
    üzerinden aşan tek yol budur). Hedef adres CHATBOT_SERVICE_URL ortam
    değişkeninden okunur — docker-compose.yml'nizde main.py'yi çalıştıran
    servisin adını buraya yazmanız gerekir (ör. "http://backend:8000";
    gerçek servis adı sizin compose dosyanıza göre değişir, buradaki
    "localhost" varsayılanı sadece aynı container/host'ta çalıştırma durumu
    içindir).
    """
    import urllib.error
    import urllib.request

    # 🛠️ Varsayılan artık http://backend:8000 — localhost DEĞİL. Doğrulandı:
    # pipeline.py "docker compose exec scraper python pipeline.py ..." ile
    # ÇALIŞIYOR, yani "scraper" container'ının İÇİNDEN çalışıyor. Bir
    # container'ın içinden "localhost" HER ZAMAN o container'ın kendisini
    # işaret eder — backend container'ının host'a açtığı 8003 portuna (hatta
    # kendi iç portu 8000'e bile) "localhost" ile ASLA ulaşılamaz. Aynı Docker
    # Compose ağındaki container'lar birbirine, host'a açılan portla değil,
    # compose'daki SERVİS ADIYLA ve container'ın KENDİ İÇ PORTUYLA ulaşır:
    # "backend" (compose service adı) + 8000 (main.py'nin container içinde
    # dinlediği port, docker-compose.yml'de "8003:8000" olarak host'a
    # eşlenmiş olan İKİNCİ sayı). Farklı bir servis adından çalıştırırsanız
    # CHATBOT_SERVICE_URL ortam değişkeniyle geçersiz kılabilirsiniz.
    taban_url = os.getenv("CHATBOT_SERVICE_URL", "http://backend:8000").rstrip("/")
    url = f"{taban_url}/admin/reindex"
    print(
        "ℹ️ 'chatbot' paketi bu ortamda import edilemiyor (ayrı bir servis/container "
        "olabilir).\n"
        f"   Bunun yerine sohbet servisinin admin ucu deneniyor: POST {url}"
    )

    headers = {"Content-Type": "application/json"}
    token = os.getenv("ADMIN_TOKEN")
    if token:
        headers["X-Admin-Token"] = token

    istek = urllib.request.Request(url, method="POST", headers=headers, data=b"{}")
    # 🛠️ HTTPError, URLError'ın ALT SINIFIDIR. Aşağıdaki `except URLError` bloğu
    # bu yüzden 500'ü de yakalayıp "adrese ulaşılamadı" diyordu — oysa adrese
    # ULAŞILMIŞTI, sunucu tarafında vektörleme patlamıştı. Sunucunun gövdesini
    # okuyup gerçek sebebi göstermek için HTTPError ayrı yakalanıyor.

    # 🛠️ Proxy'yi BİLEREK devre dışı bırakıyoruz. Windows'ta urllib.request,
    # varsayılan olarak sistem proxy ayarlarını (kayıt defterinden/WinINet)
    # otomatik okur ve "localhost" isteklerini bile bir proxy üzerinden
    # göndermeye çalışabilir — curl.exe bunu yapmadığı için `curl.exe` çalışırken
    # aynı adrese Python'dan "Connection refused" alınması tam olarak bu
    # yüzdendir (curl proxy'yi atlıyor/farklı okuyor, urllib proxy'ye
    # yönlendirip başarısız oluyor). Bu çağrı sohbet servisinin KENDİ Docker
    # ağındaki/host'undaki admin ucuna gidiyor; hiçbir zaman dış bir proxy'den
    # geçmesi gerekmiyor.
    acici = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with acici.open(istek, timeout=900) as yanit:
            gövde = json.loads(yanit.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detay = e.read().decode("utf-8", errors="replace")[:1000]
        except Exception:
            detay = "(gövde okunamadı)"
        print(
            f"❌ Vektörleme (Qdrant) hatası: {url} adresine ULAŞILDI ama sunucu "
            f"HTTP {e.code} döndü.\n"
            f"   Sunucu yanıtı: {detay}\n"
            "   Bu, ağ değil VEKTÖRLEME hatasıdır — sohbet servisinin loglarına bakın\n"
            "   (embedding API'si, Qdrant anahtarı/adresi ya da MongoDB erişimi)."
        )
        sys.exit(1)
    except urllib.error.URLError as e:
        print(
            f"❌ Vektörleme (Qdrant) hatası: 'chatbot' paketi yerel olarak import "
            f"edilemedi VE {url} adresine de ulaşılamadı ({e}).\n"
            "   Çözüm seçenekleri:\n"
            "   1) pipeline.py'yi chatbot/main.py ile AYNI container'da çalıştırın, YA DA\n"
            "   2) CHATBOT_SERVICE_URL ortam değişkenini sohbet servisinizin gerçek "
            "adresine ayarlayın\n"
            "      (docker-compose.yml'deki servis adı, ör. 'http://backend:8000')."
        )
        sys.exit(1)
    except Exception as e:
        print(f"❌ Vektörleme (Qdrant) hatası: sunucu isteğine hazırlanırken hata: {e}")
        sys.exit(1)

    if "adet" not in gövde:
        print(f"❌ Vektörleme (Qdrant) hatası: sunucudan beklenmeyen yanıt: {gövde}")
        sys.exit(1)

    _vektorleme_sonucunu_raporla(gövde["adet"])


def run_step_4_embedding():
    """MongoDB'deki TÜM kampanyaları vektörleyip Qdrant'a yazar.

    Mevcut RAG altyapısını yeniden kullanır — chatbot/indexing.py:
      • Kayıtları okur (önce islenmis_kampanyalar, boşsa smartdata.processed_campaigns,
        boşsa finagent.kampanyalar)
      • Her kampanya için arama metnini kurar
      • payload'a "banka_kodu" ekler  -> bankaya göre filtreli arama bunu kullanır
      • content_payload_key="belge"   -> sohbet tarafı bu anahtarı okur
      • Koleksiyonu force_recreate=True ile atomik olarak yeniden kurar

    ⚠️ Bu adım koleksiyonu SIFIRDAN kurar (eski vektörler silinir). Pipeline
    kazımadan sonra tam yeniden inşa yaptığı için burada istenen davranış budur.
    Embedding servisi kapalıysa mevcut koleksiyon KORUNUR (veri okunamazsa 0 döner
    ve yazma hiç yapılmaz), yani yarım/boş bir indeksle kalınmaz.

    🛠️ 'chatbot' paketi bu process'ten import edilemiyorsa (ayrı container/servis
    ihtimali — bkz. _adim4_http_ile_calistir), sessizce patlamak yerine aynı işi
    HTTP admin ucu üzerinden yaptırmayı DENER; o da başarısız olursa açık ve
    eyleme geçirilebilir bir hata mesajıyla durur.
    """
    log("ADIM 4: Kampanyalar Vektörlenip Qdrant'a Yükleniyor...")

    try:
        from chatbot.indexing import auto_init_qdrant
    except ModuleNotFoundError:
        _adim4_http_ile_calistir()
        return

    try:
        # auto_init_qdrant async; pipeline senkron olduğu için burada çalıştırıyoruz.
        # embeddings=None -> indexing.py hafif varsayılan embedder'ı kurar
        # (embedding_client üzerinden; LLM/sohbet yığınını import etmez).
        adet = asyncio.run(auto_init_qdrant())
    except Exception as e:
        # 🛠️ Artık gerçek hata tipi ve izi de basılıyor. indexing.py hatayı
        # yutmayı bıraktığı için buraya ANLAMLI bir istisna geliyor; eskiden
        # sessizce 0 dönüp pipeline yeşil bitiyordu.
        import traceback
        print(f"❌ Vektörleme (Qdrant) hatası: {type(e).__name__}: {e}")
        traceback.print_exc()
        print(
            "   ⚠️ DİKKAT: force_recreate=True koleksiyonu EN BAŞTA sildiği için,\n"
            "   koleksiyon şu an BOŞ ya da YARIM olabilir. Sorunu giderip bu adımı\n"
            "   tekrar çalıştırın:  python -m chatbot.indexing"
        )
        sys.exit(1)

    _vektorleme_sonucunu_raporla(adet)


def main():
    parser = argparse.ArgumentParser(description="SmartData Uçtan Uca Pipeline")
    parser.add_argument("banka", nargs="?", help="Çalıştırılacak banka id'si (ör. albaraka)")
    parser.add_argument("--hepsi", action="store_true", help="Aktif tüm bankaları sırayla çek")
    parser.add_argument(
        "--embed-atla",
        action="store_true",
        help="ADIM 4'ü (Qdrant vektörleme) atla — sadece kazıma/çıkarım çalışsın",
    )
    args = parser.parse_args()

    if not args.hepsi and not args.banka:
        parser.error("Lütfen bir banka id'si belirtin (ör. python pipeline.py albaraka) ya da --hepsi kullanın.")

    baslangic = datetime.now(timezone.utc)
    print("⚡ SmartData Uçtan Uca Pipeline Başlatılıyor...")

    # Sırasıyla Pipeline Adımları
    run_step_1_seed()
    run_step_2_runner(banka=args.banka, hepsi=args.hepsi)
    run_step_3_extraction()

    if args.embed_atla:
        log("ADIM 4 ATLANDI (--embed-atla) — Qdrant güncellenmedi.")
    else:
        run_step_4_embedding()

    # 🛠️ timedelta.seconds yerine total_seconds(): .seconds yalnızca gün İÇİNDEKİ
    # saniyeyi verir (0-86399), gün bileşenini atar — 24 saati aşan bir çalışmada
    # süre yanlış raporlanırdı.
    gecen_sure = int((datetime.now(timezone.utc) - baslangic).total_seconds())
    log(f"🎉 TÜM PIPELINE BAŞARIYLA TAMAMLANDI! (Süre: {gecen_sure} saniye)")


if __name__ == "__main__":
    main()