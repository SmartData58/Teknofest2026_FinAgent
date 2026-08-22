import argparse
import asyncio
import sys
from datetime import datetime, timezone


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


def run_step_4_embedding():
    """MongoDB'deki TÜM kampanyaları vektörleyip Qdrant'a yazar.

    Mevcut RAG altyapısını yeniden kullanır — chatbot/indexing.py:
      • Kayıtları okur (smartdata.processed_campaigns, boşsa finagent.kampanyalar)
      • Her kampanya için arama metnini kurar
      • payload'a "banka_kodu" ekler  -> bankaya göre filtreli arama bunu kullanır
      • content_payload_key="belge"   -> sohbet tarafı bu anahtarı okur
      • Koleksiyonu force_recreate=True ile atomik olarak yeniden kurar

    ⚠️ Bu adım koleksiyonu SIFIRDAN kurar (eski vektörler silinir). Pipeline
    kazımadan sonra tam yeniden inşa yaptığı için burada istenen davranış budur.
    Embedding servisi kapalıysa mevcut koleksiyon KORUNUR (veri okunamazsa 0 döner
    ve yazma hiç yapılmaz), yani yarım/boş bir indeksle kalınmaz.
    """
    log("ADIM 4: Kampanyalar Vektörlenip Qdrant'a Yükleniyor...")
    try:
        from chatbot.indexing import auto_init_qdrant

        # auto_init_qdrant async; pipeline senkron olduğu için burada çalıştırıyoruz.
        # embeddings=None -> indexing.py hafif varsayılan embedder'ı kurar
        # (embedding_client üzerinden; LLM/sohbet yığınını import etmez).
        adet = asyncio.run(auto_init_qdrant())

        if adet == 0:
            print(
                "⚠️ Vektörlenecek kampanya bulunamadı; Qdrant koleksiyonu değiştirilmedi.\n"
                "   MongoDB'de veri var mı diye kontrol edin: python mongo_durum.py"
            )
        else:
            print(f"✅ {adet} kampanya Qdrant'a vektörlendi.")
    except Exception as e:
        print(f"❌ Vektörleme (Qdrant) hatası: {e}")
        sys.exit(1)


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